"""
water_bills.py
══════════════
Business logic for the Water Bill Tracker module.

Status lifecycle for water_bill_requests:
    pending        — request created, not yet sent to municipality
    sent           — initial request sent (email, fax, phone, or portal)
    follow_up_sent — at least one follow-up sent after the initial request
    received       — water bill PDF received and uploaded to storage

All Supabase calls use get_supabase() from supabase_client.py.
Outbound sending (email via MS Graph, fax via Phaxio) is deferred to Phase 2.
"""

from datetime import datetime, timezone, date, timedelta
from supabase_client import get_supabase

WATER_BILLS_BUCKET = "water-bills"
GLOBAL_LEAD_TIME_DAYS = 7

# Maps followup action → resulting request status.
# 'note' entries are logged without changing the parent status.
_ACTION_TO_STATUS = {
    "sent":       "sent",
    "follow_up":  "follow_up_sent",
    "phone_call": "follow_up_sent",
    "received":   "received",
    "note":       None,
}


def get_municipalities() -> list:
    """Fetch all municipalities ordered alphabetically."""
    sb = get_supabase()
    result = sb.table("municipalities").select("*").order("name").execute()
    return result.data or []


def create_request(data: dict) -> dict:
    """Insert a new water bill request row. Returns the created record."""
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        **data,
        "status": data.get("status", "pending"),
        "updated_at": now,
    }
    result = sb.table("water_bill_requests").insert(payload).execute()
    if not result.data:
        raise RuntimeError("water_bill_requests insert returned no data.")
    return result.data[0]


def create_request_from_order(order_id: str, order_data: dict) -> dict:
    """Map a PA Extractor order to a water bill request and create it.

    Reads property address, parties, closing date, and closer/assistant fields
    from order_data (the orders table row). Status starts as 'pending'.
    """
    extracted = order_data.get("extracted_data") or {}
    prop = extracted.get("property", {}) or {}
    dates = extracted.get("dates", {}) or {}

    address_parts = [
        prop.get("street_address"),
        prop.get("city"),
        prop.get("county"),
        prop.get("state"),
        prop.get("zip_code"),
    ]
    property_address = ", ".join(p for p in address_parts if p)

    buyers = extracted.get("parties", {}).get("buyers", [])
    new_buyers = "; ".join(b.get("name", "") for b in buyers if b.get("name"))

    sellers = extracted.get("parties", {}).get("sellers", [])
    current_owners = "; ".join(s.get("name", "") for s in sellers if s.get("name"))

    closing_date_str = dates.get("closing_date")
    municipality_id = None  # Phase 2: derive from order/property lookup

    # Calculate send_by_date from closing date minus lead time.
    # Uses municipality-specific lead_time_days if a municipality_id is set,
    # falling back to GLOBAL_LEAD_TIME_DAYS.
    send_by_date = None
    lead_time_days_used = None
    if closing_date_str:
        try:
            closing = date.fromisoformat(closing_date_str)
            lead_time = GLOBAL_LEAD_TIME_DAYS
            if municipality_id:
                sb = get_supabase()
                muni_result = (
                    sb.table("municipalities")
                    .select("lead_time_days")
                    .eq("id", municipality_id)
                    .single()
                    .execute()
                )
                muni_lead = (muni_result.data or {}).get("lead_time_days")
                if muni_lead is not None:
                    lead_time = muni_lead
            send_by_date = (closing - timedelta(days=lead_time)).isoformat()
            lead_time_days_used = lead_time
        except (ValueError, TypeError):
            pass

    data = {
        "order_id":            order_id,
        "file_number":         None,
        "property_address":    property_address or None,
        "current_owners":      current_owners or None,
        "new_buyers":          new_buyers or None,
        "closing_date":        closing_date_str,
        "send_by_date":        send_by_date,
        "lead_time_days_used": lead_time_days_used,
        "municipality_id":     municipality_id,
        "closer_name":         order_data.get("closer"),
        "closer_email":        None,
        "closer_phone":        None,
        "assistant_name":      order_data.get("assistant_main_contact"),
        "assistant_email":     None,
        "assistant_phone":     None,
        "notes":               None,
        "status":              "pending",
    }
    return create_request(data)


def get_requests(filters: dict = None) -> list:
    """Fetch requests with optional filters, joined to municipalities.

    Supported filter keys:
        status (list[str])      — include only these status values
        closing_date_from (str) — ISO date string, inclusive lower bound
        closing_date_to (str)   — ISO date string, inclusive upper bound
    """
    sb = get_supabase()
    q = (
        sb.table("water_bill_requests")
        .select("*, municipalities(name, preferred_method, email, fax, portal_url)")
        .order("created_at", desc=True)
    )
    if filters:
        if filters.get("status"):
            q = q.in_("status", filters["status"])
        if filters.get("closing_date_from"):
            q = q.gte("closing_date", filters["closing_date_from"])
        if filters.get("closing_date_to"):
            q = q.lte("closing_date", filters["closing_date_to"])

    result = q.execute()
    return result.data or []


def get_request(request_id: str) -> dict:
    """Fetch a single request with its full followup log (newest first)."""
    sb = get_supabase()
    req_result = (
        sb.table("water_bill_requests")
        .select("*, municipalities(name, preferred_method, email, fax, portal_url)")
        .eq("id", request_id)
        .single()
        .execute()
    )
    record = req_result.data or {}

    followup_result = (
        sb.table("water_bill_followups")
        .select("*")
        .eq("request_id", request_id)
        .order("logged_at", desc=True)
        .execute()
    )
    record["followups"] = followup_result.data or []
    return record


def update_request(request_id: str, data: dict) -> dict:
    """Update arbitrary fields on a request. Always bumps updated_at."""
    sb = get_supabase()
    payload = {**data, "updated_at": datetime.now(timezone.utc).isoformat()}
    result = (
        sb.table("water_bill_requests")
        .update(payload)
        .eq("id", request_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"Update returned no data for request {request_id}.")
    return result.data[0]


def update_status(request_id: str, status: str) -> None:
    """Update just the status field and bump updated_at."""
    update_request(request_id, {"status": status})


def log_followup(
    request_id: str,
    action: str,
    method: str,
    notes: str,
    logged_by: str,
) -> dict:
    """Insert a followup log entry and advance the request status if applicable.

    Actions: sent, follow_up, phone_call, received, note
    'note' entries are logged without changing the parent request status.
    """
    sb = get_supabase()
    row = {
        "request_id": request_id,
        "action":     action,
        "method":     method or None,
        "notes":      notes or None,
        "logged_by":  logged_by or None,
        "logged_at":  datetime.now(timezone.utc).isoformat(),
    }
    result = sb.table("water_bill_followups").insert(row).execute()
    if not result.data:
        raise RuntimeError("water_bill_followups insert returned no data.")

    new_status = _ACTION_TO_STATUS.get(action)
    if new_status:
        update_status(request_id, new_status)

    return result.data[0]


def upload_bill_pdf(request_id: str, file_bytes: bytes, filename: str) -> str:
    """Upload a water bill PDF to the water-bills storage bucket.

    Updates bill_pdf_path on the request and sets status to 'received'.
    Returns the storage path.
    """
    sb = get_supabase()
    storage_path = f"{request_id}/{filename}"
    sb.storage.from_(WATER_BILLS_BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf"},
    )
    update_request(request_id, {"bill_pdf_path": storage_path, "status": "received"})
    return storage_path


def get_bill_pdf_url(bill_pdf_path: str) -> str:
    """Return a 60-minute signed URL for the given bill PDF storage path."""
    sb = get_supabase()
    result = sb.storage.from_(WATER_BILLS_BUCKET).create_signed_url(
        bill_pdf_path, expires_in=3600
    )
    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or (result.get("data") or {}).get("signedUrl")
            or ""
        )
    return getattr(result, "signed_url", "") or ""

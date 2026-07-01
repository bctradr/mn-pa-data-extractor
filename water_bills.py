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

import re
from datetime import datetime, timezone, date, timedelta
from supabase_client import get_supabase

WATER_BILLS_BUCKET = "water-bills"
GLOBAL_LEAD_TIME_DAYS = 7

# ── Reply-matching constants ───────────────────────────────────────────────────

_FILE_NUM_RE = re.compile(r'File#\s*([A-Za-z0-9\-]+)', re.IGNORECASE)
_DOLLAR_RE   = re.compile(r'\$[\d,]+\.?\d*|\b\d[\d,]+\.\d{2}\b')
_STREET_RE   = re.compile(r'^\s*(\d+\s+[A-Za-z0-9][^,\n]{2,30})', re.IGNORECASE)

_BOUNCE_INDICATORS = [
    "delivery status notification",
    "undeliverable",
    "mail delivery failed",
    "returned mail",
    "failure notice",
    "auto-reply",
    "automatic reply",
    "out of office",
    "autoreply",
]

# Maps followup action → resulting request status.
# 'note' entries are logged without changing the parent status.
_ACTION_TO_STATUS = {
    "sent":       "sent",
    "follow_up":  "follow_up_sent",
    "phone_call": "follow_up_sent",
    "received":   "received",
    "note":       None,
    "cancelled":  "cancelled",
    "completed":  "completed",
}


def calculate_send_by_date(closing_date, municipality_id: str = None) -> tuple:
    """Calculate send_by_date and lead_time_days_used from a closing date.

    Returns (send_by_date: date, lead_time_days_used: int), or (None, None)
    if closing_date is None. Queries municipalities.lead_time_days when
    municipality_id is provided and the column is set; falls back to
    GLOBAL_LEAD_TIME_DAYS otherwise. Works with date objects; callers handle
    ISO string conversion at their boundaries.
    """
    if closing_date is None:
        return (None, None)
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
    return (closing_date - timedelta(days=lead_time), lead_time)


def get_municipalities() -> list:
    """Fetch all municipalities ordered alphabetically, paginating past the 1000-row PostgREST default."""
    sb = get_supabase()
    all_rows = []
    page_size = 1000
    page = 0
    while True:
        result = (
            sb.table("municipalities")
            .select("*")
            .order("name")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = result.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return all_rows


def create_municipality(data: dict) -> dict:
    """Insert a new municipality row. Returns the created record."""
    sb = get_supabase()
    result = sb.table("municipalities").insert(data).execute()
    if not result.data:
        raise RuntimeError("municipalities insert returned no data.")
    return result.data[0]


def update_municipality(muni_id: str, data: dict) -> dict:
    """Update fields on a municipality. Returns the updated record."""
    sb = get_supabase()
    result = (
        sb.table("municipalities")
        .update(data)
        .eq("id", muni_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"Update returned no data for municipality {muni_id}.")
    return result.data[0]


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

    closing_date_obj = None
    if closing_date_str:
        try:
            closing_date_obj = date.fromisoformat(closing_date_str)
        except (ValueError, TypeError):
            pass
    send_by, lead_time_used = calculate_send_by_date(closing_date_obj, municipality_id)

    data = {
        "order_id":            order_id,
        "file_number":         None,
        "property_address":    property_address or None,
        "current_owners":      current_owners or None,
        "new_buyers":          new_buyers or None,
        "closing_date":        closing_date_str,
        "send_by_date":        send_by.isoformat() if send_by else None,
        "lead_time_days_used": lead_time_used,
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
        status (list[str])       — include only these status values
        created_at_from (str)    — ISO date string, inclusive lower bound on created_at
        created_at_to (str)      — ISO date string, inclusive upper bound on created_at
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
        if filters.get("created_at_from"):
            q = q.gte("created_at", filters["created_at_from"])
        if filters.get("created_at_to"):
            q = q.lte("created_at", filters["created_at_to"])

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


def cancel_request(request_id: str, reason: str, logged_by: str) -> dict:
    """Log a cancellation and set the request status to 'cancelled'.

    Raises ValueError if reason is empty or whitespace.
    """
    if not reason or not reason.strip():
        raise ValueError("Cancellation reason is required.")
    return log_followup(
        request_id=request_id,
        action="cancelled",
        method=None,
        notes=reason.strip(),
        logged_by=logged_by,
    )


def complete_request(request_id: str, logged_by: str, notes: str = None) -> dict:
    """Log completion and set the request status to 'completed'.

    Only callable when the current status is 'received'; raises ValueError otherwise.
    """
    sb = get_supabase()
    current = (
        sb.table("water_bill_requests")
        .select("status")
        .eq("id", request_id)
        .single()
        .execute()
    )
    current_status = (current.data or {}).get("status")
    if current_status != "received":
        raise ValueError(
            f"Cannot complete a request with status '{current_status}' — "
            "must be 'received' first."
        )
    return log_followup(
        request_id=request_id,
        action="completed",
        method=None,
        notes=notes or None,
        logged_by=logged_by,
    )


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


def compose_water_bill_email(request: dict) -> tuple:
    """Compose subject and body for an outbound water bill request email.

    Returns (subject: str, body: str).
    """
    muni = request.get("municipalities") or {}
    muni_name = request.get("municipality_name") or muni.get("name") or ""
    address = request.get("property_address") or "—"
    address_with_muni = f"{address}, {muni_name}" if muni_name else address
    closing = request.get("closing_date") or "—"
    owners = request.get("current_owners") or "—"
    buyers = request.get("new_buyers") or "—"
    file_num = request.get("file_number") or "—"

    closer_name  = request.get("closer_name") or ""
    closer_email = request.get("closer_email") or ""
    closer_phone = request.get("closer_phone") or ""
    asst_name    = request.get("assistant_name") or ""
    asst_email   = request.get("assistant_email") or ""
    asst_phone   = request.get("assistant_phone") or ""

    contact_lines = []
    if closer_name:
        parts = [closer_name]
        if closer_email:
            parts.append(closer_email)
        if closer_phone:
            parts.append(closer_phone)
        contact_lines.append("Closer: " + " | ".join(parts))
    if asst_name:
        parts = [asst_name]
        if asst_email:
            parts.append(asst_email)
        if asst_phone:
            parts.append(asst_phone)
        contact_lines.append("Assistant: " + " | ".join(parts))
    contact_block = "\n".join(contact_lines) if contact_lines else "See reply address above."

    subject = f"Water Bill Request - File# {file_num} - {address_with_muni}"

    body = f"""\
Dear {muni_name or "Water Department"},

We are requesting the current water/utility bill balance for the following property \
in connection with an upcoming real estate closing:

  Property Address : {address_with_muni}
  Current Owners   : {owners}
  New Buyers       : {buyers}
  Closing Date     : {closing}
  File Number      : {file_num}

Please reply to this email with the current outstanding balance as soon as possible. \
If a payoff statement or final bill is available, please include it as well.

Contact information:
{contact_block}

Thank you for your assistance.
"""
    return subject, body


# ── Inbound reply matching ─────────────────────────────────────────────────────

def _classify_reply(message: dict) -> str:
    """Classify an inbound message as 'bounce', 'structured_reply', or 'unstructured_reply'."""
    text = ((message.get("subject") or "") + " " + (message.get("body") or "")).lower()
    if any(ind in text for ind in _BOUNCE_INDICATORS):
        return "bounce"
    if _DOLLAR_RE.search(message.get("body") or ""):
        return "structured_reply"
    return "unstructured_reply"


def _extract_street_portion(address: str) -> str | None:
    """Extract 'street number + street name' from a full address for fallback matching.

    E.g. '123 Main St, Apt 4, Minneapolis, MN 55401' -> '123 Main St'.
    Returns None if address is blank or doesn't start with a street number.
    """
    if not address:
        return None
    m = _STREET_RE.match(address)
    return m.group(1).strip() if m else None


def _match_reply(message: dict, active_requests: list) -> tuple:
    """Try to match an inbound message to an active request.

    Matching priority:
    1. Regex for 'File# XXXX' in the subject line matched against file_number.
    2. Fallback: street portion of property_address found in subject or body.

    Returns (matched_request, signal) where signal is 'file_number' or
    'property_address', or (None, None) if no match.
    Sender address is never used as a matching criterion.
    """
    subject = message.get("subject") or ""
    body    = message.get("body") or ""

    # Signal 1 — file number token in subject
    file_num_match = _FILE_NUM_RE.search(subject)
    if file_num_match:
        found_num = file_num_match.group(1).strip()
        for req in active_requests:
            req_num = (req.get("file_number") or "").strip()
            if req_num and req_num == found_num:
                return req, "file_number"

    # Signal 2 — street portion of property address in subject or body
    haystack = (subject + " " + body).lower()
    for req in active_requests:
        street = _extract_street_portion(req.get("property_address") or "")
        if street and len(street) >= 6 and street.lower() in haystack:
            return req, "property_address"

    return None, None


def log_unmatched_message(message: dict) -> None:
    """Store an unmatched inbox message. Silently skips duplicates (unique gmail_message_id)."""
    sb = get_supabase()
    sb.table("water_bill_unmatched_messages").upsert(
        {
            "gmail_message_id": message.get("id"),
            "from_address":     message.get("from"),
            "subject":          message.get("subject"),
            "body_preview":     (message.get("body") or "")[:500],
            "received_at":      message.get("date"),
            "checked_at":       datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="gmail_message_id",
    ).execute()


def process_inbox_replies(messages: list) -> dict:
    """Match a list of fetched inbox messages to active requests.

    For each message:
    - If matched (by file number or property address): logs a followup note on
      the matched request recording the signal and classification.
    - If unmatched: stores in water_bill_unmatched_messages (requires migration 005).

    Args:
        messages: list of message dicts from gmail_client.check_inbox().

    Returns:
        {
          "matched":   list of {request_id, file_number, property_address,
                                message, signal, classification},
          "unmatched": list of raw message dicts,
        }
    """
    active = get_requests({"status": ["pending", "sent", "follow_up_sent"]})
    matched   = []
    unmatched = []

    for msg in messages:
        req, signal = _match_reply(msg, active)
        classification = _classify_reply(msg)

        if req:
            notes = (
                f"Inbound reply — matched on {signal.replace('_', ' ')} — "
                f"{classification.replace('_', ' ')} — "
                f"from: {msg.get('from') or '—'}"
            )
            log_followup(
                request_id=req["id"],
                action="note",
                method="email",
                notes=notes,
                logged_by="system",
            )
            matched.append({
                "request_id":       req["id"],
                "file_number":      req.get("file_number"),
                "property_address": req.get("property_address"),
                "message":          msg,
                "signal":           signal,
                "classification":   classification,
            })
        else:
            try:
                log_unmatched_message(msg)
            except Exception:
                pass  # table may not exist yet; don't crash reply processing
            unmatched.append(msg)

    return {"matched": matched, "unmatched": unmatched}


def get_unmatched_messages(status: str = "new") -> list:
    """Return unmatched inbox messages with the given status."""
    sb = get_supabase()
    result = (
        sb.table("water_bill_unmatched_messages")
        .select("*")
        .eq("status", status)
        .order("checked_at", desc=True)
        .execute()
    )
    return result.data or []


def update_unmatched_message(msg_id: str, data: dict) -> dict:
    """Update fields on an unmatched message row."""
    sb = get_supabase()
    result = (
        sb.table("water_bill_unmatched_messages")
        .update(data)
        .eq("id", msg_id)
        .execute()
    )
    return (result.data or [{}])[0]


def get_bounced_requests() -> list:
    """Return active requests whose most recent auto-processed followup was classified as a bounce."""
    sb = get_supabase()
    followup_result = (
        sb.table("water_bill_followups")
        .select("request_id, logged_at")
        .ilike("notes", "Inbound reply%bounce%")
        .order("logged_at", desc=True)
        .execute()
    )
    seen_ids: list[str] = []
    seen_set: set[str] = set()
    for row in (followup_result.data or []):
        rid = row["request_id"]
        if rid not in seen_set:
            seen_set.add(rid)
            seen_ids.append(rid)
    if not seen_ids:
        return []
    req_result = (
        sb.table("water_bill_requests")
        .select("id, file_number, property_address, status, municipality_name")
        .in_("id", seen_ids)
        .in_("status", ["sent", "follow_up_sent"])
        .execute()
    )
    return req_result.data or []

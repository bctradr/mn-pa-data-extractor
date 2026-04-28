"""
supabase_client.py
══════════════════
Helpers for the orders DB and order-documents storage bucket.
Used by new_order_app.py.
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


BUCKET_NAME = "order-documents"


@st.cache_resource
def get_supabase() -> Client:
    """Initialize Supabase client (cached across reruns)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ── Orders ────────────────────────────────────────────

def create_order(intake_fields: dict, files: list) -> str:
    """Create order row, upload files to storage, return new order_id.
    
    files: list of (filename, file_bytes) tuples.
    """
    sb = get_supabase()

    # 1. Insert order row
    result = sb.table("orders").insert(intake_fields).execute()
    if not result.data:
        raise RuntimeError("Order insert returned no data.")
    order_id = result.data[0]["id"]

    # 2. Upload files to storage and record each one
    for filename, file_bytes in files:
        storage_path = f"{order_id}/{filename}"
        sb.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
        sb.table("order_documents").insert({
            "order_id": order_id,
            "filename": filename,
            "storage_path": storage_path,
        }).execute()

    return order_id


def list_orders() -> list:
    """All orders, newest first."""
    sb = get_supabase()
    result = sb.table("orders").select("*").order("created_at", desc=True).execute()
    return result.data or []


def get_order(order_id: str) -> dict:
    sb = get_supabase()
    result = sb.table("orders").select("*").eq("id", order_id).execute()
    return result.data[0] if result.data else None


def get_order_documents(order_id: str) -> list:
    sb = get_supabase()
    result = sb.table("order_documents").select("*").eq("order_id", order_id).execute()
    return result.data or []


def download_documents(order_id: str) -> list:
    """Return list of (file_bytes, filename) for extraction."""
    sb = get_supabase()
    docs = get_order_documents(order_id)
    files = []
    for doc in docs:
        bytes_data = sb.storage.from_(BUCKET_NAME).download(doc["storage_path"])
        files.append((bytes_data, doc["filename"]))
    return files


def update_extraction(order_id: str, extracted_data: dict, flags: list):
    """Save extraction results back to the order row and mark status='extracted'."""
    sb = get_supabase()
    sb.table("orders").update({
        "extracted_data": extracted_data,
        "extraction_flags": flags,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "status": "extracted",
    }).eq("id", order_id).execute()


def delete_order(order_id: str):
    """Delete order row + cascade to documents + remove files from storage."""
    sb = get_supabase()
    docs = get_order_documents(order_id)
    # Delete files from storage first (no cascade for storage)
    for doc in docs:
        try:
            sb.storage.from_(BUCKET_NAME).remove([doc["storage_path"]])
        except Exception:
            pass  # don't block delete on a missing file
    # Delete order row (cascades to order_documents via foreign key)
    sb.table("orders").delete().eq("id", order_id).execute()

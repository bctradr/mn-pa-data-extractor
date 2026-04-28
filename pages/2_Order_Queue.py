"""
2_Order_Queue.py
════════════════
Order queue — list all saved orders, run extraction on any of them, and
export unified intake + extracted-data files for TPS upload.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

from extractor import (
    extract_from_pdf,
    flatten_combined_for_csv,
    intake_summary_text,
    intake_summary_html,
)
from summary_generator import generate_text_summary, generate_html_summary
from supabase_client import (
    list_orders,
    get_order_documents,
    download_documents,
    update_extraction,
    delete_order,
)


try:
    st.set_page_config(page_title="Order Queue", page_icon="📋", layout="wide")
except Exception:
    pass


st.title("📋 Order Queue")
st.caption("Saved orders — run extraction, review results, export for TPS.")


# ── Helpers ──────────────────────────────────────────

def _intake_from_order(order: dict) -> dict:
    """Pull just the intake fields out of an order row."""
    return {
        "order_type": order.get("order_type"),
        "client_name_referrer": order.get("client_name_referrer"),
        "client_broker": order.get("client_broker"),
        "lender": order.get("lender"),
        "mortgage_broker": order.get("mortgage_broker"),
        "plat_and_assessments": order.get("plat_and_assessments"),
        "closer": order.get("closer"),
        "underwriter_code": order.get("underwriter_code"),
        "office": order.get("office"),
        "assistant_main_contact": order.get("assistant_main_contact"),
        "business_dev_contact_other_agent": order.get("business_dev_contact_other_agent"),
        "additional_notes": order.get("additional_notes"),
    }


def _format_created_at(s: str) -> str:
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        return s[:10]


def _render_order_detail(order: dict):
    """Body of an expanded queue row."""
    order_id = order["id"]

    # ── Intake fields ──
    st.markdown("**Order intake**")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"- **Order Type:** {order.get('order_type') or '—'}")
        st.markdown(f"- **Client Name (Referrer):** {order.get('client_name_referrer') or '—'}")
        st.markdown(f"- **Client Broker:** {order.get('client_broker') or '—'}")
        st.markdown(f"- **Lender:** {order.get('lender') or '—'}")
        st.markdown(f"- **Mortgage Broker:** {order.get('mortgage_broker') or '—'}")
        st.markdown(f"- **Plat & Assessments:** {order.get('plat_and_assessments') or '—'}")
    with col_b:
        st.markdown(f"- **Closer:** {order.get('closer') or '—'}")
        st.markdown(f"- **Underwriter Code:** {order.get('underwriter_code') or '—'}")
        st.markdown(f"- **Office:** {order.get('office') or '—'}")
        st.markdown(f"- **Assistant & Main Contact:** {order.get('assistant_main_contact') or '—'}")
        st.markdown(f"- **Sales Team to Contact Other Agent:** {order.get('business_dev_contact_other_agent') or '—'}")

    notes = order.get("additional_notes")
    if notes:
        st.markdown(f"**Notes:** {notes}")

    # ── Documents ──
    st.markdown("**Documents**")
    try:
        docs = get_order_documents(order_id)
        if docs:
            for d in docs:
                st.caption(f"📄 {d['filename']}")
        else:
            st.caption("_No documents found._")
    except Exception as e:
        st.error(f"Could not load documents: {e}")

    st.divider()

    # ── Extract / Re-extract / Exports ──
    status = order.get("status", "new")
    extracted = order.get("extracted_data") or {}
    flags = order.get("extraction_flags") or []

    if status != "extracted":
        if st.button("🔍 Extract Fields", key=f"extract_{order_id}", type="primary"):
            with st.spinner("Downloading documents and extracting fields..."):
                try:
                    files = download_documents(order_id)
                    result = extract_from_pdf(files)
                    result_flags = result.get("extraction_metadata", {}).get("flags", [])
                    update_extraction(order_id, result, result_flags)
                    st.success("✅ Extraction complete!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {e}")
    else:
        st.markdown(f"**Extraction:** {len(flags)} flag(s)")
        if flags:
            with st.expander(f"Show all {len(flags)} flag(s)", expanded=False):
                for f in flags:
                    st.caption(f"⚠️ **{f.get('field', '?')}** — {f.get('issue', '?')}: {f.get('note', '')}")

        intake = _intake_from_order(order)

        st.markdown("**Export (intake + extracted PA fields, snake_case)**")
        c1, c2, c3, c4 = st.columns(4)

        text_combined = intake_summary_text(intake) + generate_text_summary(extracted, "")
        with c1:
            st.download_button(
                "📋 Text",
                data=text_combined.encode("utf-8"),
                file_name=f"order_{order_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"txt_{order_id}",
            )

        html_combined = intake_summary_html(intake) + generate_html_summary(extracted, "")
        with c2:
            st.download_button(
                "🌐 HTML",
                data=html_combined.encode("utf-8"),
                file_name=f"order_{order_id[:8]}.html",
                mime="text/html",
                use_container_width=True,
                key=f"html_{order_id}",
            )

        flat = flatten_combined_for_csv(intake, extracted)
        csv_str = pd.DataFrame([flat]).to_csv(index=False)
        with c3:
            st.download_button(
                "📥 CSV",
                data=csv_str.encode("utf-8"),
                file_name=f"order_{order_id[:8]}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"csv_{order_id}",
            )

        json_combined = {"order_intake": intake, "extracted_data": extracted}
        json_str = json.dumps(json_combined, indent=2, default=str)
        with c4:
            st.download_button(
                "📥 JSON",
                data=json_str.encode("utf-8"),
                file_name=f"order_{order_id[:8]}.json",
                mime="application/json",
                use_container_width=True,
                key=f"json_{order_id}",
            )

        st.divider()
        col_x, col_y = st.columns(2)
        with col_x:
            if st.button("🔁 Re-extract", key=f"reextract_{order_id}"):
                with st.spinner("Re-running extraction..."):
                    try:
                        files = download_documents(order_id)
                        result = extract_from_pdf(files)
                        result_flags = result.get("extraction_metadata", {}).get("flags", [])
                        update_extraction(order_id, result, result_flags)
                        st.success("Re-extraction complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Re-extraction failed: {e}")
        with col_y:
            confirm_key = f"confirm_delete_{order_id}"
            if st.session_state.get(confirm_key):
                if st.button("⚠️ Confirm delete (PDFs will be removed)", key=f"confirm_{order_id}"):
                    try:
                        delete_order(order_id)
                        st.session_state[confirm_key] = False
                        st.success("Order deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
            else:
                if st.button("🗑️ Delete order", key=f"delete_{order_id}"):
                    st.session_state[confirm_key] = True
                    st.rerun()


# ── Main ─────────────────────────────────────────────

refresh_col, _ = st.columns([1, 6])
with refresh_col:
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    orders = list_orders()
except Exception as e:
    st.error(f"Failed to load orders: {e}")
    orders = []

if not orders:
    st.info("No orders yet. Use the **New Order** page (sidebar) to create one.")
else:
    st.caption(f"{len(orders)} order(s) — newest first")
    for order in orders:
        date_str = _format_created_at(order.get("created_at", ""))
        client = order.get("client_name_referrer") or "—"
        otype = order.get("order_type") or "—"
        cl = order.get("closer") or "—"
        uw = order.get("underwriter_code") or "—"
        office_val = order.get("office") or "—"
        status = order.get("status", "new")
        status_label = "🟢 Extracted" if status == "extracted" else "🔵 New"

        header = f"**{date_str}** · {client} · {otype} · {cl} ({uw}) · {office_val} · {status_label}"
        with st.expander(header, expanded=False):
            _render_order_detail(order)

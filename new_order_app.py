"""
new_order_app.py
════════════════
Streamlit app: "Open New Order" + "Order queue".

Tab 1 (Open new order): User uploads PDFs and enters intake fields. Closer-
driven autofill populates underwriter code, office, and assistant.

Tab 2 (Order queue): All saved orders. Each row expands to show full
intake data and a button to run extraction. Once extracted, four export
buttons (text / HTML / CSV / JSON) produce unified intake+PA outputs
ready for TPS upload.
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
    INTAKE_LABELS,
)
from summary_generator import generate_text_summary, generate_html_summary
from assignment_rules import CLOSERS, OFFICES, ORDER_TYPES, get_assignment
from supabase_client import (
    create_order,
    list_orders,
    get_order_documents,
    download_documents,
    update_extraction,
    delete_order,
)


# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="Open New Order",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Open New Order")
st.caption("Intake → queue → extract → push to TPS")


# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

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
    """Make the timestamp display compactly."""
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        return s[:10]


def _render_order_detail(order: dict):
    """Body of an expanded queue row. Shows intake, docs, extract action,
    extraction results (if any), and exports."""
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
        st.markdown(f"- **Business Dev. Contact Other Agent:** {order.get('business_dev_contact_other_agent') or '—'}")

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
        # New order — single Extract button
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
        # Already extracted — show flag summary + exports
        st.markdown(f"**Extraction:** {len(flags)} flag(s)")
        if flags:
            with st.expander(f"Show all {len(flags)} flag(s)", expanded=False):
                for f in flags:
                    st.caption(f"⚠️ **{f.get('field', '?')}** — {f.get('issue', '?')}: {f.get('note', '')}")

        intake = _intake_from_order(order)

        st.markdown("**Export (intake + extracted PA fields, snake_case)**")
        c1, c2, c3, c4 = st.columns(4)

        text_combined = intake_summary_text(intake) + generate_text_summary(extracted)
        with c1:
            st.download_button(
                "📄 Text",
                data=text_combined,
                file_name=f"order_{order_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"txt_{order_id}",
            )

        html_combined = intake_summary_html(intake) + generate_html_summary(extracted)
        with c2:
            st.download_button(
                "🌐 HTML",
                data=html_combined,
                file_name=f"order_{order_id[:8]}.html",
                mime="text/html",
                use_container_width=True,
                key=f"html_{order_id}",
            )

        flat = flatten_combined_for_csv(intake, extracted)
        csv_str = pd.DataFrame([flat]).to_csv(index=False)
        with c3:
            st.download_button(
                "📊 CSV",
                data=csv_str,
                file_name=f"order_{order_id[:8]}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"csv_{order_id}",
            )

        json_combined = {"order_intake": intake, "extracted_data": extracted}
        json_str = json.dumps(json_combined, indent=2, default=str)
        with c4:
            st.download_button(
                "{ } JSON",
                data=json_str,
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


# ══════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════

tab_new, tab_queue = st.tabs(["Open new order", "Order queue"])


# ── Tab 1: Open new order ─────────────────────────────

with tab_new:
    # File uploader
    st.markdown("**Documents**")
    uploaded = st.file_uploader(
        "Drag and drop PDFs here",
        type=["pdf"],
        accept_multiple_files=True,
        help="PA, addenda, seller's disclosure — extraction figures out which is which",
        key="no_uploader",
    )
    if uploaded:
        st.success(f"Loaded {len(uploaded)} file(s)")
        for f in uploaded:
            st.caption(f"• {f.name} ({f.size / 1024:.0f} KB)")

    st.divider()

    # ── Order details ──
    col1, col2 = st.columns(2)
    with col1:
        order_type = st.selectbox(
            "Order Type *",
            options=[""] + ORDER_TYPES,
            key="no_order_type",
        )
        client_name = st.text_input("Client Name (Referrer) *", key="no_client_name")
        lender = st.text_input("Lender *", key="no_lender")
        plat = st.selectbox("Plat & Assessments *", options=["", "Yes", "No"], key="no_plat")
    with col2:
        client_broker = st.text_input("Client Broker", key="no_client_broker")
        mortgage_broker = st.text_input("Mortgage Broker *", key="no_mortgage_broker")
        bd_contact = st.selectbox(
            "Business Dev. Contact Other Agent *",
            options=["", "Yes", "No"],
            key="no_bd_contact",
        )

    # ── Closer-driven assignment block ──
    st.markdown("**Closer-driven assignment**")
    st.caption("Underwriter, office, and assistant auto-fill when you pick a closer. All three are editable.")

    col3, col4 = st.columns(2)
    with col3:
        closer = st.selectbox(
            "Closer *",
            options=[""] + CLOSERS,
            key="no_closer",
        )

    # Compute defaults from closer + order_type. Widget keys include
    # closer/order_type so they reset to fresh defaults on change.
    defaults = get_assignment(closer, order_type)
    rekey = f"{closer}__{order_type}"

    with col4:
        uw_code = st.text_input(
            "Underwriter Code",
            value=defaults["underwriter_code"],
            help="Auto-filled from closer · editable",
            key=f"no_uw_{rekey}",
        )

    col5, col6 = st.columns(2)
    with col5:
        office_options = [""] + OFFICES
        try:
            office_idx = office_options.index(defaults["office"]) if defaults["office"] else 0
        except ValueError:
            office_idx = 0
        office = st.selectbox(
            "Office",
            options=office_options,
            index=office_idx,
            help="Auto-filled from closer · editable",
            key=f"no_office_{rekey}",
        )
    with col6:
        assistant = st.text_input(
            "Assistant & Main Contact *",
            value=defaults["assistant"],
            help="Auto-filled from closer + order type · editable",
            key=f"no_assistant_{rekey}",
        )

    notes = st.text_area("Additional Notes *", height=80, key="no_notes")

    st.divider()

    # ── Save ──
    col_save_l, col_save_r = st.columns([3, 1])
    with col_save_r:
        save_clicked = st.button("💾 Save Order", type="primary", use_container_width=True)

    if save_clicked:
        errors = []
        if not uploaded:
            errors.append("At least one PDF must be uploaded.")
        if not order_type:
            errors.append("Order Type is required.")
        if not client_name:
            errors.append("Client Name (Referrer) is required.")
        if not lender:
            errors.append("Lender is required.")
        if not mortgage_broker:
            errors.append("Mortgage Broker is required.")
        if not plat:
            errors.append("Plat & Assessments is required.")
        if not bd_contact:
            errors.append("Business Dev. Contact Other Agent is required.")
        if not closer:
            errors.append("Closer is required.")
        if not assistant:
            errors.append("Assistant & Main Contact is required.")
        if not notes:
            errors.append("Additional Notes are required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            with st.spinner("Saving order and uploading documents..."):
                try:
                    intake = {
                        "order_type": order_type,
                        "client_name_referrer": client_name,
                        "client_broker": client_broker,
                        "lender": lender,
                        "mortgage_broker": mortgage_broker,
                        "plat_and_assessments": plat,
                        "closer": closer,
                        "underwriter_code": uw_code,
                        "office": office,
                        "assistant_main_contact": assistant,
                        "business_dev_contact_other_agent": bd_contact,
                        "additional_notes": notes,
                    }
                    files = [(f.name, f.read()) for f in uploaded]
                    order_id = create_order(intake, files)
                    st.success(f"✅ Order saved. View it in the **Order queue** tab.")
                    st.caption(f"Internal ID: {order_id}")
                except Exception as e:
                    st.error(f"Failed to save: {e}")


# ── Tab 2: Order queue ────────────────────────────────

with tab_queue:
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
        st.info("No orders yet. Use the **Open new order** tab to create one.")
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

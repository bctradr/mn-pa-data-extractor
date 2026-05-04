"""
2_Order_Queue.py
════════════════
Order queue — horizontal table of all saved orders. Click a row to select
it, then "Open Selection for Review" to load the order's PDFs into the PA
Extractor for OET review and CSV publish.

Status states:
  - 'new'         — saved by closer, not yet reviewed
  - 'in_review'   — opened in PA Extractor, OET reviewing
  - 'submitted'   — CSV published, ready for TPS upload
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from supabase_client import (
    list_orders,
    get_order_documents,
    download_documents,
    set_order_status,
    delete_order,
)
from ui_theme import apply_theme, section_bar


try:
    st.set_page_config(page_title="Order Queue", page_icon="📋", layout="wide")
except Exception:
    pass

apply_theme()


st.title("📋 Order Queue")
st.caption("All saved orders. Click a row to select it, then open it for review in the PA Extractor.")


# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def _format_compact_time(s: str) -> str:
    """Compact timestamp like '04/27 14:32'."""
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        return s[:16]


def _status_label(status: str) -> str:
    if status == "submitted":
        return "🟢 Submitted"
    if status == "in_review":
        return "🟡 In Review"
    return "🔵 New"


# ══════════════════════════════════════════════════════
# LOAD ORDERS
# ══════════════════════════════════════════════════════

refresh_col, _ = st.columns([1, 9])
with refresh_col:
    if st.button("🔄 Refresh"):
        st.rerun()

try:
    orders = list_orders()
except Exception as e:
    st.error(f"Failed to load orders: {e}")
    st.stop()

if not orders:
    st.info("No orders yet. Use the **New Order** page (sidebar) to create one.")
    st.stop()


# ══════════════════════════════════════════════════════
# BUILD TABLE
# ══════════════════════════════════════════════════════

# Pre-fetch all documents in one pass so the action panel can show file lists.
docs_by_order: dict = {}
for o in orders:
    try:
        docs_by_order[o["id"]] = get_order_documents(o["id"])
    except Exception:
        docs_by_order[o["id"]] = []

rows = []
for o in orders:
    rows.append({
        "Date/Time": _format_compact_time(o.get("created_at", "")),
        "Txn": o.get("transaction_type") or "",
        "Order Type": o.get("order_type") or "",
        "State": o.get("property_state") or "",
        "Client": o.get("client_name_referrer") or "",
        "Broker": o.get("client_broker") or "",
        "Lender": o.get("lender") or "",
        "Mtg Broker": o.get("mortgage_broker") or "",
        "Plat": o.get("plat_and_assessments") or "",
        "Closer": o.get("closer") or "",
        "Asst": o.get("assistant_main_contact") or "",
        "UW": o.get("underwriter_code") or "",
        "Office": o.get("office") or "",
        "Contact OTA": o.get("business_dev_contact_other_agent") or "",
        "Status": _status_label(o.get("status", "new")),
    })

df = pd.DataFrame(rows)


# ══════════════════════════════════════════════════════
# DISPLAY TABLE WITH ROW SELECTION
# ══════════════════════════════════════════════════════

section_bar(f"Order Queue — {len(orders)} order(s) (newest first)")
st.caption("Click a column header to sort · click a row to see actions below.")

selection = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Date/Time": st.column_config.TextColumn(width="small"),
        "Txn": st.column_config.TextColumn(width="small"),
        "Order Type": st.column_config.TextColumn(width="medium"),
        "State": st.column_config.TextColumn(width="small"),
        "Client": st.column_config.TextColumn(width="medium"),
    },
)


# ══════════════════════════════════════════════════════
# ACTION PANEL — appears when a row is selected
# ══════════════════════════════════════════════════════

selected_rows = selection.selection.rows if selection and selection.selection else []
if not selected_rows:
    st.info("👆 Select a row above to see actions for that order.")
    st.stop()

selected_idx = selected_rows[0]
order = orders[selected_idx]
order_id = order["id"]
status = order.get("status", "new")

st.divider()

# Header
st.subheader(
    f"Selected: {order.get('client_name_referrer') or '—'} · "
    f"{order.get('transaction_type') or '—'} · {order.get('order_type') or '—'}"
)
caption_parts = [
    f"Saved {_format_compact_time(order.get('created_at', ''))}",
    f"Closer {order.get('closer') or '—'} ({order.get('underwriter_code') or '—'})",
    f"Office {order.get('office') or '—'}",
    f"State {order.get('property_state') or '—'}",
]
if order.get("template_name"):
    caption_parts.append(f"Template: **{order['template_name']}**")
if order.get("is_new_construction"):
    caption_parts.append("🏗️ New Construction")
st.caption(" · ".join(caption_parts))

# Full notes
full_notes = order.get("additional_notes")
if full_notes:
    with st.expander("📝 Full notes", expanded=False):
        st.write(full_notes)

# Document list
docs = docs_by_order.get(order_id, [])
if docs:
    with st.expander(f"📄 Documents ({len(docs)})", expanded=False):
        for d in docs:
            st.caption(f"• {d['filename']}")
else:
    st.warning("No documents attached to this order.")


# ──────────────────────────────────────────────────────
# Open Selection for Review — choose layout
# ──────────────────────────────────────────────────────

st.markdown("")  # spacer

# Button label changes based on status
if status == "submitted":
    label_prefix = "📂 Re-open"
    help_suffix = "(already submitted — to revise extraction or re-publish CSV)"
elif status == "in_review":
    label_prefix = "📂 Re-open"
    help_suffix = "(continue reviewing)"
else:
    label_prefix = "📂 Open"
    help_suffix = "(load PDFs and start review)"

if not docs:
    st.button(f"{label_prefix} for Review", type="primary", disabled=True, help="No documents to review.")
else:
    cb1, cb2, _ = st.columns([1, 1, 2])

    def _open_for_review(target_page: str):
        try:
            files = download_documents(order_id)
            st.session_state["review_order_id"] = order_id
            st.session_state["review_order"] = order
            st.session_state["review_files"] = files
            st.session_state.pop("extraction", None)
            st.session_state.pop("filename", None)
            if status == "new":
                set_order_status(order_id, "in_review")
            st.switch_page(target_page)
        except Exception as e:
            st.error(f"Failed to open for review: {e}")

    with cb1:
        if st.button(
            f"{label_prefix} — Categorical (v1)",
            type="primary",
            help=f"Open in v1 PA Extractor (fields grouped by category) {help_suffix}",
            key=f"open_v1_{order_id}",
            use_container_width=True,
        ):
            with st.spinner("Loading documents and preparing review..."):
                _open_for_review("pages/3_PA_Extractor.py")

    with cb2:
        if st.button(
            f"{label_prefix} — PA Page Order (v2)",
            help=f"Open in v2 PA Extractor (fields grouped by PA page) {help_suffix}",
            key=f"open_v2_{order_id}",
            use_container_width=True,
        ):
            with st.spinner("Loading documents and preparing review..."):
                _open_for_review("pages/4_PA_Extractor_v2.py")


# ──────────────────────────────────────────────────────
# Delete (always available)
# ──────────────────────────────────────────────────────

st.divider()

confirm_key = f"confirm_delete_{order_id}"
if st.session_state.get(confirm_key):
    cdel_l, cdel_r = st.columns([1, 4])
    with cdel_l:
        if st.button("⚠️ Confirm delete", key=f"confirm_{order_id}"):
            try:
                delete_order(order_id)
                st.session_state[confirm_key] = False
                st.success("Order deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
    with cdel_r:
        if st.button("Cancel", key=f"cancel_{order_id}"):
            st.session_state[confirm_key] = False
            st.rerun()
else:
    if st.button("🗑️ Delete order", key=f"delete_{order_id}"):
        st.session_state[confirm_key] = True
        st.rerun()

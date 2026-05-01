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
from ui_theme import apply_theme


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

st.caption(f"{len(orders)} order(s) — newest first. Click a column header to sort.")

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
# Open Selection for Review
# ──────────────────────────────────────────────────────

st.markdown("")  # spacer

# Button label changes based on status
if status == "submitted":
    button_label = "📂 Re-open in Review (already submitted)"
    help_text = "Re-open this order to revise extraction or re-publish CSV."
elif status == "in_review":
    button_label = "📂 Re-open in Review"
    help_text = "Continue reviewing this order in the PA Extractor."
else:  # 'new' or anything else
    button_label = "📂 Open Selection for Review"
    help_text = "Load PDFs into the PA Extractor for OET review and CSV publish."

if not docs:
    st.button(button_label, type="primary", disabled=True, help="No documents to review.")
else:
    if st.button(button_label, type="primary", help=help_text, key=f"open_{order_id}"):
        with st.spinner("Loading documents and preparing review..."):
            try:
                # Download PDFs from Supabase into session state
                files = download_documents(order_id)  # [(bytes, filename), ...]
                st.session_state["review_order_id"] = order_id
                st.session_state["review_order"] = order
                st.session_state["review_files"] = files
                # Clear any prior extraction so PA Extractor re-runs fresh
                st.session_state.pop("extraction", None)
                st.session_state.pop("filename", None)

                # Flip status to 'in_review' (only if currently 'new')
                if status == "new":
                    set_order_status(order_id, "in_review")

                # Navigate to the PA Extractor page
                st.switch_page("pages/3_PA_Extractor.py")
            except Exception as e:
                st.error(f"Failed to open for review: {e}")


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

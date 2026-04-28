"""
1_New_Order.py
══════════════
Open New Order page — upload PDFs, fill in intake fields, save to queue.
"""

import streamlit as st

from assignment_rules import CLOSERS, OFFICES, ORDER_TYPES, get_assignment
from supabase_client import create_order


# Page metadata controls the sidebar entry's label and icon.
# (Filename uses ASCII only; emoji shows up here.)
try:
    st.set_page_config(page_title="New Order", page_icon="📝", layout="wide")
except Exception:
    # set_page_config can only run once per session; ignore on subsequent navigations.
    pass


st.title("📝 Open New Order")
st.caption("Upload documents and enter order details. The order will appear in the **Order Queue** for extraction.")


# ── File uploader ────────────────────────────────────
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


# ── Order details ────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    order_type = st.selectbox(
        "Order Type *",
        options=[""] + ORDER_TYPES,
        key="no_order_type",
    )
    client_name = st.text_input("Client Name (Referrer) *", key="no_client_name")
    lender = st.text_input("Lender", key="no_lender")
    sales_team_contact = st.selectbox(
        "Sales Team to Contact Other Agent *",
        options=["", "Yes", "No"],
        key="no_sales_team_contact",
    )
with col2:
    client_broker = st.text_input("Client Broker", key="no_client_broker")
    mortgage_broker = st.text_input("Mortgage Broker", key="no_mortgage_broker")
    plat = st.selectbox("Plat & Assessments *", options=["", "Yes", "No"], key="no_plat")


# ── Closer-driven assignment ─────────────────────────
st.markdown("**Closer-driven assignment**")
st.caption("Underwriter, office, and assistant auto-fill when you pick a closer. All three are editable.")

col3, col4 = st.columns(2)
with col3:
    closer = st.selectbox(
        "Closer *",
        options=[""] + CLOSERS,
        key="no_closer",
    )

# Compute defaults from closer + order_type. Widget keys include closer/order_type
# so the values reset to fresh defaults on change.
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


# ── Save ─────────────────────────────────────────────
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
    if not plat:
        errors.append("Plat & Assessments is required.")
    if not sales_team_contact:
        errors.append("Sales Team to Contact Other Agent is required.")
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
                    "business_dev_contact_other_agent": sales_team_contact,
                    "additional_notes": notes,
                }
                files = [(f.name, f.read()) for f in uploaded]
                order_id = create_order(intake, files)
                st.success("✅ Order saved. View it in the **Order Queue** page (sidebar).")
                st.caption(f"Internal ID: {order_id}")
            except Exception as e:
                st.error(f"Failed to save: {e}")

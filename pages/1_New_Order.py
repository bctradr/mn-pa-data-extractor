"""
1_New_Order.py
══════════════
Open New Order page — upload docs, fill in intake fields, save to queue.

Layout: SoftPro-style bordered sections with blue header bars.
Uses Streamlit's native st.container(border=True) plus a small CSS
override to color the borders and add header bars.
"""

import streamlit as st

from assignment_rules import CLOSERS, OFFICES, get_assignment
from transaction_categories import (
    TRANSACTION_TYPES,
    ORDER_TYPES_BY_TXN,
    PROPERTY_STATES,
    get_template_name,
)
from supabase_client import create_order


try:
    st.set_page_config(page_title="New Order", page_icon="📝", layout="wide")
except Exception:
    pass


# ══════════════════════════════════════════════════════
# STYLING — SoftPro-style sectioned layout
# ══════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Tighten top spacing */
    .block-container { padding-top: 1.5rem !important; }

    /* Page title */
    .new-order-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #0f3a5f;
        margin: 0 0 0.25rem 0;
    }
    .new-order-caption {
        font-size: 0.85rem;
        color: #555;
        margin-bottom: 0.5rem;
    }

    /* SoftPro-style blue section header */
    .softpro-section-header {
        background: #0f3a5f;
        color: white;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 4px 4px 0 0;
        margin-top: 0.6rem;
        margin-bottom: -8px;  /* overlap with bordered container below */
        position: relative;
        z-index: 1;
    }

    /* Customize Streamlit's native border-container to match SoftPro */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #c8d4e0 !important;
        border-radius: 0 4px 4px 4px !important;
        background: #fafcfe;
    }
</style>
""", unsafe_allow_html=True)


def section_header(title: str):
    """Render a SoftPro-style blue header bar."""
    st.markdown(f'<div class="softpro-section-header">{title}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# PAGE TITLE
# ══════════════════════════════════════════════════════

st.markdown('<div class="new-order-title">📝 Open New Order</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="new-order-caption">Upload documents and enter order details — '
    'order will appear in the Order Queue.</div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════
# SECTION 1 — Documents
# ══════════════════════════════════════════════════════

section_header("Documents")
with st.container(border=True):
    uploaded = st.file_uploader(
        "Drag and drop new order docs and emails here",
        type=["pdf", "docx", "msg", "eml"],
        accept_multiple_files=True,
        help="PDF, Word docs, or Outlook .msg / .eml emails. Email files are stored as-is.",
        key="no_uploader",
        label_visibility="collapsed",
    )
    if uploaded:
        st.success(f"Loaded {len(uploaded)} file(s)")
        cols = st.columns(3)
        for i, f in enumerate(uploaded):
            cols[i % 3].caption(f"• {f.name} ({f.size / 1024:.0f} KB)")


# ══════════════════════════════════════════════════════
# SECTION 2 — Transaction Details
# ══════════════════════════════════════════════════════

section_header("Transaction Details")
with st.container(border=True):
    ttype_col, ot_col, state_col = st.columns([1.2, 1, 0.9])
    with ttype_col:
        transaction_type = st.radio(
            "Transaction Type *",
            options=TRANSACTION_TYPES,
            horizontal=True,
            key="no_txn_type",
        )
    with ot_col:
        order_type_options = [""] + ORDER_TYPES_BY_TXN.get(transaction_type, [])
        order_type = st.selectbox(
            "Order Type *",
            options=order_type_options,
            key=f"no_order_type_{transaction_type}",
        )
    with state_col:
        property_state = st.selectbox(
            "Property State *",
            options=[""] + PROPERTY_STATES,
            index=1,  # default to MN
            key="no_property_state",
            help="Refinance template depends on property state.",
        )

    is_new_construction = False
    if transaction_type == "Purchase":
        is_new_construction = st.checkbox(
            "🏗️ This is New Construction",
            key="no_new_construction",
            help="Adds a 'This is New Construction' note to the order.",
        )

    template_name = get_template_name(transaction_type, order_type, property_state)
    if template_name:
        st.caption(f"📄 Template: **{template_name}**")
    elif transaction_type and order_type:
        st.caption("📄 Template: _not yet resolved (check property state)_")


# ══════════════════════════════════════════════════════
# SECTION 3 — Order Information
# ══════════════════════════════════════════════════════

section_header("Order Information")
with st.container(border=True):
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        client_name = st.text_input("Client Name (Referrer) *", key="no_client_name")
        lender = st.text_input("Lender", key="no_lender")
        plat = st.selectbox("Plat & Assessments *", options=["", "Yes", "No"], key="no_plat")
    with info_col2:
        client_broker = st.text_input("Client Broker", key="no_client_broker")
        mortgage_broker = st.text_input("Mortgage Broker", key="no_mortgage_broker")
        sales_team_contact = st.selectbox(
            "Sales Team to Contact Other Agent *",
            options=["", "Yes", "No"],
            key="no_sales_team_contact",
        )


# ══════════════════════════════════════════════════════
# SECTION 4 — Closer Assignment
# ══════════════════════════════════════════════════════

section_header("Closer Assignment")
with st.container(border=True):
    st.caption("Underwriter, office, and assistant auto-fill based on closer. All editable.")

    closer_col1, closer_col2 = st.columns(2)
    with closer_col1:
        closer = st.selectbox(
            "Closer *",
            options=[""] + CLOSERS,
            key="no_closer",
        )

        defaults = get_assignment(closer, order_type)
        rekey = f"{closer}__{order_type}"

        uw_code = st.text_input(
            "Underwriter Code",
            value=defaults["underwriter_code"],
            help="Auto-filled from closer · editable",
            key=f"no_uw_{rekey}",
        )

    with closer_col2:
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
        assistant = st.text_input(
            "Assistant & Main Contact *",
            value=defaults["assistant"],
            help="Auto-filled from closer + order type · editable",
            key=f"no_assistant_{rekey}",
        )


# ══════════════════════════════════════════════════════
# SECTION 5 — Notes
# ══════════════════════════════════════════════════════

section_header("Notes")
with st.container(border=True):
    notes = st.text_area(
        "Additional Notes",
        height=68,
        key="no_notes",
        label_visibility="collapsed",
        placeholder="Special instructions, deadlines, context for the closing team…",
    )


# ══════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════

st.markdown("")
col_save_l, col_save_r = st.columns([4, 1])
with col_save_r:
    save_clicked = st.button("💾 Save Order", type="primary", use_container_width=True)

if save_clicked:
    errors = []
    if not uploaded:
        errors.append("At least one document must be uploaded.")
    if not transaction_type:
        errors.append("Transaction Type is required.")
    if not order_type:
        errors.append("Order Type is required.")
    if not property_state:
        errors.append("Property State is required.")
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

    if errors:
        for e in errors:
            st.error(e)
    else:
        final_notes = notes or ""
        if is_new_construction:
            nc_text = "This is New Construction."
            final_notes = nc_text + (" " + final_notes if final_notes else "")

        with st.spinner("Saving order and uploading documents..."):
            try:
                intake = {
                    "transaction_type": transaction_type,
                    "order_type": order_type,
                    "property_state": property_state,
                    "is_new_construction": bool(is_new_construction),
                    "template_name": template_name,
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
                    "additional_notes": final_notes,
                }
                files = [(f.name, f.read()) for f in uploaded]
                order_id = create_order(intake, files)
                st.success("✅ Order saved. View it in the **Order Queue** page (sidebar).")
                st.caption(f"Internal ID: {order_id}")
            except Exception as e:
                st.error(f"Failed to save: {e}")

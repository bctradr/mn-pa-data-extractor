"""
1_New_Order.py
══════════════
Open New Order page — upload docs, fill in intake fields, save to queue.
"""

import streamlit as st

from assignment_rules import CLOSERS, OFFICES, ORDER_TYPES, get_assignment
from supabase_client import create_order


# Page metadata controls the sidebar entry's label and icon.
# (Filename uses ASCII only; emoji shows up here.)
try:
    st.set_page_config(page_title="New Order", page_icon="📝", layout="wide")
except Exception:
    pass


# Tighten top spacing and shrink the page title so the form sits high on screen.
st.markdown("""
<style>
    /* Pull main block up — Streamlit's default top padding is generous */
    .block-container { padding-top: 1.5rem !important; }
    /* Smaller page title */
    .new-order-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #0f3a5f;
        margin: 0 0 0.25rem 0;
    }
    .new-order-caption {
        font-size: 0.85rem;
        color: #555;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="new-order-title">📝 Open New Order</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="new-order-caption">Upload documents and enter order details — '
    'order will appear in the Order Queue.</div>',
    unsafe_allow_html=True,
)


# ── File uploader ────────────────────────────────────
uploaded = st.file_uploader(
    "Drag and drop new order docs and emails here",
    type=["pdf", "docx", "msg", "eml"],
    accept_multiple_files=True,
    help="PDF, Word docs, or Outlook .msg / .eml emails. Extraction figures out which is which.",
    key="no_uploader",
)
if uploaded:
    st.success(f"Loaded {len(uploaded)} file(s)")
    cols = st.columns(3)
    for i, f in enumerate(uploaded):
        cols[i % 3].caption(f"• {f.name} ({f.size / 1024:.0f} KB)")


st.markdown("")  # tiny spacer


# ── Order details — 3 columns ───────────────────────
col1, col2, col3 = st.columns(3)
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
with col3:
    closer = st.selectbox(
        "Closer *",
        options=[""] + CLOSERS,
        key="no_closer",
    )

    # Auto-fill defaults from closer + order_type. Widget keys include closer/order_type
    # so the values reset to fresh defaults when either changes.
    defaults = get_assignment(closer, order_type)
    rekey = f"{closer}__{order_type}"

    uw_code = st.text_input(
        "Underwriter Code",
        value=defaults["underwriter_code"],
        help="Auto-filled from closer · editable",
        key=f"no_uw_{rekey}",
    )

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


notes = st.text_area("Additional Notes", height=68, key="no_notes")


# ── Save ─────────────────────────────────────────────
col_save_l, col_save_r = st.columns([4, 1])
with col_save_r:
    save_clicked = st.button("💾 Save Order", type="primary", use_container_width=True)

if save_clicked:
    errors = []
    if not uploaded:
        errors.append("At least one document must be uploaded.")
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

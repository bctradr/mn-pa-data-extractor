"""
streamlit_app.py
Entry point for the multi-page Streamlit app.
"""

import streamlit as st
from ui_theme import apply_theme

st.set_page_config(
    page_title="MN PA Tools",
    page_icon="🏠",
    layout="wide",
)

apply_theme()

st.title("🏠 MN Purchase Agreement Tools")
st.caption("Pick a workflow from the sidebar.")

st.markdown("""
### Workflows

**📝 New Order**
Upload purchase agreement and supporting documents, fill intake fields, save to queue.

**📋 Order Queue**
View saved orders. Run extractor, review, export.

**📄 PA Extractor**
Standalone extractor — upload PA/addenda, extract, review, export.

**💧 Water Bill Requests**
Create and track water bill requests to municipalities; log followups; receive bill PDFs.
""")

# TODO(water-bills Phase 2): Auto-create a water_bill_request when a new order is saved.
# Call water_bills.create_request_from_order(order_id, order_data) from
# pages/1_New_Order.py immediately after a successful create_order() call.
# Field-mapping logic (property address, parties, closing date, closer/assistant)
# is already implemented in water_bills.create_request_from_order().
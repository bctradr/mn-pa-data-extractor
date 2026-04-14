"""
MN Purchase Agreement Extractor
================================
Streamlit app that extracts structured data from Minnesota 
real estate purchase agreements using the Claude API.

Setup:
    pip install streamlit anthropic pandas
    export ANTHROPIC_API_KEY=sk-ant-...
    streamlit run app.py
"""

import streamlit as st
import anthropic
import base64
import json
import pandas as pd
from datetime import datetime
from io import BytesIO

# ── Import the extraction prompt ──────────────────────
from extraction_prompt import EXTRACTION_SYSTEM_PROMPT
from summary_generator import generate_text_summary, generate_html_summary


# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="MN PA Extractor",
    page_icon="🏠",
    layout="wide",
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


# ══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════

@st.cache_resource
def get_client():
    """Initialize Anthropic client (cached across reruns)."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    return anthropic.Anthropic(api_key=api_key)


def extract_from_pdf(pdf_bytes: bytes) -> dict:
    """Send PDF to Claude and return parsed JSON."""
    client = get_client()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all fields from this Minnesota purchase agreement. Return only JSON.",
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    # Strip markdown fences if Claude includes them despite instructions
    raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw_text)


def flatten_for_csv(data: dict) -> dict:
    """Flatten nested extraction JSON into a single-row dict for CSV export."""
    flat = {}

    # Parties
    buyers = data.get("parties", {}).get("buyers", [])
    flat["buyer_names"] = "; ".join(b.get("name", "") for b in buyers)
    flat["buyer_entity_types"] = "; ".join(b.get("entity_type", "") for b in buyers)

    sellers = data.get("parties", {}).get("sellers", [])
    flat["seller_names"] = "; ".join(s.get("name", "") for s in sellers)
    flat["seller_entity_types"] = "; ".join(s.get("entity_type", "") for s in sellers)

    # Property
    prop = data.get("property", {})
    for key in ["street_address", "city", "county", "state", "zip_code", "legal_description", "pid"]:
        flat[key] = prop.get(key)

    # Financial
    fin = data.get("financial", {})
    for key in ["purchase_price", "earnest_money_amount", "earnest_money_holder",
                "financing_type", "down_payment_amount", "seller_concessions"]:
        flat[key] = fin.get(key)

    # Dates
    dates = data.get("dates", {})
    for key in dates:
        flat[key] = dates.get(key)

    # Title & Closing
    tc = data.get("title_and_closing", {})
    for key in tc:
        flat[key] = tc.get(key)

    # Contingencies
    cont = data.get("contingencies", {})
    for key in ["financing_contingency", "inspection_contingency",
                "appraisal_contingency", "sale_of_buyers_property"]:
        flat[key] = cont.get(key)
    flat["other_contingencies"] = "; ".join(cont.get("other_contingencies", []))

    # MN Disclosures
    mn = data.get("mn_specific_disclosures", {})
    for key in mn:
        flat[key] = mn.get(key)

    # Addenda count
    flat["addenda_count"] = len(data.get("addenda", []))
    flat["addenda_titles"] = "; ".join(
        a.get("addendum_title", "") for a in data.get("addenda", [])
    )

    # Flags count
    flags = data.get("extraction_metadata", {}).get("flags", [])
    flat["flag_count"] = len(flags)

    return flat


# ══════════════════════════════════════════════════════
# UI LAYOUT
# ══════════════════════════════════════════════════════

st.title("🏠 MN Purchase Agreement Extractor")
st.caption("Upload a Minnesota purchase agreement PDF → review extracted fields → export for title production")

# ── Sidebar: Upload ──────────────────────────────────
with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader(
        "Purchase Agreement (PDF)",
        type=["pdf"],
        help="Standard MN residential purchase agreement with any addenda",
    )

    if uploaded_file:
        st.success(f"Loaded: {uploaded_file.name}")
        st.caption(f"{uploaded_file.size / 1024:.0f} KB")

    st.divider()
    st.caption("v0.1 — Uses Claude API for extraction")

# ── Main area ─────────────────────────────────────────
if uploaded_file is None:
    st.info("👈 Upload a purchase agreement PDF to get started.")
    st.stop()

# Extract button
if st.button("🔍 Extract Fields", type="primary", use_container_width=True):
    with st.spinner("Reading agreement and extracting fields..."):
        try:
            result = extract_from_pdf(uploaded_file.read())
            st.session_state["extraction"] = result
            st.session_state["filename"] = uploaded_file.name
        except json.JSONDecodeError as e:
            st.error(f"Claude returned invalid JSON. Try re-uploading. Error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

# Show results if we have them
if "extraction" not in st.session_state:
    st.stop()

data = st.session_state["extraction"]

# ── Flags / warnings at top ──────────────────────────
flags = data.get("extraction_metadata", {}).get("flags", [])
if flags:
    st.warning(f"⚠️ {len(flags)} field(s) flagged for review")
    for flag in flags:
        st.caption(f"**{flag['field']}** — {flag['issue']}: {flag['note']}")

# ── Tabbed sections for review/editing ────────────────
tab_parties, tab_property, tab_financial, tab_dates, tab_title, tab_contingencies, tab_mn, tab_addenda, tab_json = st.tabs([
    "Parties", "Property", "Financial", "Dates",
    "Title/Closing", "Contingencies", "MN Disclosures", "Addenda", "Raw JSON"
])

with tab_parties:
    st.subheader("Buyers")
    for i, buyer in enumerate(data.get("parties", {}).get("buyers", [])):
        col1, col2 = st.columns(2)
        buyer["name"] = col1.text_input(f"Buyer {i+1} Name", value=buyer.get("name", ""), key=f"buyer_name_{i}")
        buyer["entity_type"] = col2.selectbox(
            f"Buyer {i+1} Entity Type", 
            ["individual", "trust", "llc", "corporation", "partnership", "other"],
            index=["individual", "trust", "llc", "corporation", "partnership", "other"].index(buyer.get("entity_type", "individual")),
            key=f"buyer_entity_{i}"
        )

    st.subheader("Sellers")
    for i, seller in enumerate(data.get("parties", {}).get("sellers", [])):
        col1, col2 = st.columns(2)
        seller["name"] = col1.text_input(f"Seller {i+1} Name", value=seller.get("name", ""), key=f"seller_name_{i}")
        seller["entity_type"] = col2.selectbox(
            f"Seller {i+1} Entity Type",
            ["individual", "trust", "llc", "corporation", "partnership", "other"],
            index=["individual", "trust", "llc", "corporation", "partnership", "other"].index(seller.get("entity_type", "individual")),
            key=f"seller_entity_{i}"
        )

with tab_property:
    prop = data.get("property", {})
    col1, col2 = st.columns(2)
    prop["street_address"] = col1.text_input("Street Address", value=prop.get("street_address", ""))
    prop["city"] = col2.text_input("City", value=prop.get("city", ""))
    col1, col2, col3 = st.columns(3)
    prop["county"] = col1.text_input("County", value=prop.get("county", ""))
    prop["zip_code"] = col2.text_input("Zip Code", value=prop.get("zip_code", ""))
    prop["pid"] = col3.text_input("PID / Parcel #", value=prop.get("pid", "") or "")
    prop["legal_description"] = st.text_area("Legal Description", value=prop.get("legal_description", ""), height=100)

with tab_financial:
    fin = data.get("financial", {})
    col1, col2, col3 = st.columns(3)
    fin["purchase_price"] = col1.number_input("Purchase Price", value=float(fin.get("purchase_price", 0)))
    fin["earnest_money_amount"] = col2.number_input("Earnest Money", value=float(fin.get("earnest_money_amount", 0)))
    fin["seller_concessions"] = col3.number_input("Seller Concessions", value=float(fin.get("seller_concessions", 0) or 0))
    col1, col2 = st.columns(2)
    fin["financing_type"] = col1.selectbox(
        "Financing Type",
        ["conventional", "fha", "va", "usda", "cash", "contract_for_deed", "assumption", "other"],
        index=["conventional", "fha", "va", "usda", "cash", "contract_for_deed", "assumption", "other"].index(fin.get("financing_type", "conventional")),
    )
    fin["earnest_money_holder"] = col2.text_input("Earnest Money Holder", value=fin.get("earnest_money_holder", "") or "")

with tab_dates:
    dates = data.get("dates", {})
    date_fields = [
        ("closing_date", "Closing Date"),
        ("possession_date", "Possession Date"),
        ("acceptance_deadline", "Acceptance Deadline"),
        ("title_commitment_deadline", "Title Commitment Deadline"),
        ("inspection_deadline", "Inspection Deadline"),
        ("financing_contingency_deadline", "Financing Contingency Deadline"),
        ("appraisal_contingency_deadline", "Appraisal Contingency Deadline"),
        ("buyer_signature_date", "Buyer Signature Date"),
        ("seller_signature_date", "Seller Signature Date"),
    ]
    col1, col2 = st.columns(2)
    for i, (key, label) in enumerate(date_fields):
        target = col1 if i % 2 == 0 else col2
        dates[key] = target.text_input(label, value=dates.get(key, "") or "")

with tab_title:
    tc = data.get("title_and_closing", {})
    col1, col2 = st.columns(2)
    tc["title_company"] = col1.text_input("Title Company", value=tc.get("title_company", "") or "")
    tc["closing_agent"] = col2.text_input("Closing Agent", value=tc.get("closing_agent", "") or "")
    col1, col2 = st.columns(2)
    tc["listing_agent_name"] = col1.text_input("Listing Agent", value=tc.get("listing_agent_name", "") or "")
    tc["listing_brokerage"] = col2.text_input("Listing Brokerage", value=tc.get("listing_brokerage", "") or "")
    col1, col2 = st.columns(2)
    tc["selling_agent_name"] = col1.text_input("Selling Agent", value=tc.get("selling_agent_name", "") or "")
    tc["selling_brokerage"] = col2.text_input("Selling Brokerage", value=tc.get("selling_brokerage", "") or "")

with tab_contingencies:
    cont = data.get("contingencies", {})
    col1, col2 = st.columns(2)
    cont["financing_contingency"] = col1.checkbox("Financing Contingency", value=cont.get("financing_contingency", False))
    cont["inspection_contingency"] = col2.checkbox("Inspection Contingency", value=cont.get("inspection_contingency", False))
    col1, col2 = st.columns(2)
    cont["appraisal_contingency"] = col1.checkbox("Appraisal Contingency", value=cont.get("appraisal_contingency", False))
    cont["sale_of_buyers_property"] = col2.checkbox("Sale of Buyer's Property", value=cont.get("sale_of_buyers_property", False))
    other = cont.get("other_contingencies", [])
    cont["other_contingencies_text"] = st.text_input("Other Contingencies (semicolon-separated)", value="; ".join(other))

with tab_mn:
    mn = data.get("mn_specific_disclosures", {})
    col1, col2, col3 = st.columns(3)
    mn["well_disclosure_present"] = col1.checkbox("Well Disclosure Present", value=mn.get("well_disclosure_present", False))
    mn["well_number"] = col1.text_input("Well Number (MDH)", value=mn.get("well_number", "") or "")
    mn["septic_disclosure_present"] = col2.checkbox("Septic Disclosure Present", value=mn.get("septic_disclosure_present", False))
    mn["septic_system_type"] = col2.text_input("Septic System Type", value=mn.get("septic_system_type", "") or "")
    mn["hoa_present"] = col3.checkbox("HOA Present", value=mn.get("hoa_present", False))
    mn["hoa_name"] = col3.text_input("HOA Name", value=mn.get("hoa_name", "") or "")

with tab_addenda:
    addenda = data.get("addenda", [])
    if addenda:
        for i, add in enumerate(addenda):
            st.markdown(f"**{add.get('addendum_title', f'Addendum {i+1}')}**")
            st.caption(add.get("summary", ""))
    else:
        st.info("No addenda detected.")

with tab_json:
    st.json(data)


# ── Export ────────────────────────────────────────────
st.divider()
st.subheader("Export")

fname = st.session_state.get("filename", "output")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Text summary — best for pasting into TPS notes
    text_summary = generate_text_summary(data, fname)
    st.download_button(
        "📋 Summary (Text)",
        data=text_summary.encode("utf-8"),
        file_name=f"summary_{fname}.txt",
        mime="text/plain",
        use_container_width=True,
        help="Plain text — paste directly into TPS notes",
    )

with col2:
    # HTML summary — formatted, printable
    html_summary = generate_html_summary(data, fname)
    st.download_button(
        "🌐 Summary (HTML)",
        data=html_summary.encode("utf-8"),
        file_name=f"summary_{fname}.html",
        mime="text/html",
        use_container_width=True,
        help="Formatted summary — open in browser or print",
    )

with col3:
    # CSV export (flattened single row)
    flat = flatten_for_csv(data)
    df = pd.DataFrame([flat])
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Data (CSV)",
        data=csv_bytes,
        file_name=f"extraction_{fname}.csv",
        mime="text/csv",
        use_container_width=True,
        help="Flat CSV — one row, all fields as columns",
    )

with col4:
    # JSON export (full nested)
    json_bytes = json.dumps(data, indent=2).encode("utf-8")
    st.download_button(
        "📥 Data (JSON)",
        data=json_bytes,
        file_name=f"extraction_{fname}.json",
        mime="application/json",
        use_container_width=True,
        help="Full structured data — for integrations",
    )

# Preview the text summary inline for quick copy-paste
with st.expander("📋 Preview Text Summary (click to copy)"):
    st.code(text_summary, language=None)


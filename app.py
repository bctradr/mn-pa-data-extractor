"""
MN Purchase Agreement Extractor
================================
Streamlit app that extracts structured data from Minnesota 
real estate purchase agreements using the Claude API.

Setup:
    pip install streamlit anthropic pandas
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

# ── Custom theme CSS ─────────────────────────────────
st.markdown("""
<style>
    /* Header bar */
    header[data-testid="stHeader"] {
        background-color: #1a4e7a;
    }
    
    /* Main title */
    h1 {
        color: #1a4e7a !important;
    }
    
    /* Tab styling */
    button[data-baseweb="tab"] {
        color: #1a4e7a !important;
        font-weight: 500;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1a4e7a !important;
        border-bottom-color: #1a4e7a !important;
    }
    
    /* Subheaders */
    h2, h3 {
        color: #2a6496 !important;
    }
    
    /* Primary button */
    button[kind="primary"], .stButton > button[kind="primary"] {
        background-color: #1a4e7a !important;
        border-color: #1a4e7a !important;
    }
    
    /* Info box */
    div[data-testid="stAlert"] {
        border-left-color: #1a4e7a;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #e8f0f8;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2 {
        color: #1a4e7a !important;
    }
    
    /* Dynamic text area - auto height */
    .dynamic-text {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 8px 12px;
        margin-bottom: 8px;
        font-family: inherit;
        font-size: 14px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .dynamic-text-label {
        font-size: 14px;
        color: #555;
        margin-bottom: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════

@st.cache_resource
def get_client():
    """Initialize Anthropic client (cached across reruns)."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    return anthropic.Anthropic(api_key=api_key)


def extract_from_pdf(pdf_files: list) -> dict:
    """Send one or more PDFs to Claude and return parsed JSON."""
    client = get_client()

    # Build document blocks for each PDF
    content = []
    for pdf_bytes, filename in pdf_files:
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        content.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        })
    content.append({
        "type": "text",
        "text": "Extract all fields from this Minnesota purchase agreement. All uploaded documents are part of the same transaction. Return only JSON.",
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )

    raw_text = response.content[0].text
    # Strip markdown fences if Claude includes them despite instructions
    raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw_text)


def get_line_ref(data: dict, field_name: str) -> str:
    """Get the PA line number reference for a field, formatted for display."""
    source_lines = data.get("extraction_metadata", {}).get("source_lines", {})
    line = source_lines.get(field_name)
    if line:
        # If it's just a number, prefix with "Line"
        if str(line).isdigit():
            return f"Line {line}"
        return str(line)
    return ""


def format_currency(value) -> str:
    """Format a number as currency string for text_input display."""
    if value is None or value == 0:
        return ""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def parse_currency(text: str) -> float:
    """Parse a currency string back to a float."""
    if not text or text.strip() == "":
        return 0.0
    # Remove $, commas, spaces
    cleaned = text.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def dynamic_text(label: str, value: str, key: str = None):
    """Display text in an auto-sized box — no scrolling needed."""
    if not value:
        return
    st.markdown(f'<div class="dynamic-text-label">{label}</div>'
                f'<div class="dynamic-text">{value}</div>', 
                unsafe_allow_html=True)


def auto_height(text: str, min_height: int = 68, chars_per_line: int = 80) -> int:
    """Calculate text_area height based on content length."""
    if not text:
        return min_height
    lines = text.count('\n') + 1
    wrapped_lines = max(lines, len(text) // chars_per_line + 1)
    return max(min_height, wrapped_lines * 24 + 44)


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
    for key in ["street_address", "unit_no", "city", "county", "state", "zip_code", "legal_description", "pid"]:
        flat[key] = prop.get(key)

    # Financial
    fin = data.get("financial", {})
    for key in ["purchase_price", "earnest_money_amount", "earnest_money_holder",
                "financing_type", "down_payment_amount", "seller_concessions",
                "cash_pct", "cash_amount", "mortgage_pct", "mortgage_amount",
                "assumption_pct", "assumption_amount", "contract_for_deed_pct", "contract_for_deed_amount"]:
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

    # Well/Septic
    ws = data.get("well_septic", {})
    for key in ws:
        flat[f"ws_{key}"] = ws.get(key)

    # HOA
    hoa = data.get("hoa", {})
    for key in hoa:
        flat[f"hoa_{key}"] = hoa.get(key)

    # Home Warranty
    hw = data.get("home_warranty", {})
    flat["home_warranty_included"] = hw.get("plan_included")
    flat["home_warranty_details"] = hw.get("plan_details")

    # Other Terms
    flat["other_terms"] = data.get("other_terms")

    # FIRPTA
    firpta = data.get("firpta", {})
    flat["firpta_foreign_person"] = firpta.get("seller_is_foreign_person")

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
        accept_multiple_files=True,
        help="Upload one or more PDFs — all docs from the same transaction",
    )

    if uploaded_file:
        st.success(f"Loaded {len(uploaded_file)} file(s)")
        for f in uploaded_file:
            st.caption(f"• {f.name} ({f.size / 1024:.0f} KB)")

    st.divider()
    st.caption("v0.2 — Uses Claude API for extraction")

# ── Main area ─────────────────────────────────────────
if not uploaded_file:
    st.info("👈 Upload a purchase agreement PDF to get started.")
    st.stop()

# Extract button
if st.button("🔍 Extract Fields", type="primary", use_container_width=True):
    with st.spinner("Reading agreement and extracting fields..."):
        try:
            pdf_files = [(f.read(), f.name) for f in uploaded_file]
            result = extract_from_pdf(pdf_files)
            st.session_state["extraction"] = result
            st.session_state["filename"] = uploaded_file[0].name
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

# ── Helper: show flags inline below fields ───────────
flags = data.get("extraction_metadata", {}).get("flags", [])

def get_flags_for(field_prefix: str) -> list:
    """Return flags matching by full dotted path or short field name.
    Claude may return field names as 'sellers' or 'parties.sellers[0].name',
    so we match both the full prefix and the base name extracted from it."""
    prefix_last = field_prefix.split(".")[-1].split("[")[0]
    return [f for f in flags if 
        f.get("field", "").startswith(field_prefix) or
        f.get("field", "").startswith(prefix_last)
    ]

def show_flags(field_prefix: str):
    """Display any flags for a field as small warnings below it."""
    for f in get_flags_for(field_prefix):
        st.caption(f"⚠️ _{f.get('issue', '?')}_ — {f.get('note', '')}")

def line_label(field_name: str) -> str:
    """Return a line reference string for display next to a field label."""
    ref = get_line_ref(data, field_name)
    if ref:
        return f" ({ref})"
    return ""

# ── Summary flag count at top ─────────────────────────
if flags:
    st.info(f"📋 {len(flags)} field(s) flagged — see notes below each field in the relevant tab.")

# ── Tabbed sections for review/editing ────────────────
tab_parties, tab_property, tab_financial, tab_dates, tab_title, tab_contingencies, tab_wellseptic, tab_addenda, tab_json = st.tabs([
    "Parties", "Property", "Financial", "Dates",
    "Title/Closing", "Contingencies", "Well/Septic", "Addenda", "Raw JSON"
])

with tab_parties:
    st.subheader("Buyers")
    for i, buyer in enumerate(data.get("parties", {}).get("buyers", [])):
        col1, col2 = st.columns(2)
        buyer["name"] = col1.text_input(
            f"Buyer {i+1} Name{line_label('buyers')}", 
            value=buyer.get("name", ""), key=f"buyer_name_{i}"
        )
        buyer["entity_type"] = col2.selectbox(
            f"Buyer {i+1} Entity Type", 
            ["individual", "trust", "llc", "corporation", "partnership", "other"],
            index=["individual", "trust", "llc", "corporation", "partnership", "other"].index(buyer.get("entity_type", "individual")),
            key=f"buyer_entity_{i}"
        )
        show_flags(f"parties.buyers[{i}]")

    st.subheader("Sellers")
    for i, seller in enumerate(data.get("parties", {}).get("sellers", [])):
        col1, col2 = st.columns(2)
        seller["name"] = col1.text_input(
            f"Seller {i+1} Name{line_label('sellers')}", 
            value=seller.get("name", ""), key=f"seller_name_{i}"
        )
        seller["entity_type"] = col2.selectbox(
            f"Seller {i+1} Entity Type",
            ["individual", "trust", "llc", "corporation", "partnership", "other"],
            index=["individual", "trust", "llc", "corporation", "partnership", "other"].index(seller.get("entity_type", "individual")),
            key=f"seller_entity_{i}"
        )
        show_flags(f"parties.sellers[{i}]")

    # ── FIRPTA (line ~493) ───────────────────────────
    st.markdown("---")
    firpta = data.get("firpta", {})
    is_foreign = firpta.get("seller_is_foreign_person")
    if is_foreign is True:
        firpta_text = "Seller IS a foreign person"
    elif is_foreign is False:
        firpta_text = "Seller IS NOT a foreign person"
    else:
        firpta_text = "Not stated"
    st.text_input(
        f"FIRPTA Status{line_label('firpta')}", 
        value=firpta_text, key="firpta_status"
    )

with tab_property:
    prop = data.get("property", {})
    col1, col2, col3 = st.columns([3, 1, 2])
    prop["street_address"] = col1.text_input(
        f"Street Address{line_label('street_address')}", 
        value=prop.get("street_address", "")
    )
    prop["unit_no"] = col2.text_input(
        f"Unit No.{line_label('unit_no')}", 
        value=prop.get("unit_no", "") or ""
    )
    prop["city"] = col3.text_input(
        f"City{line_label('city')}", 
        value=prop.get("city", "")
    )
    show_flags("property.street_address")
    show_flags("property.city")
    col1, col2, col3 = st.columns(3)
    prop["county"] = col1.text_input(
        f"County{line_label('county')}", 
        value=prop.get("county", "")
    )
    prop["zip_code"] = col2.text_input(
        f"Zip Code{line_label('zip_code')}", 
        value=prop.get("zip_code", "")
    )
    prop["pid"] = col3.text_input(
        f"PID / Parcel #{line_label('pid')}", 
        value=prop.get("pid", "") or ""
    )
    show_flags("property.county")
    show_flags("property.pid")
    legal = prop.get("legal_description", "")
    prop["legal_description"] = st.text_area(
        f"Legal Description from PA{line_label('legal_description')}", 
        value=legal, height=auto_height(legal)
    )
    show_flags("property.legal_description")

with tab_financial:
    fin = data.get("financial", {})
    
    # Purchase price, earnest money, seller concessions — text inputs (no +/- spinners)
    col1, col2, col3 = st.columns(3)
    price_str = col1.text_input(
        f"Purchase Price{line_label('purchase_price')}", 
        value=format_currency(fin.get("purchase_price", 0))
    )
    fin["purchase_price"] = parse_currency(price_str)
    
    em_str = col2.text_input(
        f"Earnest Money{line_label('earnest_money_amount')}", 
        value=format_currency(fin.get("earnest_money_amount", 0))
    )
    fin["earnest_money_amount"] = parse_currency(em_str)
    
    sc_str = col3.text_input(
        f"Seller Concessions{line_label('seller_concessions')}", 
        value=format_currency(fin.get("seller_concessions", 0))
    )
    fin["seller_concessions"] = parse_currency(sc_str)
    
    show_flags("financial.purchase_price")
    show_flags("financial.earnest_money")
    show_flags("financial.seller_concessions")
    
    col1, col2 = st.columns(2)
    fin["financing_type"] = col1.selectbox(
        f"Financing Type{line_label('financing_type')}",
        ["conventional", "fha", "va", "usda", "cash", "contract_for_deed", "assumption", "other"],
        index=["conventional", "fha", "va", "usda", "cash", "contract_for_deed", "assumption", "other"].index(fin.get("financing_type", "conventional")),
    )
    fin["earnest_money_holder"] = col2.text_input(
        f"Earnest Money Holder{line_label('earnest_money_holder')}", 
        value=fin.get("earnest_money_holder", "") or ""
    )
    show_flags("financial.financing_type")
    
    # ── Financing Breakdown ──────────────────────────
    st.markdown("---")
    st.markdown("**Financing Breakdown**")
    
    purchase_price = fin.get("purchase_price", 0) or 0
    
    # Cash
    cash_pct = fin.get("cash_pct")
    mortgage_pct = fin.get("mortgage_pct")
    
    if cash_pct is not None or mortgage_pct is not None:
        col1, col2, col3, col4 = st.columns(4)
        
        cash_pct_val = cash_pct if cash_pct is not None else 0
        cash_calc = purchase_price * (cash_pct_val / 100) if purchase_price and cash_pct_val else 0
        cash_amount = fin.get("cash_amount") or cash_calc
        
        col1.text_input(
            f"CASH %{line_label('cash_pct')}", 
            value=f"{cash_pct_val}%", disabled=True
        )
        col2.text_input(
            "CASH Amount", 
            value=format_currency(cash_amount), disabled=True
        )
        
        mortgage_pct_val = mortgage_pct if mortgage_pct is not None else 0
        mortgage_calc = purchase_price * (mortgage_pct_val / 100) if purchase_price and mortgage_pct_val else 0
        mortgage_amount = fin.get("mortgage_amount") or mortgage_calc
        
        col3.text_input(
            f"MORTGAGE %{line_label('mortgage_pct')}", 
            value=f"{mortgage_pct_val}%", disabled=True
        )
        col4.text_input(
            "Mortgage Amount (est. based on PA)", 
            value=format_currency(mortgage_amount), disabled=True
        )
    else:
        st.caption("No cash/mortgage breakdown found in agreement.")
    
    # Assumption — only show if populated
    assumption_pct = fin.get("assumption_pct")
    if assumption_pct is not None:
        col1, col2 = st.columns(2)
        assumption_calc = purchase_price * (assumption_pct / 100) if purchase_price and assumption_pct else 0
        assumption_amount = fin.get("assumption_amount") or assumption_calc
        col1.text_input(
            f"ASSUMPTION %{line_label('assumption_pct')}", 
            value=f"{assumption_pct}%", disabled=True
        )
        col2.text_input(
            "ASSUMPTION Amount", 
            value=format_currency(assumption_amount), disabled=True
        )
    
    # Contract for Deed — only show if populated
    cfd_pct = fin.get("contract_for_deed_pct")
    if cfd_pct is not None:
        col1, col2 = st.columns(2)
        cfd_calc = purchase_price * (cfd_pct / 100) if purchase_price and cfd_pct else 0
        cfd_amount = fin.get("contract_for_deed_amount") or cfd_calc
        col1.text_input(
            f"CONTRACT FOR DEED %{line_label('contract_for_deed_pct')}", 
            value=f"{cfd_pct}%", disabled=True
        )
        col2.text_input(
            "CONTRACT FOR DEED Amount", 
            value=format_currency(cfd_amount), disabled=True
        )

with tab_dates:
    dates = data.get("dates", {})
    date_fields = [
        ("purchase_agreement_date", "Purchase Agreement Date"),
        ("closing_date", "Closing Date"),
        ("possession_date", "Possession Date"),
        ("buyer_signature_date", "Buyer Signature Date"),
        ("seller_signature_date", "Seller Signature Date"),
    ]
    col1, col2 = st.columns(2)
    for i, (key, label) in enumerate(date_fields):
        target = col1 if i % 2 == 0 else col2
        dates[key] = target.text_input(
            f"{label}{line_label(key)}", 
            value=dates.get(key, "") or ""
        )
    # Show date flags below the grid
    for key, label in date_fields:
        show_flags(f"dates.{key}")

with tab_title:
    tc = data.get("title_and_closing", {})
    col1, col2 = st.columns(2)
    tc["title_company"] = col1.text_input(
        f"Title Company{line_label('title_company')}", 
        value=tc.get("title_company", "") or ""
    )
    tc["closing_agent"] = col2.text_input(
        f"Closing Agent{line_label('closing_agent')}", 
        value=tc.get("closing_agent", "") or ""
    )
    show_flags("title_and_closing.title_company")
    show_flags("title_and_closing.closing_agent")
    col1, col2 = st.columns(2)
    tc["listing_agent_name"] = col1.text_input(
        f"Listing Agent{line_label('listing_agent_name')}", 
        value=tc.get("listing_agent_name", "") or ""
    )
    tc["listing_brokerage"] = col2.text_input(
        "Listing Brokerage", 
        value=tc.get("listing_brokerage", "") or ""
    )
    col1, col2 = st.columns(2)
    tc["selling_agent_name"] = col1.text_input(
        f"Selling Agent{line_label('selling_agent_name')}", 
        value=tc.get("selling_agent_name", "") or ""
    )
    tc["selling_brokerage"] = col2.text_input(
        "Selling Brokerage", 
        value=tc.get("selling_brokerage", "") or ""
    )

with tab_contingencies:
    cont = data.get("contingencies", {})
    col1, col2 = st.columns(2)
    cont["financing_contingency"] = col1.checkbox("Financing Contingency", value=cont.get("financing_contingency", False))
    cont["inspection_contingency"] = col2.checkbox("Inspection Contingency", value=cont.get("inspection_contingency", False))
    col1, col2 = st.columns(2)
    cont["appraisal_contingency"] = col1.checkbox("Appraisal Contingency", value=cont.get("appraisal_contingency", False))
    cont["sale_of_buyers_property"] = col2.checkbox("Sale of Buyer's Property", value=cont.get("sale_of_buyers_property", False))
    other = cont.get("other_contingencies", [])
    if other:
        st.markdown("**Other Contingencies:**")
        for i, item in enumerate(other):
            st.text_input(f"Contingency {i+1}", value=item, key=f"other_cont_{i}")
    else:
        st.caption("No other contingencies detected.")
    show_flags("contingencies")
    
    # ── Other Terms (line ~454) ──────────────────────
    st.markdown("---")
    st.markdown("**Other Terms**")
    other_terms = data.get("other_terms")
    if other_terms:
        st.text_area(
            f"Other{line_label('other_terms')}", 
            value=other_terms, height=auto_height(other_terms), key="other_terms"
        )
    else:
        st.caption("No other terms found.")
    
    # ── Home Warranty (lines ~385-392) ───────────────
    st.markdown("---")
    st.markdown("**Home Warranty**")
    hw = data.get("home_warranty", {})
    hw_details = hw.get("plan_details", "No Home Protection/Warranty Plan")
    st.text_input(
        f"Home Warranty{line_label('home_warranty')}", 
        value=hw_details or "No Home Protection/Warranty Plan", key="home_warranty"
    )

with tab_wellseptic:
    ws = data.get("well_septic", {})
    
    st.subheader("From Purchase Agreement")
    col1, col2 = st.columns(2)
    pa_well = ws.get("pa_well_known")
    well_display = "Yes" if pa_well is True else "No" if pa_well is False else "Not stated"
    col1.text_input(
        f"Seller knows of wells{line_label('pa_well_known')}", 
        value=well_display, key="pa_well_known"
    )
    pa_ssts = ws.get("pa_ssts_on_property")
    ssts_display = "Yes" if pa_ssts is True else "No" if pa_ssts is False else "Not stated"
    col2.text_input(
        f"SSTS on property{line_label('pa_ssts_on_property')}", 
        value=ssts_display, key="pa_ssts"
    )
    pa_notes = ws.get("pa_well_septic_notes")
    if pa_notes:
        dynamic_text("PA Notes", pa_notes)
    
    st.subheader("From Disclosure Statement")
    disc_well = ws.get("disclosure_well_info")
    disc_ssts = ws.get("disclosure_ssts_info")
    if disc_well or disc_ssts:
        if disc_well:
            dynamic_text("Disclosure — Well", disc_well)
        if disc_ssts:
            dynamic_text("Disclosure — SSTS", disc_ssts)
    else:
        st.caption("No well/septic info found in Disclosure Statement.")
    
    well_num = ws.get("well_number")
    if well_num:
        st.text_input("Well Number (MDH)", value=well_num, key="well_num")
    
    if ws.get("discrepancy_flag"):
        st.warning("⚠️ Discrepancy detected between PA and Disclosure Statement — review well/septic details.")
    
    show_flags("well_septic")
    show_flags("well")
    show_flags("septic")
    show_flags("ssts")

with tab_addenda:
    # HOA section at top of addenda tab
    hoa = data.get("hoa", {})
    if hoa.get("hoa_present"):
        st.subheader("HOA / Association")
        col1, col2 = st.columns(2)
        col1.text_input("HOA Name", value=hoa.get("hoa_name", "") or "", key="hoa_name")
        dues = hoa.get("hoa_dues_amount")
        freq = hoa.get("hoa_dues_frequency", "") or ""
        if dues:
            col2.text_input("HOA Dues", value=f"${dues:,.2f} {freq}", key="hoa_dues")
        else:
            col2.text_input("HOA Dues", value="Not stated in PA", key="hoa_dues")
        show_flags("hoa")
        st.markdown("---")
    
    # Addenda listing — filtered
    addenda = data.get("addenda", [])
    excluded = ["wire fraud", "arbitration", "lead-based paint", "lead based paint"]
    filtered = [a for a in addenda if not any(
        ex in a.get("addendum_title", "").lower() for ex in excluded
    )]
    
    st.subheader("Addenda")
    if filtered:
        for i, add in enumerate(filtered):
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

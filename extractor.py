"""
extractor.py
════════════
Shared extraction + CSV-flatten logic. Single source of truth for the
Anthropic call and the flat CSV row shape. Imported by all PA extractor
pages so review-mode publish and standalone export produce the same
columns in the same order.

Also provides combined-export helpers that prepend order intake fields
to the extracted PA data, for the four export formats (text / HTML /
CSV / JSON) used in the new_order_app's queue.
"""

import streamlit as st
import anthropic
import base64
import json

from extraction_prompt import EXTRACTION_SYSTEM_PROMPT


# ── Config ────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


# ── Anthropic client ──────────────────────────────────

@st.cache_resource
def get_client():
    """Initialize Anthropic client (cached across reruns)."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    return anthropic.Anthropic(api_key=api_key)


# ── Extraction (mirrors app.py) ───────────────────────

def extract_from_pdf(pdf_files: list) -> dict:
    """Send one or more PDFs to Claude and return parsed JSON.
    
    pdf_files: list of (pdf_bytes, filename) tuples.
    """
    client = get_client()

    content = []
    for pdf_bytes, _filename in pdf_files:
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
        "text": (
            "Extract all fields from this Minnesota purchase agreement. "
            "All uploaded documents are part of the same transaction. "
            "Return only JSON."
        ),
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text
    raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw_text)


# ── CSV column order ─────────────────────────────────
# Explicit lists so output columns are stable across extraction runs.
# Add new fields at the END of their section to avoid breaking any
# downstream TPS mapping that relies on column position.

_PROPERTY_COLUMNS = [
    "street_address", "unit_no", "city", "county", "state",
    "zip_code", "legal_description", "pid",
]

_FINANCIAL_COLUMNS = [
    "purchase_price", "earnest_money_amount", "earnest_money_holder",
    "financing_type", "down_payment_amount", "seller_concessions",
    "cash_pct", "cash_amount", "mortgage_pct", "mortgage_amount",
    "assumption_pct", "assumption_amount",
    "contract_for_deed_pct", "contract_for_deed_amount",
]

_DATE_COLUMNS = [
    "purchase_agreement_date", "closing_date", "possession_date",
    "buyer_signature_date", "seller_signature_date",
]

_TITLE_CLOSING_COLUMNS = [
    "title_company", "closing_agent",
    "listing_agent_name", "listing_brokerage",
    "selling_agent_name", "selling_brokerage",
]

_CONTINGENCY_BOOL_COLUMNS = [
    "financing_contingency", "inspection_contingency",
    "appraisal_contingency", "sale_of_buyers_property",
]

_WELL_SEPTIC_COLUMNS = [
    "pa_well_known", "pa_ssts_on_property", "pa_well_septic_notes",
    "disclosure_well_info", "disclosure_ssts_info",
    "well_number", "discrepancy_flag",
]

_HOA_COLUMNS = [
    "hoa_present", "hoa_name", "hoa_dues_amount", "hoa_dues_frequency",
]


def flatten_for_csv(data: dict) -> dict:
    """Flatten nested extraction JSON into a single-row dict for CSV export.

    Column order is fixed (see _*_COLUMNS lists above) so CSV output is
    stable across runs — required for TPS column mapping.
    """
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
    for key in _PROPERTY_COLUMNS:
        flat[key] = prop.get(key)

    # Financial
    fin = data.get("financial", {})
    for key in _FINANCIAL_COLUMNS:
        flat[key] = fin.get(key)

    # Dates
    dates = data.get("dates", {})
    for key in _DATE_COLUMNS:
        flat[key] = dates.get(key)

    # Title & Closing
    tc = data.get("title_and_closing", {})
    for key in _TITLE_CLOSING_COLUMNS:
        flat[key] = tc.get(key)

    # Contingencies
    cont = data.get("contingencies", {})
    for key in _CONTINGENCY_BOOL_COLUMNS:
        flat[key] = cont.get(key)
    flat["other_contingencies"] = "; ".join(cont.get("other_contingencies", []))

    # Well / Septic
    ws = data.get("well_septic", {})
    for key in _WELL_SEPTIC_COLUMNS:
        flat[f"ws_{key}"] = ws.get(key)

    # HOA
    hoa = data.get("hoa", {})
    for key in _HOA_COLUMNS:
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

    # Addenda
    flat["addenda_count"] = len(data.get("addenda", []))
    flat["addenda_titles"] = "; ".join(
        a.get("addendum_title", "") for a in data.get("addenda", [])
    )

    # Flags
    flags = data.get("extraction_metadata", {}).get("flags", [])
    flat["flag_count"] = len(flags)

    return flat


# ── Combined intake + extraction exports ──────────────
# These prepend order-intake fields (entered by the user in the New Order
# tab) to the extracted PA fields, for unified TPS-bound exports.

INTAKE_FIELD_ORDER = [
    "transaction_type",
    "order_type",
    "property_state",
    "is_new_construction",
    "template_name",
    "client_name_referrer",
    "client_broker",
    "lender",
    "mortgage_broker",
    "plat_and_assessments",
    "closer",
    "underwriter_code",
    "office",
    "assistant_main_contact",
    "business_dev_contact_other_agent",
    "additional_notes",
]

INTAKE_LABELS = [
    ("Transaction Type", "transaction_type"),
    ("Order Type", "order_type"),
    ("Property State", "property_state"),
    ("New Construction", "is_new_construction"),
    ("Template Name", "template_name"),
    ("Client Name (Referrer)", "client_name_referrer"),
    ("Client Broker", "client_broker"),
    ("Lender", "lender"),
    ("Mortgage Broker", "mortgage_broker"),
    ("Plat & Assessments", "plat_and_assessments"),
    ("Closer", "closer"),
    ("Underwriter Code", "underwriter_code"),
    ("Office", "office"),
    ("Assistant & Main Contact", "assistant_main_contact"),
    ("Sales Team to Contact Other Agent", "business_dev_contact_other_agent"),
    ("Additional Notes", "additional_notes"),
]


def flatten_combined_for_csv(intake: dict, extracted: dict) -> dict:
    """Order intake fields first (snake_case), then flattened extraction fields."""
    flat = {f: (intake.get(f) or "") for f in INTAKE_FIELD_ORDER}
    flat.update(flatten_for_csv(extracted))
    return flat


def intake_summary_text(intake: dict) -> str:
    """Plain-text 'Order Information' section for prepending to text exports."""
    lines = ["═══ ORDER INFORMATION ═══", ""]
    for label, key in INTAKE_LABELS:
        val = intake.get(key) or ""
        lines.append(f"{label}: {val}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def intake_summary_html(intake: dict) -> str:
    """HTML 'Order Information' section for prepending to HTML exports."""
    rows = []
    for label, key in INTAKE_LABELS:
        val = intake.get(key) or ""
        rows.append(
            f"<tr><td style='padding:4px 12px 4px 0;'><b>{label}</b></td>"
            f"<td style='padding:4px 0;'>{val}</td></tr>"
        )
    return (
        "<h2>Order Information</h2>\n"
        "<table style='border-collapse:collapse; margin-bottom:1em;'>\n"
        + "\n".join(rows)
        + "\n</table>\n"
    )

"""
extractor.py
════════════
Shared extraction logic for the new_order_app.

The extract_from_pdf() and flatten_for_csv() functions mirror the same
functions in app.py exactly. This module is imported by new_order_app.py
so the queue's "Extract Fields" button uses the same logic as the
standalone extractor.

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


def flatten_for_csv(data: dict) -> dict:
    """Flatten nested extraction JSON into a single-row dict for CSV export.
    
    Mirrors flatten_for_csv() in app.py.
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
    "order_type",
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
    ("Order Type", "order_type"),
    ("Client Name (Referrer)", "client_name_referrer"),
    ("Client Broker", "client_broker"),
    ("Lender", "lender"),
    ("Mortgage Broker", "mortgage_broker"),
    ("Plat & Assessments", "plat_and_assessments"),
    ("Closer", "closer"),
    ("Underwriter Code", "underwriter_code"),
    ("Office", "office"),
    ("Assistant & Main Contact", "assistant_main_contact"),
    ("Business Dev. Contact Other Agent", "business_dev_contact_other_agent"),
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

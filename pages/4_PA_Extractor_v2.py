"""
4_PA_Extractor_v2.py
═════════════════════
Alternate view of the PA Extractor — same extracted data, but fields grouped
in the order they appear in the standard Minnesota Purchase Agreement form
(by PA page section) rather than by category.

Standard MN PA form sections used here (these are conventional groupings;
actual page numbers vary slightly between MAR forms but the order is stable):

  PA pp. 1–2: Parties + Property + Purchase Price
  PA pp. 2–3: Earnest Money + Financing Type + Closing
  PA pp. 3–4: Title & Deed + Closing Costs/Concessions
  PA pp. 4–5: Contingencies (financing / inspection / appraisal / sale-of-property)
  PA pp. 5–8: MN-specific Disclosures (well, septic, methamphetamine, abandoned wells, etc.)
  PA pp. 8–10: Standard Provisions
  PA pp. 10+:  Addenda

If the extracted PA appears non-standard (e.g., custom-drafted), we flag it
at the top so the OET knows fields may be in unexpected order.
"""

import streamlit as st
import json
import pandas as pd
import zipfile
from io import BytesIO

from extractor import extract_from_pdf, flatten_combined_for_csv, intake_summary_text, intake_summary_html, parse_currency
from extraction_prompt import EXTRACTION_SYSTEM_PROMPT
from summary_generator import generate_text_summary, generate_html_summary
from supabase_client import set_order_status, update_extraction
from ui_theme import apply_theme, section_header, section_bar


try:
    st.set_page_config(page_title="PA Extractor v2", page_icon="📑", layout="wide")
except Exception:
    pass

apply_theme()


st.title("📑 PA Extractor v2")
st.caption("Alternate review layout — fields grouped by PA page section (order they appear in the MN PA form)")


# ══════════════════════════════════════════════════════
# DETECT ORDER-REVIEW CONTEXT
# ══════════════════════════════════════════════════════

review_order = st.session_state.get("review_order")
review_order_id = st.session_state.get("review_order_id")
review_files = st.session_state.get("review_files")
in_review_mode = bool(review_order and review_files)


# ══════════════════════════════════════════════════════
# REVIEW BANNER (when launched from Order Queue)
# ══════════════════════════════════════════════════════

if in_review_mode:
    st.success(
        f"📂 **Review mode** — Order for "
        f"**{review_order.get('client_name_referrer') or '—'}** · "
        f"{review_order.get('transaction_type') or '—'} / "
        f"{review_order.get('order_type') or '—'} · "
        f"State {review_order.get('property_state') or '—'} · "
        f"Closer {review_order.get('closer') or '—'}"
        + (f" · 🏗️ New Construction" if review_order.get("is_new_construction") else "")
    )
    if review_order.get("template_name"):
        st.caption(f"📄 Template: **{review_order['template_name']}**")

    cexit, _ = st.columns([1, 5])
    with cexit:
        if st.button("⬅️ Back to Queue (exit review mode)"):
            for k in ("review_order", "review_order_id", "review_files",
                      "extraction", "filename"):
                st.session_state.pop(k, None)
            st.switch_page("pages/2_Order_Queue.py")


# ══════════════════════════════════════════════════════
# UPLOAD / EXTRACT
# ══════════════════════════════════════════════════════

with st.sidebar:
    st.header("Upload")
    if in_review_mode:
        st.info(f"📂 Reviewing order — {len(review_files)} file(s) loaded from queue.")
        for fbytes, fname in review_files:
            st.caption(f"• {fname} ({len(fbytes) / 1024:.0f} KB)")
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader(
            "Purchase Agreement (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload one or more PDFs from the same transaction",
        )
        if uploaded_file:
            st.success(f"Loaded {len(uploaded_file)} file(s)")
            for f in uploaded_file:
                st.caption(f"• {f.name} ({f.size / 1024:.0f} KB)")

    st.divider()
    st.caption("v2 — PA-page-order layout")


# ── Auto-extract in review mode; manual button in standalone ──
if in_review_mode:
    if "extraction" not in st.session_state:
        with st.spinner("Reading agreement and extracting fields..."):
            try:
                pdf_files = [(b, fname) for (b, fname) in review_files]
                result = extract_from_pdf(pdf_files)
                st.session_state["extraction"] = result
                st.session_state["filename"] = review_files[0][1]
            except json.JSONDecodeError as e:
                st.error(f"Claude returned invalid JSON. Try Re-extract. Error: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()

    if st.button("🔁 Re-run extraction", help="Re-extract from the loaded PDFs"):
        with st.spinner("Re-running extraction..."):
            try:
                pdf_files = [(b, fname) for (b, fname) in review_files]
                result = extract_from_pdf(pdf_files)
                st.session_state["extraction"] = result
                st.rerun()
            except Exception as e:
                st.error(f"Re-extraction failed: {e}")
else:
    if not uploaded_file:
        st.info("👈 Upload a purchase agreement PDF to get started.")
        st.stop()
    if st.button("🔍 Extract Fields", type="primary", use_container_width=True):
        with st.spinner("Reading agreement and extracting fields..."):
            try:
                pdf_files = [(f.read(), f.name) for f in uploaded_file]
                result = extract_from_pdf(pdf_files)
                st.session_state["extraction"] = result
                st.session_state["filename"] = uploaded_file[0].name
            except json.JSONDecodeError as e:
                st.error(f"Claude returned invalid JSON. Error: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()


if "extraction" not in st.session_state:
    st.stop()

data = st.session_state["extraction"]
fname = st.session_state.get("filename", "output")
flags = data.get("extraction_metadata", {}).get("flags", [])


# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def field_flag_note(field_path: str):
    """If this field has a flag from extraction, show it inline."""
    for f in flags:
        if f.get("field") == field_path:
            st.caption(f"⚠️ **{f.get('issue', 'flag')}** — {f.get('note', '')}")


def fmt_currency(v):
    if v is None or v == "":
        return ""
    try:
        return f"${float(v):,.2f}"
    except (ValueError, TypeError):
        return str(v)


# ══════════════════════════════════════════════════════
# Detect non-standard PA (more than ~5% chance — the < 1% case)
# ══════════════════════════════════════════════════════

# Heuristic: check that core MN-specific disclosures are present in the
# extraction. If they're missing, the document is probably custom.
mn = data.get("mn_specific_disclosures", {})
has_mn_markers = any(mn.get(k) is not None for k in (
    "well_disclosure", "individual_septic_disclosure",
    "methamphetamine_disclosure", "abandoned_wells_disclosure",
))

if not has_mn_markers:
    st.warning(
        "⚠️ **Non-standard PA detected** — this document is missing some standard "
        "MN-specific disclosures. Field positions below may not match a typical "
        "MN purchase agreement form. Consider using PA Extractor (v1, categorical) "
        "instead."
    )


# Flag count summary
if flags:
    st.info(f"📋 {len(flags)} field(s) flagged — see notes below each field.")


# ══════════════════════════════════════════════════════
# PA-ORDERED SECTIONS
# ══════════════════════════════════════════════════════

# ── PA pp. 1–2: Parties, Property, Purchase Price ─────
section_header("PA pp. 1–2 — Parties, Property & Purchase Price")
with st.container(border=True):
    # Buyers
    st.markdown("**Buyers**")
    buyers = data.get("parties", {}).get("buyers", [])
    if not buyers:
        st.caption("_No buyers extracted._")
    for i, buyer in enumerate(buyers):
        c1, c2 = st.columns(2)
        buyer["name"] = c1.text_input(
            f"Buyer {i+1} Name", value=buyer.get("name", ""), key=f"v2_buyer_name_{i}"
        )
        buyer["entity_type"] = c2.text_input(
            f"Buyer {i+1} Entity Type", value=buyer.get("entity_type", ""), key=f"v2_buyer_etype_{i}"
        )

    # Sellers
    st.markdown("**Sellers**")
    sellers = data.get("parties", {}).get("sellers", [])
    if not sellers:
        st.caption("_No sellers extracted._")
    for i, seller in enumerate(sellers):
        c1, c2 = st.columns(2)
        seller["name"] = c1.text_input(
            f"Seller {i+1} Name", value=seller.get("name", ""), key=f"v2_seller_name_{i}"
        )
        seller["entity_type"] = c2.text_input(
            f"Seller {i+1} Entity Type", value=seller.get("entity_type", ""), key=f"v2_seller_etype_{i}"
        )

    # Property
    st.markdown("**Property**")
    prop = data.get("property", {}) or {}
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        prop["street_address"] = st.text_input("Street Address", value=prop.get("street_address", "") or "", key="v2_prop_addr")
        prop["city"] = st.text_input("City", value=prop.get("city", "") or "", key="v2_prop_city")
        prop["county"] = st.text_input("County", value=prop.get("county", "") or "", key="v2_prop_county")
    with pcol2:
        prop["state"] = st.text_input("State", value=prop.get("state", "") or "", key="v2_prop_state")
        prop["zip_code"] = st.text_input("ZIP Code", value=prop.get("zip_code", "") or "", key="v2_prop_zip")
        prop["pid"] = st.text_input("Property ID (PID)", value=prop.get("pid", "") or "", key="v2_prop_pid")
    prop["legal_description"] = st.text_area("Legal Description", value=prop.get("legal_description", "") or "", key="v2_prop_legal", height=68)
    data["property"] = prop

    # Purchase price (top-level financial)
    st.markdown("**Purchase Price**")
    fin = data.get("financial", {}) or {}
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        _price_in = st.text_input("Purchase Price", value=fmt_currency(fin.get("purchase_price")), key="v2_fin_price")
        fin["purchase_price"] = parse_currency(_price_in)
    with fcol2:
        _down_in = st.text_input("Down Payment", value=fmt_currency(fin.get("down_payment_amount")), key="v2_fin_down")
        fin["down_payment_amount"] = parse_currency(_down_in)
    data["financial"] = fin


# ── PA pp. 2–3: Earnest Money, Financing, Closing ─────
section_header("PA pp. 2–3 — Earnest Money, Financing & Closing")
with st.container(border=True):
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        _em_in = st.text_input(
            "Earnest Money Amount",
            value=fmt_currency(fin.get("earnest_money_amount")),
            key="v2_em_amt",
        )
        fin["earnest_money_amount"] = parse_currency(_em_in)
        fin["earnest_money_holder"] = st.text_input(
            "Earnest Money Holder",
            value=fin.get("earnest_money_holder", "") or "",
            key="v2_em_holder",
        )
    with fcol2:
        fin["financing_type"] = st.text_input(
            "Financing Type",
            value=fin.get("financing_type", "") or "",
            key="v2_fin_type",
        )
        _conc_in = st.text_input(
            "Seller Concessions",
            value=fmt_currency(fin.get("seller_concessions")),
            key="v2_fin_conc",
        )
        fin["seller_concessions"] = parse_currency(_conc_in)

    # Dates
    dates = data.get("dates", {}) or {}
    st.markdown("**Key Dates**")
    dcol1, dcol2 = st.columns(2)
    date_keys = list(dates.keys())
    half = (len(date_keys) + 1) // 2
    with dcol1:
        for k in date_keys[:half]:
            dates[k] = st.text_input(k.replace("_", " ").title(), value=str(dates.get(k, "") or ""), key=f"v2_date_{k}")
    with dcol2:
        for k in date_keys[half:]:
            dates[k] = st.text_input(k.replace("_", " ").title(), value=str(dates.get(k, "") or ""), key=f"v2_date_{k}")
    data["dates"] = dates


# ── PA pp. 3–4: Title & Closing ───────────────────────
section_header("PA pp. 3–4 — Title & Closing")
with st.container(border=True):
    tc = data.get("title_and_closing", {}) or {}
    tcol1, tcol2 = st.columns(2)
    tc_keys = list(tc.keys())
    half = (len(tc_keys) + 1) // 2
    with tcol1:
        for k in tc_keys[:half]:
            tc[k] = st.text_input(k.replace("_", " ").title(), value=str(tc.get(k, "") or ""), key=f"v2_tc_{k}")
    with tcol2:
        for k in tc_keys[half:]:
            tc[k] = st.text_input(k.replace("_", " ").title(), value=str(tc.get(k, "") or ""), key=f"v2_tc_{k}")
    data["title_and_closing"] = tc


# ── PA pp. 4–5: Contingencies ─────────────────────────
section_header("PA pp. 4–5 — Contingencies")
with st.container(border=True):
    cont = data.get("contingencies", {}) or {}
    ccol1, ccol2 = st.columns(2)
    with ccol1:
        cont["financing_contingency"] = st.checkbox(
            "Financing Contingency",
            value=bool(cont.get("financing_contingency", False)),
            key="v2_cont_fin",
        )
        cont["inspection_contingency"] = st.checkbox(
            "Inspection Contingency",
            value=bool(cont.get("inspection_contingency", False)),
            key="v2_cont_insp",
        )
    with ccol2:
        cont["appraisal_contingency"] = st.checkbox(
            "Appraisal Contingency",
            value=bool(cont.get("appraisal_contingency", False)),
            key="v2_cont_apr",
        )
        cont["sale_of_buyers_property"] = st.checkbox(
            "Sale of Buyer's Property",
            value=bool(cont.get("sale_of_buyers_property", False)),
            key="v2_cont_sale",
        )

    other = "; ".join(cont.get("other_contingencies", []) or [])
    new_other = st.text_input("Other Contingencies (semicolon-separated)", value=other, key="v2_cont_other")
    cont["other_contingencies"] = [x.strip() for x in new_other.split(";") if x.strip()]
    data["contingencies"] = cont


# ── PA pp. 5–8: MN-Specific Disclosures ───────────────
section_header("PA pp. 5–8 — MN-Specific Disclosures")
with st.container(border=True):
    mn = data.get("mn_specific_disclosures", {}) or {}
    if mn:
        mn_keys = list(mn.keys())
        mcol1, mcol2 = st.columns(2)
        half = (len(mn_keys) + 1) // 2
        with mcol1:
            for k in mn_keys[:half]:
                mn[k] = st.text_input(k.replace("_", " ").title(), value=str(mn.get(k, "") or ""), key=f"v2_mn_{k}")
        with mcol2:
            for k in mn_keys[half:]:
                mn[k] = st.text_input(k.replace("_", " ").title(), value=str(mn.get(k, "") or ""), key=f"v2_mn_{k}")
        data["mn_specific_disclosures"] = mn
    else:
        st.caption("_No MN-specific disclosures extracted._")


# ── PA pp. 10+: Addenda ───────────────────────────────
section_header("PA pp. 10+ — Addenda")
with st.container(border=True):
    addenda = data.get("addenda", []) or []
    if addenda:
        for i, add in enumerate(addenda):
            st.markdown(f"**{add.get('addendum_title', f'Addendum {i+1}')}**")
            st.caption(add.get("summary", ""))
    else:
        st.info("No addenda detected.")


# ── Raw JSON (collapsed) ──────────────────────────────
section_header("Raw JSON (debug)")
with st.container(border=True):
    with st.expander("Show raw JSON (for debugging only)", expanded=False):
        st.json(data)


# ══════════════════════════════════════════════════════
# EXPORT / PUBLISH
# ══════════════════════════════════════════════════════

st.divider()

if in_review_mode:
    section_bar("Publish")
    st.caption(
        "Once you've reviewed the fields above for accuracy, choose either Publish "
        "option. Both mark the order as **Submitted**; the zip option also bundles "
        "the original documents so they're ready to attach in TPS."
    )

    # Build CSV
    intake = {
        "transaction_type": review_order.get("transaction_type"),
        "order_type": review_order.get("order_type"),
        "property_state": review_order.get("property_state"),
        "is_new_construction": review_order.get("is_new_construction"),
        "template_name": review_order.get("template_name"),
        "client_name_referrer": review_order.get("client_name_referrer"),
        "client_broker": review_order.get("client_broker"),
        "lender": review_order.get("lender"),
        "mortgage_broker": review_order.get("mortgage_broker"),
        "plat_and_assessments": review_order.get("plat_and_assessments"),
        "closer": review_order.get("closer"),
        "underwriter_code": review_order.get("underwriter_code"),
        "office": review_order.get("office"),
        "assistant_main_contact": review_order.get("assistant_main_contact"),
        "business_dev_contact_other_agent": review_order.get("business_dev_contact_other_agent"),
        "additional_notes": review_order.get("additional_notes"),
    }
    flat = flatten_combined_for_csv(intake, data)
    csv_bytes = pd.DataFrame([flat]).to_csv(index=False).encode("utf-8")

    text_combined = (intake_summary_text(intake) + generate_text_summary(data, fname)).encode("utf-8")

    short_id = (review_order_id or "order")[:8]
    client_slug = (review_order.get("client_name_referrer") or "order").replace(" ", "_")

    # Build zip
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"order_{short_id}_data.csv", csv_bytes)
        zf.writestr(f"order_{short_id}_summary.txt", text_combined)
        for fbytes, fname_doc in review_files:
            zf.writestr(f"documents/{fname_doc}", fbytes)
    zip_bytes = zip_buf.getvalue()

    def _on_publish():
        try:
            ext_flags = data.get("extraction_metadata", {}).get("flags", [])
            update_extraction(review_order_id, data, ext_flags)
            set_order_status(review_order_id, "submitted")
            st.session_state["just_published"] = True
        except Exception as e:
            st.session_state["publish_error"] = str(e)

    cpub_l, cpub_m, cpub_r = st.columns([1, 1, 1])
    with cpub_l:
        st.download_button(
            "📤 Publish CSV (zip with docs)",
            data=zip_bytes,
            file_name=f"{client_slug}_{short_id}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
            on_click=_on_publish,
            key="v2_publish_zip",
        )
    with cpub_m:
        st.download_button(
            "📤 Publish CSV (no docs)",
            data=csv_bytes,
            file_name=f"{client_slug}_{short_id}.csv",
            mime="text/csv",
            use_container_width=True,
            on_click=_on_publish,
            key="v2_publish_csv",
            help="Downloads just the CSV. Order is still marked as Submitted.",
        )
    with cpub_r:
        if st.session_state.get("just_published"):
            st.success("✅ Published! Order marked as Submitted.")
            if st.button("⬅️ Back to Queue", key="v2_back"):
                for k in ("review_order", "review_order_id", "review_files",
                          "extraction", "filename", "just_published"):
                    st.session_state.pop(k, None)
                st.switch_page("pages/2_Order_Queue.py")
        elif st.session_state.get("publish_error"):
            st.error(f"Publish failed: {st.session_state['publish_error']}")
            st.session_state.pop("publish_error", None)

else:
    # Standalone mode — same 4-button export grid
    section_bar("Export")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        text_summary = generate_text_summary(data, fname)
        st.download_button(
            "📋 Summary (Text)",
            data=text_summary.encode("utf-8"),
            file_name=f"summary_{fname}.txt",
            mime="text/plain",
            use_container_width=True,
            key="v2_dl_text",
        )
    with col2:
        html_summary = generate_html_summary(data, fname)
        st.download_button(
            "🌐 Summary (HTML)",
            data=html_summary.encode("utf-8"),
            file_name=f"summary_{fname}.html",
            mime="text/html",
            use_container_width=True,
            key="v2_dl_html",
        )
    with col3:
        from extractor import flatten_for_csv
        flat = flatten_for_csv(data)
        df = pd.DataFrame([flat])
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Data (CSV)",
            data=csv_bytes,
            file_name=f"extraction_{fname}.csv",
            mime="text/csv",
            use_container_width=True,
            key="v2_dl_csv",
        )
    with col4:
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        st.download_button(
            "📥 Data (JSON)",
            data=json_bytes,
            file_name=f"extraction_{fname}.json",
            mime="application/json",
            use_container_width=True,
            key="v2_dl_json",
        )

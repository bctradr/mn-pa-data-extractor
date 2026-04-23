"""
Summary generator for MN Purchase Agreement extractions.
Produces clean text and HTML summaries for pasting into title production software.
"""

from datetime import datetime


def generate_text_summary(data: dict, filename: str = "") -> str:
    """Generate a plain-text summary suitable for pasting into TPS notes."""
    lines = []
    lines.append("=" * 60)
    lines.append("PURCHASE AGREEMENT DATA SUMMARY")
    lines.append("=" * 60)
    if filename:
        lines.append(f"Source: {filename}")
    lines.append(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Parties
    lines.append("-" * 40)
    lines.append("PARTIES")
    lines.append("-" * 40)
    buyers = data.get("parties", {}).get("buyers", [])
    for i, b in enumerate(buyers, 1):
        name = b.get("name", "N/A")
        etype = b.get("entity_type", "individual")
        ename = b.get("entity_name", "")
        label = f"Buyer {i}: {name}"
        if etype != "individual":
            label += f" ({etype}"
            if ename:
                label += f" - {ename}"
            label += ")"
        lines.append(label)

    sellers = data.get("parties", {}).get("sellers", [])
    for i, s in enumerate(sellers, 1):
        name = s.get("name", "N/A")
        etype = s.get("entity_type", "individual")
        ename = s.get("entity_name", "")
        label = f"Seller {i}: {name}"
        if etype != "individual":
            label += f" ({etype}"
            if ename:
                label += f" - {ename}"
            label += ")"
        lines.append(label)
    lines.append("")

    # Property
    lines.append("-" * 40)
    lines.append("PROPERTY")
    lines.append("-" * 40)
    prop = data.get("property", {})
    lines.append(f"Address: {prop.get('street_address', 'N/A')}")
    unit = prop.get("unit_no")
    if unit:
        lines.append(f"Unit No.: {unit}")
    lines.append(f"City: {prop.get('city', 'N/A')}")
    lines.append(f"County: {prop.get('county', 'N/A')}")
    lines.append(f"State: {prop.get('state', 'Minnesota')}")
    lines.append(f"Zip: {prop.get('zip_code', 'N/A')}")
    pid = prop.get("pid")
    if pid:
        lines.append(f"PID/Parcel #: {pid}")
    lines.append(f"Legal Description from PA: {prop.get('legal_description', 'N/A')}")
    lines.append("")

    # Financial
    lines.append("-" * 40)
    lines.append("FINANCIAL")
    lines.append("-" * 40)
    fin = data.get("financial", {})
    price = fin.get("purchase_price", 0)
    lines.append(f"Purchase Price: ${price:,.2f}")
    em = fin.get("earnest_money_amount", 0)
    lines.append(f"Earnest Money: ${em:,.2f}")
    holder = fin.get("earnest_money_holder")
    if holder:
        lines.append(f"Earnest Money Holder: {holder}")
    lines.append(f"Financing Type: {fin.get('financing_type', 'N/A')}")
    dp = fin.get("down_payment_amount")
    if dp:
        lines.append(f"Down Payment: ${dp:,.2f}")
    sc = fin.get("seller_concessions")
    if sc:
        lines.append(f"Seller Concessions: ${sc:,.2f}")
    # Financing breakdown
    cash_pct = fin.get("cash_pct")
    if cash_pct is not None:
        cash_amt = fin.get("cash_amount") or (price * cash_pct / 100 if price else 0)
        lines.append(f"Cash: {cash_pct}% (${cash_amt:,.2f})")
    mortgage_pct = fin.get("mortgage_pct")
    if mortgage_pct is not None:
        mort_amt = fin.get("mortgage_amount") or (price * mortgage_pct / 100 if price else 0)
        lines.append(f"Mortgage Financing: {mortgage_pct}% (${mort_amt:,.2f})")
    assumption_pct = fin.get("assumption_pct")
    if assumption_pct is not None:
        assump_amt = fin.get("assumption_amount") or (price * assumption_pct / 100 if price else 0)
        lines.append(f"Assumption: {assumption_pct}% (${assump_amt:,.2f})")
    cfd_pct = fin.get("contract_for_deed_pct")
    if cfd_pct is not None:
        cfd_amt = fin.get("contract_for_deed_amount") or (price * cfd_pct / 100 if price else 0)
        lines.append(f"Contract for Deed: {cfd_pct}% (${cfd_amt:,.2f})")
    lines.append("")

    # Dates
    lines.append("-" * 40)
    lines.append("KEY DATES")
    lines.append("-" * 40)
    dates = data.get("dates", {})
    date_labels = [
        ("purchase_agreement_date", "Purchase Agreement Date"),
        ("closing_date", "Closing Date"),
        ("possession_date", "Possession Date"),
        ("buyer_signature_date", "Buyer Signature Date"),
        ("seller_signature_date", "Seller Signature Date"),
    ]
    for key, label in date_labels:
        val = dates.get(key)
        if val:
            lines.append(f"{label}: {val}")
    lines.append("")

    # Title & Closing
    lines.append("-" * 40)
    lines.append("TITLE & CLOSING")
    lines.append("-" * 40)
    tc = data.get("title_and_closing", {})
    tc_fields = [
        ("title_company", "Title Company"),
        ("closing_agent", "Closing Agent"),
        ("listing_agent_name", "Listing Agent"),
        ("listing_brokerage", "Listing Brokerage"),
        ("selling_agent_name", "Selling Agent"),
        ("selling_brokerage", "Selling Brokerage"),
    ]
    for key, label in tc_fields:
        val = tc.get(key)
        if val:
            lines.append(f"{label}: {val}")
    lines.append("")

    # Contingencies
    lines.append("-" * 40)
    lines.append("CONTINGENCIES")
    lines.append("-" * 40)
    cont = data.get("contingencies", {})
    cont_flags = [
        ("financing_contingency", "Financing"),
        ("inspection_contingency", "Inspection"),
        ("appraisal_contingency", "Appraisal"),
        ("sale_of_buyers_property", "Sale of Buyer's Property"),
    ]
    active = [label for key, label in cont_flags if cont.get(key)]
    if active:
        lines.append("Active: " + ", ".join(active))
    else:
        lines.append("Active: None")
    other = cont.get("other_contingencies", [])
    if other:
        lines.append("Other: " + "; ".join(other))
    lines.append("")

    # Well/Septic
    lines.append("-" * 40)
    lines.append("WELL / SEPTIC")
    lines.append("-" * 40)
    ws = data.get("well_septic", {})
    pa_well = ws.get("pa_well_known")
    well_display = "Yes" if pa_well is True else "No" if pa_well is False else "Not stated"
    lines.append(f"PA — Seller knows of wells: {well_display}")
    pa_ssts = ws.get("pa_ssts_on_property")
    ssts_display = "Yes" if pa_ssts is True else "No" if pa_ssts is False else "Not stated"
    lines.append(f"PA — SSTS on property: {ssts_display}")
    disc_well = ws.get("disclosure_well_info")
    if disc_well:
        lines.append(f"Disclosure — Well: {disc_well}")
    disc_ssts = ws.get("disclosure_ssts_info")
    if disc_ssts:
        lines.append(f"Disclosure — SSTS: {disc_ssts}")
    wn = ws.get("well_number")
    if wn:
        lines.append(f"Well Number (MDH): {wn}")
    if ws.get("discrepancy_flag"):
        lines.append("⚠ DISCREPANCY between PA and Disclosure Statement")
    lines.append("")

    # HOA
    hoa_data = data.get("hoa", {})
    if hoa_data.get("hoa_present"):
        lines.append("-" * 40)
        lines.append("HOA / ASSOCIATION")
        lines.append("-" * 40)
        lines.append(f"HOA Present: Yes")
        hoa_name = hoa_data.get("hoa_name")
        if hoa_name:
            lines.append(f"HOA Name: {hoa_name}")
        hoa_dues = hoa_data.get("hoa_dues_amount")
        if hoa_dues:
            freq = hoa_data.get("hoa_dues_frequency", "")
            lines.append(f"HOA Dues: ${hoa_dues:,.2f} {freq}")
        lines.append("")

    # Home Warranty
    hw = data.get("home_warranty", {})
    hw_details = hw.get("plan_details", "No Home Protection/Warranty Plan")
    lines.append(f"Home Warranty: {hw_details or 'No Home Protection/Warranty Plan'}")

    # Other Terms
    other_terms = data.get("other_terms")
    if other_terms:
        lines.append(f"Other Terms: {other_terms}")

    # FIRPTA
    firpta = data.get("firpta", {})
    is_foreign = firpta.get("seller_is_foreign_person")
    if is_foreign is True:
        lines.append("FIRPTA: Seller IS a foreign person")
    elif is_foreign is False:
        lines.append("FIRPTA: Seller IS NOT a foreign person")
    lines.append("")

    # Addenda
    addenda = data.get("addenda", [])
    excluded = ["wire fraud", "arbitration", "lead-based paint", "lead based paint"]
    filtered = [a for a in addenda if not any(
        ex in a.get("addendum_title", "").lower() for ex in excluded
    )]
    if filtered:
        lines.append("-" * 40)
        lines.append("ADDENDA")
        lines.append("-" * 40)
        for i, a in enumerate(filtered, 1):
            title = a.get("addendum_title", f"Addendum {i}")
            summary = a.get("summary", "")
            date = a.get("addendum_date", "")
            line = f"{i}. {title}"
            if date:
                line += f" ({date})"
            lines.append(line)
            if summary:
                lines.append(f"   {summary}")
        lines.append("")

    # Flags
    flags = data.get("extraction_metadata", {}).get("flags", [])
    if flags:
        lines.append("-" * 40)
        lines.append("⚠ EXTRACTION FLAGS (review these)")
        lines.append("-" * 40)
        for f in flags:
            lines.append(f"• {f.get('field', '?')}: [{f.get('issue', '?')}] {f.get('note', '')}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("END OF SUMMARY")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_html_summary(data: dict, filename: str = "") -> str:
    """Generate a styled HTML summary."""
    text_summary = generate_text_summary(data, filename)

    # Build HTML with clean styling
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PA Summary - {filename}</title>
<style>
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        max-width: 800px;
        margin: 40px auto;
        padding: 20px;
        color: #333;
        line-height: 1.5;
    }}
    h1 {{
        color: #1a365d;
        border-bottom: 3px solid #2b6cb0;
        padding-bottom: 10px;
        font-size: 22px;
    }}
    h2 {{
        color: #2b6cb0;
        border-bottom: 1px solid #bee3f8;
        padding-bottom: 5px;
        margin-top: 25px;
        font-size: 16px;
    }}
    .meta {{
        color: #718096;
        font-size: 13px;
        margin-bottom: 20px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }}
    td {{
        padding: 5px 10px;
        vertical-align: top;
        border-bottom: 1px solid #edf2f7;
    }}
    td:first-child {{
        font-weight: 600;
        width: 220px;
        color: #4a5568;
        white-space: nowrap;
    }}
    .flag {{
        background: #fff5f5;
        border-left: 4px solid #fc8181;
        padding: 8px 12px;
        margin: 5px 0;
        font-size: 14px;
    }}
    .flag-label {{
        font-weight: 600;
        color: #c53030;
    }}
    .contingency-active {{
        color: #276749;
        font-weight: 600;
    }}
    .addendum {{
        background: #f7fafc;
        padding: 8px 12px;
        margin: 5px 0;
        border-left: 3px solid #a0aec0;
    }}
    @media print {{
        body {{ margin: 20px; }}
    }}
</style>
</head>
<body>
<h1>Purchase Agreement Data Summary</h1>
<div class="meta">"""

    if filename:
        html += f"Source: {filename}<br>"
    html += f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>"

    # Parties
    html += "<h2>Parties</h2><table>"
    buyers = data.get("parties", {}).get("buyers", [])
    for i, b in enumerate(buyers, 1):
        name = b.get("name", "N/A")
        etype = b.get("entity_type", "individual")
        ename = b.get("entity_name", "")
        extra = ""
        if etype != "individual":
            extra = f" <em>({etype}"
            if ename:
                extra += f" — {ename}"
            extra += ")</em>"
        html += f"<tr><td>Buyer {i}</td><td>{name}{extra}</td></tr>"

    sellers = data.get("parties", {}).get("sellers", [])
    for i, s in enumerate(sellers, 1):
        name = s.get("name", "N/A")
        etype = s.get("entity_type", "individual")
        ename = s.get("entity_name", "")
        extra = ""
        if etype != "individual":
            extra = f" <em>({etype}"
            if ename:
                extra += f" — {ename}"
            extra += ")</em>"
        html += f"<tr><td>Seller {i}</td><td>{name}{extra}</td></tr>"
    html += "</table>"

    # Property
    html += "<h2>Property</h2><table>"
    prop = data.get("property", {})
    html += f"<tr><td>Address</td><td>{prop.get('street_address', 'N/A')}</td></tr>"
    unit = prop.get("unit_no")
    if unit:
        html += f"<tr><td>Unit No.</td><td>{unit}</td></tr>"
    html += f"<tr><td>City</td><td>{prop.get('city', 'N/A')}</td></tr>"
    html += f"<tr><td>County</td><td>{prop.get('county', 'N/A')}</td></tr>"
    html += f"<tr><td>State</td><td>{prop.get('state', 'Minnesota')}</td></tr>"
    html += f"<tr><td>Zip</td><td>{prop.get('zip_code', 'N/A')}</td></tr>"
    pid = prop.get("pid")
    if pid:
        html += f"<tr><td>PID / Parcel #</td><td>{pid}</td></tr>"
    html += f"<tr><td>Legal Description from PA</td><td>{prop.get('legal_description', 'N/A')}</td></tr>"
    html += "</table>"

    # Financial
    html += "<h2>Financial</h2><table>"
    fin = data.get("financial", {})
    price = fin.get("purchase_price", 0)
    html += f"<tr><td>Purchase Price</td><td>${price:,.2f}</td></tr>"
    em = fin.get("earnest_money_amount", 0)
    html += f"<tr><td>Earnest Money</td><td>${em:,.2f}</td></tr>"
    holder = fin.get("earnest_money_holder")
    if holder:
        html += f"<tr><td>Earnest Money Holder</td><td>{holder}</td></tr>"
    html += f"<tr><td>Financing Type</td><td>{fin.get('financing_type', 'N/A')}</td></tr>"
    dp = fin.get("down_payment_amount")
    if dp:
        html += f"<tr><td>Down Payment</td><td>${dp:,.2f}</td></tr>"
    sc = fin.get("seller_concessions")
    if sc:
        html += f"<tr><td>Seller Concessions</td><td>${sc:,.2f}</td></tr>"
    # Financing breakdown
    cash_pct = fin.get("cash_pct")
    if cash_pct is not None:
        cash_amt = fin.get("cash_amount") or (price * cash_pct / 100 if price else 0)
        html += f"<tr><td>Cash</td><td>{cash_pct}% (${cash_amt:,.2f})</td></tr>"
    mortgage_pct = fin.get("mortgage_pct")
    if mortgage_pct is not None:
        mort_amt = fin.get("mortgage_amount") or (price * mortgage_pct / 100 if price else 0)
        html += f"<tr><td>Mortgage Financing</td><td>{mortgage_pct}% (${mort_amt:,.2f})</td></tr>"
    assumption_pct = fin.get("assumption_pct")
    if assumption_pct is not None:
        assump_amt = fin.get("assumption_amount") or (price * assumption_pct / 100 if price else 0)
        html += f"<tr><td>Assumption</td><td>{assumption_pct}% (${assump_amt:,.2f})</td></tr>"
    cfd_pct = fin.get("contract_for_deed_pct")
    if cfd_pct is not None:
        cfd_amt = fin.get("contract_for_deed_amount") or (price * cfd_pct / 100 if price else 0)
        html += f"<tr><td>Contract for Deed</td><td>{cfd_pct}% (${cfd_amt:,.2f})</td></tr>"
    html += "</table>"

    # Dates
    html += "<h2>Key Dates</h2><table>"
    dates = data.get("dates", {})
    date_labels = [
        ("purchase_agreement_date", "Purchase Agreement Date"),
        ("closing_date", "Closing Date"),
        ("possession_date", "Possession Date"),
        ("buyer_signature_date", "Buyer Signature Date"),
        ("seller_signature_date", "Seller Signature Date"),
    ]
    for key, label in date_labels:
        val = dates.get(key)
        if val:
            html += f"<tr><td>{label}</td><td>{val}</td></tr>"
    html += "</table>"

    # Title & Closing
    html += "<h2>Title &amp; Closing</h2><table>"
    tc = data.get("title_and_closing", {})
    tc_fields = [
        ("title_company", "Title Company"),
        ("closing_agent", "Closing Agent"),
        ("listing_agent_name", "Listing Agent"),
        ("listing_brokerage", "Listing Brokerage"),
        ("selling_agent_name", "Selling Agent"),
        ("selling_brokerage", "Selling Brokerage"),
    ]
    for key, label in tc_fields:
        val = tc.get(key)
        if val:
            html += f"<tr><td>{label}</td><td>{val}</td></tr>"
    html += "</table>"

    # Contingencies
    html += "<h2>Contingencies</h2><table>"
    cont = data.get("contingencies", {})
    cont_flags = [
        ("financing_contingency", "Financing"),
        ("inspection_contingency", "Inspection"),
        ("appraisal_contingency", "Appraisal"),
        ("sale_of_buyers_property", "Sale of Buyer's Property"),
    ]
    active = [label for key, label in cont_flags if cont.get(key)]
    if active:
        html += f'<tr><td>Active</td><td class="contingency-active">{", ".join(active)}</td></tr>'
    else:
        html += '<tr><td>Active</td><td>None</td></tr>'
    other = cont.get("other_contingencies", [])
    if other:
        html += f"<tr><td>Other</td><td>{'; '.join(other)}</td></tr>"
    html += "</table>"

    # Well/Septic
    html += "<h2>Well / Septic</h2><table>"
    ws = data.get("well_septic", {})
    pa_well = ws.get("pa_well_known")
    well_display = "Yes" if pa_well is True else "No" if pa_well is False else "Not stated"
    html += f"<tr><td>PA — Seller knows of wells</td><td>{well_display}</td></tr>"
    pa_ssts = ws.get("pa_ssts_on_property")
    ssts_display = "Yes" if pa_ssts is True else "No" if pa_ssts is False else "Not stated"
    html += f"<tr><td>PA — SSTS on property</td><td>{ssts_display}</td></tr>"
    disc_well = ws.get("disclosure_well_info")
    if disc_well:
        html += f"<tr><td>Disclosure — Well</td><td>{disc_well}</td></tr>"
    disc_ssts = ws.get("disclosure_ssts_info")
    if disc_ssts:
        html += f"<tr><td>Disclosure — SSTS</td><td>{disc_ssts}</td></tr>"
    wn = ws.get("well_number")
    if wn:
        html += f"<tr><td>Well Number (MDH)</td><td>{wn}</td></tr>"
    html += "</table>"
    if ws.get("discrepancy_flag"):
        html += '<div class="flag"><span class="flag-label">Well/Septic</span>: Discrepancy between PA and Disclosure Statement</div>'

    # HOA
    hoa_data = data.get("hoa", {})
    if hoa_data.get("hoa_present"):
        html += "<h2>HOA / Association</h2><table>"
        html += "<tr><td>HOA Present</td><td>Yes</td></tr>"
        hoa_name = hoa_data.get("hoa_name")
        if hoa_name:
            html += f"<tr><td>HOA Name</td><td>{hoa_name}</td></tr>"
        hoa_dues = hoa_data.get("hoa_dues_amount")
        if hoa_dues:
            freq = hoa_data.get("hoa_dues_frequency", "")
            html += f"<tr><td>HOA Dues</td><td>${hoa_dues:,.2f} {freq}</td></tr>"
        html += "</table>"

    # Home Warranty, Other Terms, FIRPTA
    html += "<h2>Additional</h2><table>"
    hw = data.get("home_warranty", {})
    hw_details = hw.get("plan_details", "No Home Protection/Warranty Plan")
    html += f"<tr><td>Home Warranty</td><td>{hw_details or 'No Home Protection/Warranty Plan'}</td></tr>"
    other_terms = data.get("other_terms")
    if other_terms:
        html += f"<tr><td>Other Terms</td><td>{other_terms}</td></tr>"
    firpta = data.get("firpta", {})
    is_foreign = firpta.get("seller_is_foreign_person")
    if is_foreign is True:
        html += "<tr><td>FIRPTA</td><td>Seller IS a foreign person</td></tr>"
    elif is_foreign is False:
        html += "<tr><td>FIRPTA</td><td>Seller IS NOT a foreign person</td></tr>"
    html += "</table>"

    # Addenda — filtered
    addenda = data.get("addenda", [])
    excluded = ["wire fraud", "arbitration", "lead-based paint", "lead based paint"]
    filtered = [a for a in addenda if not any(
        ex in a.get("addendum_title", "").lower() for ex in excluded
    )]
    if filtered:
        html += "<h2>Addenda</h2>"
        for i, a in enumerate(filtered, 1):
            title = a.get("addendum_title", f"Addendum {i}")
            summary = a.get("summary", "")
            date = a.get("addendum_date", "")
            html += f'<div class="addendum"><strong>{i}. {title}</strong>'
            if date:
                html += f" <em>({date})</em>"
            if summary:
                html += f"<br>{summary}"
            html += "</div>"

    # Flags
    flags = data.get("extraction_metadata", {}).get("flags", [])
    if flags:
        html += "<h2>⚠ Extraction Flags</h2>"
        for f in flags:
            html += f'<div class="flag"><span class="flag-label">{f.get("field", "?")}</span>: '
            html += f'[{f.get("issue", "?")}] {f.get("note", "")}</div>'

    html += "</body></html>"
    return html

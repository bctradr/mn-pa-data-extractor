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
    lines.append(f"City: {prop.get('city', 'N/A')}")
    lines.append(f"County: {prop.get('county', 'N/A')}")
    lines.append(f"State: {prop.get('state', 'Minnesota')}")
    lines.append(f"Zip: {prop.get('zip_code', 'N/A')}")
    pid = prop.get("pid")
    if pid:
        lines.append(f"PID/Parcel #: {pid}")
    lines.append(f"Legal Description: {prop.get('legal_description', 'N/A')}")
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
    lines.append("")

    # Dates
    lines.append("-" * 40)
    lines.append("KEY DATES")
    lines.append("-" * 40)
    dates = data.get("dates", {})
    date_labels = [
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

    # MN Disclosures
    lines.append("-" * 40)
    lines.append("MN-SPECIFIC DISCLOSURES")
    lines.append("-" * 40)
    mn = data.get("mn_specific_disclosures", {})
    well = "Yes" if mn.get("well_disclosure_present") else "No"
    lines.append(f"Well Disclosure: {well}")
    wn = mn.get("well_number")
    if wn:
        lines.append(f"Well Number (MDH): {wn}")
    septic = "Yes" if mn.get("septic_disclosure_present") else "No"
    lines.append(f"Septic Disclosure: {septic}")
    st_val = mn.get("septic_system_type")
    if st_val:
        lines.append(f"Septic Type: {st_val}")
    hoa = "Yes" if mn.get("hoa_present") else "No"
    lines.append(f"HOA: {hoa}")
    hoa_name = mn.get("hoa_name")
    if hoa_name:
        lines.append(f"HOA Name: {hoa_name}")
    hoa_dues = mn.get("hoa_dues_amount")
    if hoa_dues:
        freq = mn.get("hoa_dues_frequency", "")
        lines.append(f"HOA Dues: ${hoa_dues:,.2f} {freq}")
    lines.append("")

    # Addenda
    addenda = data.get("addenda", [])
    if addenda:
        lines.append("-" * 40)
        lines.append("ADDENDA")
        lines.append("-" * 40)
        for i, a in enumerate(addenda, 1):
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
    html += f"<tr><td>City</td><td>{prop.get('city', 'N/A')}</td></tr>"
    html += f"<tr><td>County</td><td>{prop.get('county', 'N/A')}</td></tr>"
    html += f"<tr><td>State</td><td>{prop.get('state', 'Minnesota')}</td></tr>"
    html += f"<tr><td>Zip</td><td>{prop.get('zip_code', 'N/A')}</td></tr>"
    pid = prop.get("pid")
    if pid:
        html += f"<tr><td>PID / Parcel #</td><td>{pid}</td></tr>"
    html += f"<tr><td>Legal Description</td><td>{prop.get('legal_description', 'N/A')}</td></tr>"
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
    html += "</table>"

    # Dates
    html += "<h2>Key Dates</h2><table>"
    dates = data.get("dates", {})
    date_labels = [
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

    # MN Disclosures
    html += "<h2>MN-Specific Disclosures</h2><table>"
    mn = data.get("mn_specific_disclosures", {})
    well = "Yes" if mn.get("well_disclosure_present") else "No"
    html += f"<tr><td>Well Disclosure</td><td>{well}</td></tr>"
    wn = mn.get("well_number")
    if wn:
        html += f"<tr><td>Well Number (MDH)</td><td>{wn}</td></tr>"
    septic = "Yes" if mn.get("septic_disclosure_present") else "No"
    html += f"<tr><td>Septic Disclosure</td><td>{septic}</td></tr>"
    st_val = mn.get("septic_system_type")
    if st_val:
        html += f"<tr><td>Septic Type</td><td>{st_val}</td></tr>"
    hoa = "Yes" if mn.get("hoa_present") else "No"
    html += f"<tr><td>HOA</td><td>{hoa}</td></tr>"
    hoa_name = mn.get("hoa_name")
    if hoa_name:
        html += f"<tr><td>HOA Name</td><td>{hoa_name}</td></tr>"
    hoa_dues = mn.get("hoa_dues_amount")
    if hoa_dues:
        freq = mn.get("hoa_dues_frequency", "")
        html += f"<tr><td>HOA Dues</td><td>${hoa_dues:,.2f} {freq}</td></tr>"
    html += "</table>"

    # Addenda
    addenda = data.get("addenda", [])
    if addenda:
        html += "<h2>Addenda</h2>"
        for i, a in enumerate(addenda, 1):
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

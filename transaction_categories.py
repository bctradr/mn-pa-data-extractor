"""
transaction_categories.py
═════════════════════════
Two-tier transaction classification + template-name resolution.

Transaction Type (high-level: 3 options) → Order Type (specific: 5–7 each)
        ↓ + Property State + Construction-Loan flag
            → Template name (for CSV export to TPS)
"""

# ── Tier 1: Transaction Type ─────────────────────────
TRANSACTION_TYPES = ["Purchase", "Refinance", "Other"]


# ── Tier 2: Order Type (per Transaction Type) ────────
ORDER_TYPES_BY_TXN = {
    "Purchase": [
        "Buyside - Loan",
        "Buyside - Cash",
        "Seller Side - No TI",
        "Seller Side - TI",
        "Dual - Loan",
        "Dual - Cash",
        "Title Insurance Only",
    ],
    "Refinance": [
        "Residence / 2nd Home",
        "Commercial / Investor",
        "Construction Loan",
        "Loan Modification",
    ],
    "Other": [
        "Title Report (OE)",
        "Title Report (Listing Pre-Check)",
        "Recording Service Only",
        "Title Ins. Only - No Transaction",
        "Notary Signing Only",
    ],
}


# ── Property states (for refinance template routing) ──
PROPERTY_STATES = ["MN", "WI", "FL", "Other (workshare state)"]


# ── Template mapping ─────────────────────────────────
# Refinance templates depend on property state EXCEPT for Construction Loan
# (always MN-specific) and Loan Modification (always MN refinance template).
_REFI_BY_STATE = {
    "MN": "1.3 MN REFINANCE",
    "WI": "2.4 WI REFINANCE CDF",
    "FL": "3.1 FL Refinance CDF",
    "Other (workshare state)": "4.1 Workshare Refinance",
}

# Purchase + Other are state-agnostic.
_PURCHASE_TEMPLATES = {
    "Buyside - Loan":         "1.0 MN PURCH-BUYER CDF",
    "Buyside - Cash":         "1.0 MN PURCH-BUYER CDF",
    "Seller Side - No TI":    "1.2 MN SELLER SIDE",
    "Seller Side - TI":       "1.2 MN SELLER SIDE",
    "Dual - Loan":            "1.1 MN PURCH-DUAL CDF",
    "Dual - Cash":            "1.1 MN PURCH-DUAL CDF",
    "Title Insurance Only":   "1.4 MN FNF-PHX NCS TITLE ONLY",
}

_OTHER_TEMPLATES = {
    "Title Report (OE)":                "0.10 OE Report",
    "Title Report (Listing Pre-Check)": "1.5 Listing-Title Pre-Check",
    "Recording Service Only":           "0.11 Recording Service Only",
    "Title Ins. Only - No Transaction": "1.4 MN FNF-PHX NCS TITLE ONLY",
    "Notary Signing Only":              "0.12 Courtesy Closing",
}


def get_template_name(transaction_type: str, order_type: str, property_state: str = "") -> str:
    """Return the template name based on the three-way classification.
    
    Returns "" when any required input is missing or unmapped.
    """
    if not transaction_type or not order_type:
        return ""

    if transaction_type == "Purchase":
        return _PURCHASE_TEMPLATES.get(order_type, "")

    if transaction_type == "Other":
        return _OTHER_TEMPLATES.get(order_type, "")

    if transaction_type == "Refinance":
        # Construction Loan is MN-only regardless of property state
        if order_type == "Construction Loan":
            return "1.3a MN REFI - CONST LOAN"
        # Loan Modification routes to MN refi template regardless of state
        if order_type == "Loan Modification":
            return "1.3 MN REFINANCE"
        # Residence/2nd Home and Commercial/Investor — state-routed
        if order_type in ("Residence / 2nd Home", "Commercial / Investor"):
            return _REFI_BY_STATE.get(property_state, "")

    return ""


# ── Buyside / Sellside / Dual classification ─────────
# Used by assignment_rules.py for Lisa/Marcy/Paula's conditional assistant
# (Ashley = buyside, Sandra = sellside, "Ashley & Sandra" = dual).
_SELLSIDE_ORDER_TYPES = {"Seller Side - No TI", "Seller Side - TI"}
_DUAL_ORDER_TYPES = {"Dual - Loan", "Dual - Cash"}


def transaction_side(order_type: str) -> str:
    """Return one of: 'sellside', 'dual', 'buyside' (default).
    
    Refinance and Other order types all classify as 'buyside' for the
    assistant-assignment rule.
    """
    if order_type in _SELLSIDE_ORDER_TYPES:
        return "sellside"
    if order_type in _DUAL_ORDER_TYPES:
        return "dual"
    return "buyside"

"""
assignment_rules.py
═══════════════════
Closer-driven defaults for Underwriter Code, Office, and Assistant.
"""

from transaction_categories import transaction_side


# ── Dropdown lists ────────────────────────────────────

CLOSERS = [
    "Paula", "Trina", "Jenny", "Angie", "Chelsea", "Carmen",
    "Lorrie", "Lisa", "Sara", "Kami", "Molly", "Marcy",
    "Pam", "Carrie", "Nicole",
]

OFFICES = [
    "Lake Elmo", "Blaine", "Maple Grove", "Otsego",
    "Coon Rapids KW", "Coon Rapids Main", "Forest Lake",
    "Edina", "Ramsey",
]

UW_CODES = ["ST", "OR", "CT", "FA"]


# ── Closer assignment rules ───────────────────────────
# Closers whose assistant doesn't depend on order type
_STATIC_DEFAULTS = {
    "Angie":   {"underwriter_code": "OR", "office": "Lake Elmo",        "assistant": "Lydia"},
    "Carmen":  {"underwriter_code": "OR", "office": "Blaine",           "assistant": "Ashley"},
    "Carrie":  {"underwriter_code": "FA", "office": "Maple Grove",      "assistant": "Ryan"},
    "Chelsea": {"underwriter_code": "OR", "office": "Otsego",           "assistant": "Ryan"},
    "Jenny":   {"underwriter_code": "OR", "office": "Lake Elmo",        "assistant": "Maddie"},
    "Kami":    {"underwriter_code": "CT", "office": "Lake Elmo",        "assistant": "Carolyn"},
    "Lorrie":  {"underwriter_code": "CT", "office": "Forest Lake",      "assistant": "Nicole"},
    "Molly":   {"underwriter_code": "CT", "office": "Coon Rapids Main", "assistant": "Ryan"},
    "Pam":     {"underwriter_code": "FA", "office": "Edina",            "assistant": "Jessica"},
    "Sara":    {"underwriter_code": "CT", "office": "Edina",            "assistant": "Jessica"},
    "Trina":   {"underwriter_code": "ST", "office": "Otsego",           "assistant": "Kim T."},
    "Nicole":  {"underwriter_code": "CT", "office": "Forest Lake",      "assistant": "Nicole"},
}

# Closers whose assistant depends on order type (buyside / sellside / dual)
_CONDITIONAL_DEFAULTS = {
    "Lisa":  {"underwriter_code": "CT", "office": "Coon Rapids KW"},
    "Marcy": {"underwriter_code": "CT", "office": "Coon Rapids KW"},
    "Paula": {"underwriter_code": "ST", "office": "Ramsey"},
}


def _assistant_for_order_type(order_type: str) -> str:
    """Lisa/Marcy/Paula buyside-vs-sellside-vs-dual rule.
    
    Ashley = buyside default.
    Sandra = sellside.
    "Ashley & Sandra" = dual.
    """
    side = transaction_side(order_type)
    if side == "sellside":
        return "Sandra"
    if side == "dual":
        return "Ashley & Sandra"
    return "Ashley"


def get_assignment(closer: str, order_type: str = "") -> dict:
    """Return autofill defaults {underwriter_code, office, assistant} for a given closer.
    
    All three values can be edited by the user after autofill.
    """
    empty = {"underwriter_code": "", "office": "", "assistant": ""}
    if not closer:
        return empty
    if closer in _STATIC_DEFAULTS:
        return _STATIC_DEFAULTS[closer].copy()
    if closer in _CONDITIONAL_DEFAULTS:
        d = _CONDITIONAL_DEFAULTS[closer].copy()
        d["assistant"] = _assistant_for_order_type(order_type)
        return d
    return empty

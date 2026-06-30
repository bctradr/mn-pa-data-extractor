"""
6_Manage_Municipalities.py
Municipal contact directory — browse, search, and edit municipality contact info
for the Water Bill Tracker.
"""

import streamlit as st
import pandas as pd

from water_bills import get_municipalities, create_municipality, update_municipality
from ui_theme import apply_theme, section_header, section_bar

try:
    st.set_page_config(page_title="Municipalities", page_icon="🏛️", layout="wide")
except Exception:
    pass

apply_theme()

_METHODS = ["email", "fax", "phone", "portal"]
_STATES  = ["MN", "WI"]


def _muni_label(m: dict) -> str:
    state = m.get("state")
    return f"{m['name']}, {state}" if state else m["name"]


# ── Session state ──────────────────────────────────────────────────────────────

if "mm_selected_id" not in st.session_state:
    st.session_state.mm_selected_id = None
if "mm_show_add" not in st.session_state:
    st.session_state.mm_show_add = False


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════

hdr_col, btn_col = st.columns([7, 1])
with hdr_col:
    st.title("🏛️ Manage Municipalities")
with btn_col:
    st.markdown("")
    if st.button("➕ Add Municipality", type="primary", use_container_width=True):
        st.session_state.mm_show_add = not st.session_state.mm_show_add
        st.session_state.mm_selected_id = None
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ADD MUNICIPALITY FORM
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.mm_show_add:
    with st.expander("➕ New Municipality", expanded=True):
        with st.form("mm_add_form", clear_on_submit=True):
            ac1, ac2    = st.columns([3, 1])
            add_name    = ac1.text_input("Municipality Name")
            add_state   = ac2.selectbox("State", _STATES)
            bc1, bc2    = st.columns(2)
            add_method  = bc1.selectbox("Preferred Method", ["—"] + _METHODS)
            add_lead    = bc2.number_input("Lead Time (days)", min_value=0, max_value=60, value=7)
            add_email   = st.text_input("Email")
            cc1, cc2    = st.columns(2)
            add_fax     = cc1.text_input("Fax")
            add_portal  = cc2.text_input("Portal URL")
            add_notes   = st.text_area("Notes", height=68)
            add_save    = st.form_submit_button("💾 Save", type="primary")
        if add_save:
            if not add_name.strip():
                st.error("Name is required.")
            else:
                try:
                    create_municipality({
                        "name":             add_name.strip(),
                        "state":            add_state,
                        "preferred_method": add_method if add_method != "—" else None,
                        "lead_time_days":   int(add_lead) if add_lead else None,
                        "email":            add_email or None,
                        "fax":              add_fax or None,
                        "portal_url":       add_portal or None,
                        "notes":            add_notes or None,
                    })
                    st.success(f"Added {add_name.strip()}, {add_state}.")
                    st.session_state.mm_show_add = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# LOAD + SUMMARY STATS
# ══════════════════════════════════════════════════════════════════════════════

try:
    all_munis = get_municipalities()
except Exception as e:
    st.error(f"Failed to load municipalities: {e}")
    st.stop()

total       = len(all_munis)
has_contact = sum(1 for m in all_munis if m.get("preferred_method"))
missing     = total - has_contact

sm1, sm2, sm3 = st.columns(3)
sm1.metric("Total Municipalities", total)
sm2.metric("Have Contact Info",    has_contact)
sm3.metric("Missing Contact Info", missing)


# ══════════════════════════════════════════════════════════════════════════════
# FILTERS + TABLE
# ══════════════════════════════════════════════════════════════════════════════

section_bar("Municipality List")
fc1, fc2, fc3, fc4 = st.columns([3, 1, 2, 1])
search_q     = fc1.text_input("Search", placeholder="Type to filter by name…",
                               label_visibility="collapsed")
state_filter = fc2.selectbox("State", ["All"] + _STATES, label_visibility="collapsed")
missing_only = fc3.checkbox("Missing contact info only")
with fc4:
    st.markdown("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

filtered = all_munis
if search_q:
    sq = search_q.strip().lower()
    filtered = [m for m in filtered if sq in (m.get("name") or "").lower()]
if state_filter != "All":
    filtered = [m for m in filtered if m.get("state") == state_filter]
if missing_only:
    filtered = [m for m in filtered if not m.get("preferred_method")]

rows = [
    {
        "Name":      m.get("name") or "—",
        "State":     m.get("state") or "—",
        "Method":    m.get("preferred_method") or "—",
        "Email":     m.get("email") or "—",
        "Lead Time": str(m["lead_time_days"]) if m.get("lead_time_days") is not None else "—",
        "Notes":     (m.get("notes") or "")[:60],
    }
    for m in filtered
]
df = (
    pd.DataFrame(rows)
    if rows
    else pd.DataFrame(columns=["Name", "State", "Method", "Email", "Lead Time", "Notes"])
)

st.caption(f"Showing {len(filtered):,} of {total:,} municipalities · click a row to edit")
selection = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Name":      st.column_config.TextColumn(width="large"),
        "State":     st.column_config.TextColumn(width="small"),
        "Method":    st.column_config.TextColumn(width="medium"),
        "Email":     st.column_config.TextColumn(width="large"),
        "Lead Time": st.column_config.TextColumn(width="small"),
        "Notes":     st.column_config.TextColumn(width="large"),
    },
)

selected_rows = (
    selection.selection.rows
    if selection and selection.selection
    else []
)
if selected_rows:
    st.session_state.mm_selected_id = filtered[selected_rows[0]]["id"]


# ══════════════════════════════════════════════════════════════════════════════
# EDIT PANEL
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.mm_selected_id:
    st.stop()

muni = next(
    (m for m in all_munis if m["id"] == st.session_state.mm_selected_id), None
)
if not muni:
    st.warning("Selected municipality not found — it may have been deleted.")
    st.session_state.mm_selected_id = None
    st.stop()

st.divider()

dh_col, dc_col = st.columns([8, 1])
with dh_col:
    label_str = _muni_label(muni)
    st.subheader(f"✏️ {label_str}")
with dc_col:
    st.markdown("")
    if st.button("✕ Close", key="mm_close"):
        st.session_state.mm_selected_id = None
        st.rerun()

section_header("Edit Municipality")
with st.container(border=True):
    with st.form(f"mm_edit_{muni['id']}"):
        ec1, ec2    = st.columns([3, 1])
        edit_name   = ec1.text_input("Name",  value=muni.get("name") or "")
        state_opts  = ["—"] + _STATES
        edit_state  = ec2.selectbox(
            "State",
            options=state_opts,
            index=state_opts.index(muni["state"]) if muni.get("state") in _STATES else 0,
        )
        bc1, bc2    = st.columns(2)
        method_opts = ["—"] + _METHODS
        curr_method = muni.get("preferred_method") or "—"
        edit_method = bc1.selectbox(
            "Preferred Method",
            options=method_opts,
            index=method_opts.index(curr_method) if curr_method in method_opts else 0,
        )
        edit_lead   = bc2.number_input(
            "Lead Time (days)",
            min_value=0,
            max_value=60,
            value=int(muni["lead_time_days"]) if muni.get("lead_time_days") is not None else 0,
        )
        edit_email  = st.text_input("Email",      value=muni.get("email") or "")
        cc1, cc2    = st.columns(2)
        edit_fax    = cc1.text_input("Fax",       value=muni.get("fax") or "")
        edit_portal = cc2.text_input("Portal URL", value=muni.get("portal_url") or "")
        edit_notes  = st.text_area("Notes",        value=muni.get("notes") or "", height=100)
        save_edit   = st.form_submit_button("💾 Save Changes", type="primary")

    if save_edit:
        if not edit_name.strip():
            st.error("Name is required.")
        else:
            try:
                update_municipality(muni["id"], {
                    "name":             edit_name.strip(),
                    "state":            edit_state if edit_state != "—" else None,
                    "preferred_method": edit_method if edit_method != "—" else None,
                    "lead_time_days":   int(edit_lead) if edit_lead else None,
                    "email":            edit_email or None,
                    "fax":              edit_fax or None,
                    "portal_url":       edit_portal or None,
                    "notes":            edit_notes or None,
                })
                st.success("Saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

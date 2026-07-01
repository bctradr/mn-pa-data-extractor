"""
5_Water_Bills.py
══════════════════
Water Bill Requests — create and track water bill requests to municipalities.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from water_bills import (
    get_municipalities,
    create_municipality,
    update_municipality,
    create_request,
    get_requests,
    get_request,
    update_request,
    log_followup,
    upload_bill_pdf,
    get_bill_pdf_url,
    calculate_send_by_date,
    cancel_request,
    complete_request,
    compose_water_bill_email,
    process_inbox_replies,
    get_unmatched_messages,
    update_unmatched_message,
    get_bounced_requests,
)
from gmail_client import send_email, check_inbox
from ui_theme import apply_theme, section_header, section_bar

try:
    st.set_page_config(page_title="Water Bills", page_icon="💧", layout="wide")
except Exception:
    pass

apply_theme()

# ── Constants ─────────────────────────────────────────────────────────────────

_STATUS_LABELS = {
    "pending":        "⚪ Pending",
    "sent":           "🔵 Sent",
    "follow_up_sent": "🟠 Follow-up Sent",
    "received":       "🟢 Received",
    "cancelled":      "🔴 Cancelled",
    "completed":      "✅ Completed",
}
_STATUSES = ["pending", "sent", "follow_up_sent", "received", "cancelled", "completed"]
_ACTIONS  = ["sent", "follow_up", "phone_call", "received", "note"]
_METHODS  = ["email", "fax", "phone", "portal"]


def _status_label(s: str) -> str:
    return _STATUS_LABELS.get(s, s or "—")


def _muni_label(m: dict) -> str:
    state = m.get("state")
    return f"{m['name']}, {state}" if state else m["name"]


def _fmt_ts(ts: str) -> str:
    if not ts:
        return "—"
    return ts[:16].replace("T", " ")


# ── Session state ─────────────────────────────────────────────────────────────

if "wb_show_form" not in st.session_state:
    st.session_state.wb_show_form = False
if "wb_selected_id" not in st.session_state:
    st.session_state.wb_selected_id = None
if "wb_date_preset" not in st.session_state:
    st.session_state.wb_date_preset = "all"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title("💧 Water Bill Requests")
_, btn_col = st.columns([5, 1.5])
with btn_col:
    if st.button("➕ New Request", type="primary", use_container_width=True):
        st.session_state.wb_show_form = not st.session_state.wb_show_form
        st.session_state.wb_selected_id = None
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# NEW REQUEST FORM
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.wb_show_form:
    try:
        municipalities = get_municipalities()
    except Exception:
        municipalities = []
    muni_options = [_muni_label(m) for m in municipalities]
    muni_map     = {_muni_label(m): m for m in municipalities}

    with st.expander("➕ New Water Bill Request", expanded=True):
        with st.expander("➕ City not in list? Add it first", expanded=False):
            with st.form("wb_quickadd_muni", clear_on_submit=True):
                qa_c1, qa_c2 = st.columns([3, 1])
                qa_name  = qa_c1.text_input("Name")
                qa_state = qa_c2.selectbox("State", ["MN", "WI"])
                qa_save  = st.form_submit_button("Create", type="primary")
            if qa_save:
                if qa_name.strip():
                    try:
                        create_municipality({"name": qa_name.strip(), "state": qa_state})
                        st.success(
                            f"Created '{qa_name.strip()}, {qa_state}'. "
                            "Select it in the municipality dropdown below."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
                else:
                    st.error("Name is required.")

        section_header("Property & Parties")
        with st.form("wb_new_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            file_number      = fc1.text_input("File Number")
            property_address = fc2.text_input("Property Address")
            pc1, pc2         = st.columns(2)
            current_owners   = pc1.text_input("Current Owners")
            new_buyers       = pc2.text_input("New Buyers")
            closing_date_new = st.date_input("Closing Date", value=None)

            st.markdown("**Municipality**")
            muni_choice = st.selectbox(
                "Municipality",
                options=["— select municipality —"] + muni_options,
                label_visibility="collapsed",
            )
            if muni_choice == "— select municipality —":
                muni_id   = None
                muni_name = None
                pref_idx  = 0
            else:
                chosen    = muni_map.get(muni_choice, {})
                muni_id   = chosen.get("id")
                muni_name = chosen.get("name")
                pref      = chosen.get("preferred_method") or "email"
                pref_idx  = _METHODS.index(pref) if pref in _METHODS else 0

            req_method = st.selectbox("Request Method", _METHODS, index=pref_idx)

            section_header("Closer & Assistant")
            cc1, cc2, cc3 = st.columns(3)
            closer_name  = cc1.text_input("Closer Name")
            closer_email = cc2.text_input("Closer Email")
            closer_phone = cc3.text_input("Closer Phone")
            ac1, ac2, ac3 = st.columns(3)
            asst_name  = ac1.text_input("Assistant Name")
            asst_email = ac2.text_input("Assistant Email")
            asst_phone = ac3.text_input("Assistant Phone")

            notes_new = st.text_area("Notes", height=68)

            save_new = st.form_submit_button("💾 Save Request", type="primary")

        if save_new:
            sbd_new, ltd_new = calculate_send_by_date(closing_date_new, muni_id)
            try:
                create_request({
                    "file_number":         file_number or None,
                    "property_address":    property_address or None,
                    "current_owners":      current_owners or None,
                    "new_buyers":          new_buyers or None,
                    "closing_date":        closing_date_new.isoformat() if closing_date_new else None,
                    "send_by_date":        sbd_new.isoformat() if sbd_new else None,
                    "lead_time_days_used": ltd_new,
                    "municipality_id":     muni_id,
                    "municipality_name":   muni_name,
                    "request_method":      req_method or None,
                    "closer_name":         closer_name or None,
                    "closer_email":        closer_email or None,
                    "closer_phone":        closer_phone or None,
                    "assistant_name":      asst_name or None,
                    "assistant_email":     asst_email or None,
                    "assistant_phone":     asst_phone or None,
                    "notes":               notes_new or None,
                })
                st.success("Request created.")
                st.session_state.wb_show_form = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create request: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# NEEDS ATTENTION BANNER
# ══════════════════════════════════════════════════════════════════════════════

_attn_items = []
_attn_error = None
try:
    _unmatched_msgs = get_unmatched_messages(status="new")
    _bounced_reqs   = get_bounced_requests()
    _attn_items = (
        [{"_type": "unmatched", **m} for m in _unmatched_msgs]
        + [{"_type": "bounced", **r}  for r in _bounced_reqs]
    )
except Exception as _attn_exc:
    _err_str = str(_attn_exc).lower()
    if "water_bill_unmatched_messages" in _err_str or "does not exist" in _err_str or "column" in _err_str:
        _attn_error = "migration"
    else:
        _attn_error = str(_attn_exc)

if _attn_error == "migration":
    st.info("Run migration 006 to enable the Needs Attention panel.")
elif _attn_error:
    st.warning(f"Needs Attention panel unavailable: {_attn_error}")
elif _attn_items:
    with st.expander(f"⚠️ {len(_attn_items)} item(s) need attention", expanded=True):
        try:
            _open_reqs = get_requests({"status": ["pending", "sent", "follow_up_sent"]})
        except Exception:
            _open_reqs = []
        _req_opts = {
            f"{r.get('file_number') or '—'}  —  {r.get('property_address') or '—'}": r["id"]
            for r in _open_reqs
        }

        for _item in _attn_items:
            _itype = _item["_type"]
            _iid   = _item.get("id")

            if _itype == "unmatched":
                _i_from  = _item.get("from_address") or "—"
                _i_subj  = _item.get("subject") or "(no subject)"
                _i_date  = (_item.get("checked_at") or "")[:10]
                _i_label = f"**Unmatched Message** · {_i_from} · _{_i_subj}_"
            else:
                _i_from  = _item.get("file_number") or "—"
                _i_subj  = _item.get("property_address") or "—"
                _i_date  = "—"
                _i_label = f"**Bounced Request** · File# {_i_from} · {_i_subj}"

            _ac1, _ac2, _ac3, _ac4 = st.columns([5, 1, 1.5, 1.5])
            _ac1.markdown(_i_label)
            _ac2.caption(_i_date)

            with _ac3:
                if _itype == "unmatched":
                    if st.button("🔗 Link", key=f"wb_attn_link_{_iid}"):
                        st.session_state[f"wb_attn_link_open_{_iid}"] = True
                else:
                    if st.button("View", key=f"wb_attn_view_{_iid}"):
                        st.session_state.wb_selected_id = _iid
                        st.rerun()

            with _ac4:
                if _itype == "unmatched":
                    if st.button("✕ Dismiss", key=f"wb_attn_dismiss_{_iid}"):
                        try:
                            update_unmatched_message(_iid, {"status": "dismissed"})
                            st.session_state.pop(f"wb_attn_link_open_{_iid}", None)
                            st.rerun()
                        except Exception as _de:
                            st.error(f"Dismiss failed: {_de}")

            if _itype == "unmatched" and st.session_state.get(f"wb_attn_link_open_{_iid}"):
                with st.form(f"wb_attn_link_form_{_iid}"):
                    _link_sel = st.selectbox(
                        "Link to request",
                        options=["— select —"] + list(_req_opts.keys()),
                    )
                    _lc1, _lc2 = st.columns(2)
                    _link_ok     = _lc1.form_submit_button("✅ Confirm", type="primary")
                    _link_cancel = _lc2.form_submit_button("Cancel")
                if _link_ok:
                    if _link_sel == "— select —":
                        st.error("Select a request first.")
                    else:
                        try:
                            _linked_rid = _req_opts[_link_sel]
                            update_unmatched_message(_iid, {
                                "status": "reviewed",
                                "linked_request_id": _linked_rid,
                            })
                            log_followup(
                                request_id=_linked_rid,
                                action="note",
                                method="email",
                                notes=f"Manually linked from unmatched inbox message — {_i_subj}",
                                logged_by="system",
                            )
                            st.session_state.pop(f"wb_attn_link_open_{_iid}", None)
                            st.rerun()
                        except Exception as _le:
                            st.error(f"Link failed: {_le}")
                if _link_cancel:
                    st.session_state.pop(f"wb_attn_link_open_{_iid}", None)
                    st.rerun()

            st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# FILTERS + TABLE
# ══════════════════════════════════════════════════════════════════════════════

today = date.today()
section_bar("All Requests")
_sc = st.columns([1, 1, 1.4, 1, 1.2, 1.2, 0.5])
cb_pending   = _sc[0].checkbox("⚪ Pending",        value=True,  key="wb_cb_pending")
cb_sent      = _sc[1].checkbox("🔵 Sent",            value=True,  key="wb_cb_sent")
cb_followup  = _sc[2].checkbox("🟠 Follow-up Sent",  value=True,  key="wb_cb_followup")
cb_received  = _sc[3].checkbox("🟢 Received",        value=False, key="wb_cb_received")
cb_completed = _sc[4].checkbox("✅ Completed",       value=False, key="wb_cb_completed")
cb_cancelled = _sc[5].checkbox("🔴 Cancelled",       value=False, key="wb_cb_cancelled")
with _sc[6]:
    st.markdown("<div style='padding-top:6px'></div>", unsafe_allow_html=True)
    if st.button("🔄", use_container_width=True, help="Refresh"):
        st.rerun()

status_filter = [s for s, v in [
    ("pending",        cb_pending),
    ("sent",           cb_sent),
    ("follow_up_sent", cb_followup),
    ("received",       cb_received),
    ("completed",      cb_completed),
    ("cancelled",      cb_cancelled),
] if v]

_PRESET_KEYS   = ["all", "this_week", "last_week", "this_month", "last_month", "custom"]
_PRESET_LABELS = ["All", "This Week", "Last Week", "This Month", "Last Month", "Custom"]
_dp = st.columns(len(_PRESET_KEYS))
for _i, (_pk, _pl) in enumerate(zip(_PRESET_KEYS, _PRESET_LABELS)):
    _active = st.session_state.wb_date_preset == _pk
    if _dp[_i].button(_pl, key=f"wb_dp_{_pk}", type="primary" if _active else "secondary",
                      use_container_width=True):
        st.session_state.wb_date_preset = None if _active else _pk
        st.rerun()

date_from = date_to = None
_preset = st.session_state.wb_date_preset
if _preset == "this_week":
    date_from = today - timedelta(days=today.weekday())
    date_to   = date_from + timedelta(days=6)
elif _preset == "last_week":
    date_from = today - timedelta(days=today.weekday() + 7)
    date_to   = date_from + timedelta(days=6)
elif _preset == "this_month":
    date_from = today.replace(day=1)
    date_to   = (today.replace(month=today.month + 1, day=1) - timedelta(days=1)) \
                if today.month < 12 else today.replace(month=12, day=31)
elif _preset == "last_month":
    _lm_end = today.replace(day=1) - timedelta(days=1)
    date_from = _lm_end.replace(day=1)
    date_to   = _lm_end
elif _preset == "custom":
    _dcc1, _dcc2 = st.columns(2)
    date_from = _dcc1.date_input("Closing from", value=None, key="wb_custom_from")
    date_to   = _dcc2.date_input("Closing to",   value=None, key="wb_custom_to")

filters: dict = {}
if status_filter:
    filters["status"] = status_filter
if date_from:
    filters["closing_date_from"] = date_from.isoformat()
if date_to:
    filters["closing_date_to"] = date_to.isoformat()

try:
    requests = get_requests(filters or None)
except Exception as e:
    st.error(f"Failed to load requests: {e}")
    st.stop()

if not requests:
    st.info("No requests match the current filters.")
    st.stop()

rows = []
raw_send_by = []  # parallel lists for row styling; not shown directly
raw_status = []
for r in requests:
    sbd_str = r.get("send_by_date")
    sbd = None
    if sbd_str:
        try:
            sbd = date.fromisoformat(sbd_str)
        except (ValueError, TypeError):
            pass
    raw_send_by.append(sbd)
    raw_status.append(r.get("status", ""))
    rows.append({
        "File #":       r.get("file_number") or "—",
        "Address":      r.get("property_address") or "—",
        "Municipality": r.get("municipality_name") or "—",
        "Method":       r.get("request_method") or "—",
        "Status":       _status_label(r.get("status", "")),
        "Send By":      sbd.isoformat() if sbd else "—",
        "Closing":      r.get("closing_date") or "—",
        "Updated":      _fmt_ts(r.get("updated_at", "")),
    })

df = pd.DataFrame(rows)


def _highlight_rows(row):
    sbd = raw_send_by[row.name]
    status = raw_status[row.name]
    if sbd is None or status in ("cancelled", "completed"):
        return [""] * len(row)
    if sbd < today:
        return ["background-color: #ffd5d5"] * len(row)   # red — overdue
    if sbd == today:
        return ["background-color: #fff3cd"] * len(row)   # amber — due today
    return [""] * len(row)


st.caption("Click a row to open the detail panel. 🔴 overdue · 🟠 due today")
selection = st.dataframe(
    df.style.apply(_highlight_rows, axis=1),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Address":      st.column_config.TextColumn(width="large"),
        "Municipality": st.column_config.TextColumn(width="medium"),
        "Status":       st.column_config.TextColumn(width="medium"),
        "Send By":      st.column_config.TextColumn(width="small"),
    },
)

selected_rows = (
    selection.selection.rows
    if selection and selection.selection
    else []
)
if selected_rows:
    st.session_state.wb_selected_id = requests[selected_rows[0]]["id"]


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL PANEL
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.wb_selected_id:
    st.stop()

rid = st.session_state.wb_selected_id

try:
    detail = get_request(rid)
except Exception as e:
    st.error(f"Failed to load request: {e}")
    st.stop()

_muni_data  = detail.get("municipalities") or {}
_muni_email = (_muni_data.get("email") or "").strip()
_is_email   = detail.get("request_method") == "email"

st.divider()

dh_col, dc_col = st.columns([8, 1])
with dh_col:
    addr_display = detail.get("property_address") or detail.get("file_number") or "Request Detail"
    st.subheader(f"{_status_label(detail.get('status', ''))}  ·  {addr_display}")
    if detail.get("municipality_name"):
        st.caption(
            f"Municipality: {detail['municipality_name']}  ·  "
            f"Method: {detail.get('request_method') or '—'}"
        )
with dc_col:
    if st.button("✕ Close", key="wb_close_detail"):
        st.session_state.wb_selected_id = None
        st.rerun()

# Terminal-state banner
_terminal_followup = next(
    (f for f in detail.get("followups", []) if f.get("action") in ("cancelled", "completed")),
    None,
)
if detail.get("status") == "cancelled":
    _reason = (_terminal_followup or {}).get("notes") or ""
    st.error("🔴 **Cancelled**" + (f" — {_reason}" if _reason else ""))
elif detail.get("status") == "completed":
    _comp_notes = (_terminal_followup or {}).get("notes") or ""
    st.success("✅ **Completed**" + (f" — {_comp_notes}" if _comp_notes else ""))

left_col, right_col = st.columns(2)


# ── Left: editable request fields ────────────────────────────────────────────

with left_col:
    try:
        municipalities_edit = get_municipalities()
    except Exception:
        municipalities_edit = []
    muni_labels_edit  = ["— none —"] + [_muni_label(m) for m in municipalities_edit]
    muni_label_to_obj = {_muni_label(m): m for m in municipalities_edit}

    # Full municipality record for Edit City Record (select("*") from get_municipalities)
    _cur_muni_obj = None
    if detail.get("municipality_id"):
        for _m in municipalities_edit:
            if _m["id"] == detail["municipality_id"]:
                _cur_muni_obj = _m
                break

    # Resolve current selection by ID (preferred) then fall back to name match.
    _cur_label = None
    if detail.get("municipality_id"):
        for _m in municipalities_edit:
            if _m["id"] == detail["municipality_id"]:
                _cur_label = _muni_label(_m)
                break
    if _cur_label is None and detail.get("municipality_name"):
        for _m in municipalities_edit:
            if _m.get("name") == detail["municipality_name"]:
                _cur_label = _muni_label(_m)
                break
    muni_edit_idx = (
        muni_labels_edit.index(_cur_label) if _cur_label in muni_labels_edit else 0
    )
    status_edit_idx = _STATUSES.index(detail.get("status", "pending")) if detail.get("status") in _STATUSES else 0
    method_edit_idx = _METHODS.index(detail.get("request_method", "email")) if detail.get("request_method") in _METHODS else 0

    cd_val = None
    if detail.get("closing_date"):
        try:
            cd_val = date.fromisoformat(detail["closing_date"])
        except (ValueError, TypeError):
            pass

    section_header("Request Details")
    with st.container(border=True):
        # Municipality email status — read-only, above the form
        if _muni_email:
            st.caption(f"Sending to: {_muni_email}")
        elif detail.get("municipality_id"):
            st.warning("No email on file for this municipality. Use Edit City Record to add one.")

        with st.form(f"wb_edit_{rid}"):
            ef1, ef2 = st.columns(2)
            fn_edit   = ef1.text_input("File Number",      value=detail.get("file_number") or "")
            addr_edit = ef2.text_input("Property Address", value=detail.get("property_address") or "")
            ow1, ow2  = st.columns(2)
            own_edit  = ow1.text_input("Current Owners",   value=detail.get("current_owners") or "")
            buy_edit  = ow2.text_input("New Buyers",       value=detail.get("new_buyers") or "")
            cd_edit   = st.date_input("Closing Date",      value=cd_val)

            mu1, mu2 = st.columns(2)
            muni_edit   = mu1.selectbox("Municipality",    muni_labels_edit, index=muni_edit_idx)
            method_edit = mu2.selectbox("Request Method",  _METHODS,        index=method_edit_idx)
            status_edit = st.selectbox(
                "Status", _STATUSES, index=status_edit_idx, format_func=_status_label
            )

            notes_edit = st.text_area("Notes", value=detail.get("notes") or "", height=68)
            save_edit  = st.form_submit_button("💾 Save Changes", type="primary")

        if save_edit:
            chosen_edit = muni_label_to_obj.get(muni_edit, {})
            try:
                update_request(rid, {
                    "file_number":       fn_edit or None,
                    "property_address":  addr_edit or None,
                    "current_owners":    own_edit or None,
                    "new_buyers":        buy_edit or None,
                    "closing_date":      cd_edit.isoformat() if cd_edit else None,
                    "municipality_id":   chosen_edit.get("id"),
                    "municipality_name": chosen_edit.get("name") if muni_edit != "— none —" else None,
                    "request_method":    method_edit,
                    "status":            status_edit,
                    "notes":             notes_edit or None,
                })
                st.success("Saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

        # Closer / assistant — read-only display (auto-populated from order intake)
        _cl = detail.get("closer_name") or "—"
        _as = detail.get("assistant_name") or "—"
        st.caption(f"Closer: {_cl}  ·  Assistant: {_as}")

    # Edit City Record — inline expander beneath Request Details
    with st.expander("✏️ Edit City Record", expanded=False):
        if not _cur_muni_obj:
            st.caption("Select a municipality on this request first.")
        else:
            _pref_methods = ["email", "fax", "phone", "portal"]
            _pref_idx = _pref_methods.index(_cur_muni_obj.get("preferred_method") or "email") \
                if (_cur_muni_obj.get("preferred_method") or "email") in _pref_methods else 0
            with st.form(f"wb_muni_edit_{rid}"):
                mc1, mc2 = st.columns([3, 1])
                muni_name_edit  = mc1.text_input("Name",  value=_cur_muni_obj.get("name") or "")
                muni_state_edit = mc2.selectbox("State", ["MN", "WI"],
                    index=0 if (_cur_muni_obj.get("state") or "MN") == "MN" else 1)
                muni_pref_edit  = st.selectbox("Preferred Method", _pref_methods, index=_pref_idx)
                me1, me2 = st.columns(2)
                muni_email_edit = me1.text_input("Email", value=_cur_muni_obj.get("email") or "")
                muni_fax_edit   = me2.text_input("Fax",   value=_cur_muni_obj.get("fax") or "")
                muni_portal_edit = st.text_input("Portal URL", value=_cur_muni_obj.get("portal_url") or "")
                muni_lead_edit  = st.number_input("Lead Time (days)", min_value=0, max_value=90,
                    value=int(_cur_muni_obj.get("lead_time_days") or 7))
                muni_notes_edit = st.text_area("Notes", value=_cur_muni_obj.get("notes") or "", height=68)
                muni_save = st.form_submit_button("💾 Save City Record", type="primary")
            if muni_save:
                try:
                    update_municipality(_cur_muni_obj["id"], {
                        "name":             muni_name_edit or None,
                        "state":            muni_state_edit,
                        "preferred_method": muni_pref_edit,
                        "email":            muni_email_edit or None,
                        "fax":              muni_fax_edit or None,
                        "portal_url":       muni_portal_edit or None,
                        "lead_time_days":   muni_lead_edit,
                        "notes":            muni_notes_edit or None,
                    })
                    st.success("City record saved.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")


# ── Right: followup log, log action, mark received, download ─────────────────

with right_col:
    followups = detail.get("followups", [])

    section_header("Followup Log")
    with st.container(border=True):
        if followups:
            for f in followups:
                action_label = f.get("action", "note").replace("_", " ").title()
                method_part  = f" via {f['method']}" if f.get("method") else ""
                who          = f.get("logged_by") or "—"
                when         = _fmt_ts(f.get("logged_at", ""))
                st.markdown(f"**{action_label}{method_part}** · {when} · _{who}_")
                if f.get("notes"):
                    st.caption(f["notes"])
                st.divider()
        else:
            st.caption("No followup entries yet.")

        with st.expander("📝 Log Action"):
            with st.form(f"wb_log_{rid}"):
                action_in    = st.selectbox("Action", _ACTIONS)
                method_in    = st.selectbox("Method (if applicable)", ["—"] + _METHODS)
                notes_log    = st.text_area("Notes", height=68)
                logged_by_in = st.text_input("Your initials / name")
                log_submit   = st.form_submit_button("Log", type="primary")

            if log_submit:
                try:
                    log_followup(
                        request_id=rid,
                        action=action_in,
                        method=method_in if method_in != "—" else "",
                        notes=notes_log,
                        logged_by=logged_by_in,
                    )
                    st.success("Logged.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Log failed: {e}")

    # Send Now (pending only)
    if detail.get("status") == "pending":
        st.markdown("")
        section_header("Send Now")
        with st.container(border=True):
            if _is_email:
                # Email path — always show Send Review popup; To field editable with muni email pre-filled
                if st.button("📤 Send Email Now", key=f"wb_send_btn_{rid}", type="primary"):
                    st.session_state[f"wb_show_send_{rid}"] = True
                if st.session_state.get(f"wb_show_send_{rid}"):
                    _subject, _body = compose_water_bill_email(detail)
                    st.markdown("**Send Review**")
                    if not _muni_email:
                        st.warning(
                            "No email on file for this municipality. "
                            "Add one in Manage Municipalities, or enter an address manually below before sending."
                        )
                    to_addr = st.text_input(
                        "To",
                        value=_muni_email,
                        key=f"wb_send_to_{rid}",
                        placeholder="municipality@city.gov",
                    )
                    st.caption(f"**Subject:** {_subject}")
                    with st.expander("Preview email body", expanded=True):
                        st.text(_body)
                    send_notes_in   = st.text_input("Notes (optional)", key=f"wb_send_notes_{rid}")
                    send_by_name_in = st.text_input("Your initials / name", key=f"wb_send_by_{rid}")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("📤 Send Email", key=f"wb_send_confirm_{rid}", type="primary"):
                            if not to_addr or "@" not in to_addr:
                                st.error("Enter a valid recipient email address in the To field.")
                            else:
                                try:
                                    send_email(to=to_addr, subject=_subject, body=_body)
                                    log_followup(
                                        request_id=rid,
                                        action="sent",
                                        method="email",
                                        notes=send_notes_in or f"Sent via Gmail to {to_addr}",
                                        logged_by=send_by_name_in,
                                    )
                                    st.session_state.pop(f"wb_show_send_{rid}", None)
                                    st.success(f"Email sent to {to_addr}.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Send failed: {e}")
                    with sc2:
                        if st.button("Never mind", key=f"wb_send_dismiss_{rid}"):
                            st.session_state.pop(f"wb_show_send_{rid}", None)
                            st.rerun()
            else:
                # Non-email method — manual log only
                if st.button("📤 Mark as Sent", key=f"wb_send_btn_{rid}", type="primary"):
                    st.session_state[f"wb_show_send_{rid}"] = True
                if st.session_state.get(f"wb_show_send_{rid}"):
                    send_notes_in   = st.text_input("Notes", value="Sent manually", key=f"wb_send_notes_{rid}")
                    send_by_name_in = st.text_input("Your initials / name", key=f"wb_send_by_{rid}")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("Confirm Send", key=f"wb_send_confirm_{rid}", type="primary"):
                            try:
                                log_followup(
                                    request_id=rid,
                                    action="sent",
                                    method=detail.get("request_method") or "",
                                    notes=send_notes_in or "Sent manually",
                                    logged_by=send_by_name_in,
                                )
                                st.session_state.pop(f"wb_show_send_{rid}", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    with sc2:
                        if st.button("Never mind", key=f"wb_send_dismiss_{rid}"):
                            st.session_state.pop(f"wb_show_send_{rid}", None)
                            st.rerun()

    # Check for Replies (email method, sent or follow_up_sent)
    if _is_email and detail.get("status") in ("sent", "follow_up_sent"):
        st.markdown("")
        section_header("Check for Replies")
        with st.container(border=True):
            st.caption("Scans inbox since last update and matches messages to requests by file number or address.")
            if st.button("🔍 Check for Replies", key=f"wb_check_replies_{rid}"):
                try:
                    messages = check_inbox(since_timestamp=detail.get("updated_at", ""))
                    results  = process_inbox_replies(messages)
                    st.session_state[f"wb_replies_{rid}"] = results
                except Exception as e:
                    st.error(f"Inbox check failed: {e}")

            results = st.session_state.get(f"wb_replies_{rid}")
            if results is not None:
                this_request_matches = [
                    m for m in results.get("matched", []) if m["request_id"] == rid
                ]
                other_matches = [
                    m for m in results.get("matched", []) if m["request_id"] != rid
                ]
                unmatched = results.get("unmatched", [])

                if this_request_matches:
                    st.caption(f"**{len(this_request_matches)} message(s) matched to this request** and logged as followup notes:")
                    for m in this_request_matches:
                        signal_label = m["signal"].replace("_", " ")
                        class_label  = m["classification"].replace("_", " ")
                        msg = m["message"]
                        st.markdown(
                            f"**{msg.get('subject') or '(no subject)'}** — {msg.get('from', '—')}  \n"
                            f"Matched on: {signal_label} · Type: {class_label}"
                            + (" 📎" if msg.get("has_attachments") else "")
                        )
                        st.caption(msg.get("date", ""))
                        if msg.get("body"):
                            with st.expander("Show message"):
                                st.text(msg["body"][:3000])
                        st.divider()
                else:
                    st.caption("No replies matched to this request.")

                if other_matches:
                    st.caption(
                        f"{len(other_matches)} message(s) matched to other request(s) and logged there: "
                        + ", ".join(
                            m.get("file_number") or m.get("property_address") or m["request_id"]
                            for m in other_matches
                        )
                    )
                if unmatched:
                    st.caption(f"{len(unmatched)} message(s) could not be matched to any request and were stored in the unmatched log.")

    # Mark Received (not applicable once received, cancelled, or completed)
    if detail.get("status") not in ("received", "cancelled", "completed"):
        st.markdown("")
        section_header("Mark Received")
        with st.container(border=True):
            bill_upload = st.file_uploader(
                "Upload Water Bill PDF",
                type=["pdf"],
                key=f"wb_bill_{rid}",
            )
            if bill_upload:
                if st.button("📥 Upload & Mark Received", key=f"wb_recv_{rid}", type="primary"):
                    try:
                        upload_bill_pdf(rid, bill_upload.read(), bill_upload.name)
                        st.success("Bill uploaded — status set to Received.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

    # Mark Completed (received only)
    if detail.get("status") == "received":
        st.markdown("")
        section_header("Mark Completed")
        with st.container(border=True):
            if st.button("✅ Mark Completed", key=f"wb_complete_btn_{rid}", type="primary"):
                st.session_state[f"wb_show_complete_{rid}"] = True
            if st.session_state.get(f"wb_show_complete_{rid}"):
                complete_notes_in = st.text_area("Notes (optional)", height=68, key=f"wb_complete_notes_{rid}")
                complete_by_in    = st.text_input("Your initials / name", key=f"wb_complete_by_{rid}")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Confirm Complete", key=f"wb_complete_confirm_{rid}", type="primary"):
                        try:
                            complete_request(rid, complete_by_in, complete_notes_in or None)
                            st.session_state.pop(f"wb_show_complete_{rid}", None)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Failed: {e}")
                with cc2:
                    if st.button("Never mind", key=f"wb_complete_dismiss_{rid}"):
                        st.session_state.pop(f"wb_show_complete_{rid}", None)
                        st.rerun()

    # Download Bill
    if detail.get("bill_pdf_path"):
        st.markdown("")
        section_header("Bill PDF")
        with st.container(border=True):
            if st.button("⬇️ Generate Download Link", key=f"wb_dl_{rid}"):
                try:
                    url = get_bill_pdf_url(detail["bill_pdf_path"])
                    st.session_state[f"wb_dl_url_{rid}"] = url
                except Exception as e:
                    st.error(f"Could not generate link: {e}")
            cached_url = st.session_state.get(f"wb_dl_url_{rid}")
            if cached_url:
                st.link_button("📄 Open Bill PDF (60-min link)", cached_url)
                st.caption("Link expires in 60 minutes.")

    # Cancel Request (visible unless already in a terminal state)
    if detail.get("status") not in ("cancelled", "completed"):
        st.markdown("")
        section_header("Cancel Request")
        with st.container(border=True):
            if st.button("🚫 Cancel Request", key=f"wb_cancel_btn_{rid}"):
                st.session_state[f"wb_show_cancel_{rid}"] = True
            if st.session_state.get(f"wb_show_cancel_{rid}"):
                cancel_reason_in = st.text_area("Reason (required)", height=68, key=f"wb_cancel_reason_{rid}")
                cancel_by_in     = st.text_input("Your initials / name", key=f"wb_cancel_by_{rid}")
                xc1, xc2 = st.columns(2)
                with xc1:
                    if st.button("Confirm Cancel", key=f"wb_cancel_confirm_{rid}", type="primary"):
                        try:
                            cancel_request(rid, cancel_reason_in, cancel_by_in)
                            st.session_state.pop(f"wb_show_cancel_{rid}", None)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Failed: {e}")
                with xc2:
                    if st.button("Never mind", key=f"wb_cancel_dismiss_{rid}"):
                        st.session_state.pop(f"wb_show_cancel_{rid}", None)
                        st.rerun()

"""
5_Water_Bills.py
══════════════════
Water Bill Requests — create and track water bill requests to municipalities.
"""

import streamlit as st
import pandas as pd
from datetime import date

from water_bills import (
    get_municipalities,
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
)
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


def _fmt_ts(ts: str) -> str:
    if not ts:
        return "—"
    return ts[:16].replace("T", " ")


# ── Session state ─────────────────────────────────────────────────────────────

if "wb_show_form" not in st.session_state:
    st.session_state.wb_show_form = False
if "wb_selected_id" not in st.session_state:
    st.session_state.wb_selected_id = None


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════

hdr_col, btn_col = st.columns([7, 1])
with hdr_col:
    st.title("💧 Water Bill Requests")
with btn_col:
    st.markdown("")
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
    muni_names = [m["name"] for m in municipalities]
    muni_map   = {m["name"]: m for m in municipalities}

    with st.expander("➕ New Water Bill Request", expanded=True):
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
            mc1, mc2 = st.columns(2)
            muni_choice = mc1.selectbox(
                "Municipality",
                options=["— enter manually —"] + muni_names,
                label_visibility="collapsed",
            )
            if muni_choice == "— enter manually —":
                muni_name_manual = mc2.text_input("Municipality Name")
                muni_id   = None
                muni_name = muni_name_manual or None
                pref_idx  = 0
            else:
                chosen   = muni_map.get(muni_choice, {})
                muni_id  = chosen.get("id")
                muni_name = muni_choice
                pref     = chosen.get("preferred_method", "email")
                pref_idx = _METHODS.index(pref) if pref in _METHODS else 0

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
# FILTERS + TABLE
# ══════════════════════════════════════════════════════════════════════════════

section_bar("All Requests")
fc1, fc2, fc3, fc4 = st.columns([3, 1.5, 1.5, 1])
status_filter = fc1.multiselect(
    "Status",
    options=_STATUSES,
    format_func=_status_label,
    default=["pending", "sent", "follow_up_sent"],
    label_visibility="collapsed",
    placeholder="Filter by status…",
)
date_from = fc2.date_input("Closing from", value=None, label_visibility="collapsed")
date_to   = fc3.date_input("Closing to",   value=None, label_visibility="collapsed")
with fc4:
    st.markdown("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

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

today = date.today()
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
    muni_names_edit = ["— none —"] + [m["name"] for m in municipalities_edit]
    muni_map_edit   = {m["name"]: m for m in municipalities_edit}

    current_muni    = detail.get("municipality_name") or ""
    muni_edit_idx   = muni_names_edit.index(current_muni) if current_muni in muni_names_edit else 0
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
        with st.form(f"wb_edit_{rid}"):
            ef1, ef2 = st.columns(2)
            fn_edit   = ef1.text_input("File Number",      value=detail.get("file_number") or "")
            addr_edit = ef2.text_input("Property Address", value=detail.get("property_address") or "")
            ow1, ow2  = st.columns(2)
            own_edit  = ow1.text_input("Current Owners",   value=detail.get("current_owners") or "")
            buy_edit  = ow2.text_input("New Buyers",       value=detail.get("new_buyers") or "")
            cd_edit   = st.date_input("Closing Date",      value=cd_val)

            mu1, mu2 = st.columns(2)
            muni_edit   = mu1.selectbox("Municipality",    muni_names_edit, index=muni_edit_idx)
            method_edit = mu2.selectbox("Request Method",  _METHODS,        index=method_edit_idx)
            status_edit = st.selectbox(
                "Status", _STATUSES, index=status_edit_idx, format_func=_status_label
            )

            sc1, sc2, sc3 = st.columns(3)
            cln_edit = sc1.text_input("Closer Name",  value=detail.get("closer_name") or "")
            cle_edit = sc2.text_input("Closer Email", value=detail.get("closer_email") or "")
            clp_edit = sc3.text_input("Closer Phone", value=detail.get("closer_phone") or "")
            sa1, sa2, sa3 = st.columns(3)
            asn_edit = sa1.text_input("Assistant Name",  value=detail.get("assistant_name") or "")
            ase_edit = sa2.text_input("Assistant Email", value=detail.get("assistant_email") or "")
            asp_edit = sa3.text_input("Assistant Phone", value=detail.get("assistant_phone") or "")

            notes_edit = st.text_area("Notes", value=detail.get("notes") or "", height=68)
            save_edit  = st.form_submit_button("💾 Save Changes", type="primary")

        if save_edit:
            chosen_edit = muni_map_edit.get(muni_edit, {})
            try:
                update_request(rid, {
                    "file_number":       fn_edit or None,
                    "property_address":  addr_edit or None,
                    "current_owners":    own_edit or None,
                    "new_buyers":        buy_edit or None,
                    "closing_date":      cd_edit.isoformat() if cd_edit else None,
                    "municipality_id":   chosen_edit.get("id"),
                    "municipality_name": muni_edit if muni_edit != "— none —" else None,
                    "request_method":    method_edit,
                    "status":            status_edit,
                    "closer_name":       cln_edit or None,
                    "closer_email":      cle_edit or None,
                    "closer_phone":      clp_edit or None,
                    "assistant_name":    asn_edit or None,
                    "assistant_email":   ase_edit or None,
                    "assistant_phone":   asp_edit or None,
                    "notes":             notes_edit or None,
                })
                st.success("Saved.")
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

    # Send Now (pending only — fast-path to 'sent' without the full Log Action form)
    if detail.get("status") == "pending":
        st.markdown("")
        section_header("Send Now")
        with st.container(border=True):
            if st.button("📤 Send Now", key=f"wb_send_btn_{rid}", type="primary"):
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

"""Personal medication list and follow-up reminders. Records only: never prescribes or advises dosing."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import config
import ui
from database import (add_medication, add_reminder, delete_medication, delete_reminder, get_patient_by_user,
                      list_medications, list_reminders, log_action, set_reminder_done)
from utils import format_date


def render(user: dict) -> None:
    ui.page_header("Medications & Reminders", "Personal reminders and follow-up dates. This is a record, not a prescription.", "💊")
    ui.disclaimer("Only your prescriber or pharmacist can advise on dosage and changes. Use this page to remember "
                  "what you have been told to take and when your follow-up is due.")
    patient = get_patient_by_user(user["id"])
    if not patient:
        st.warning("Your patient profile could not be found.")
        return
    tab_med, tab_rem = st.tabs(["💊 Medications", "🔔 Reminders & follow-ups"])
    with tab_med:
        _medications(patient, user)
    with tab_rem:
        _reminders(patient, user)


def _medications(patient: dict, user: dict) -> None:
    with st.form("med_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Medicine name", max_chars=120)
        frequency = c2.selectbox("How often (as instructed)", config.MEDICATION_FREQUENCIES)
        c3, c4 = st.columns(2)
        start = c3.date_input("Start date", value=date.today())
        ongoing = c4.checkbox("Ongoing (no end date)", value=True)
        end = c4.date_input("End date", value=date.today() + timedelta(days=30), disabled=ongoing)
        notes = st.text_area("Notes (optional)", max_chars=300, placeholder="For example: take with food, as per my doctor")
        submitted = st.form_submit_button("Add to my list")
    if submitted:
        if not name.strip():
            st.error("Please enter a medicine name.")
        elif not ongoing and end < start:
            st.error("The end date cannot be before the start date.")
        else:
            add_medication(patient["id"], name.strip(), frequency, start.isoformat(),
                           None if ongoing else end.isoformat(), notes.strip() or None)
            log_action(user["id"], "medication_added", "medication record")
            st.success("Added.")

    meds = list_medications(patient["id"])
    if not meds:
        ui.empty_state("No medications recorded yet.")
    for med in meds:
        c1, c2 = st.columns([5, 1])
        with c1:
            ended = med["end_date"] and med["end_date"] < date.today().isoformat()
            status = "Completed" if ended else "Active"
            st.markdown(f"**{med['medicine_name']}** · {med['frequency']} · {status}  \n"
                        f"<small>From {format_date(med['start_date'])}"
                        f"{' to ' + format_date(med['end_date']) if med['end_date'] else ' (ongoing)'}"
                        f"{' · ' + med['notes'] if med['notes'] else ''}</small>", unsafe_allow_html=True)
        with c2:
            st.button("Remove", key=f"delmed_{med['id']}", on_click=_remove_med, args=(med["id"], patient["id"]))


def _remove_med(med_id: int, patient_id: int) -> None:
    if delete_medication(med_id, patient_id):
        st.toast("Removed from your list.")


def _reminders(patient: dict, user: dict) -> None:
    with st.form("rem_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        rtype = c1.selectbox("Type", config.REMINDER_TYPES)
        title = c2.text_input("Title", max_chars=120, placeholder="e.g. Follow-up for blood test review")
        c3, c4 = st.columns(2)
        rdate = c3.date_input("Date", value=date.today() + timedelta(days=7), min_value=date.today())
        rtime = c4.time_input("Time (optional)", value=None)
        c5, c6 = st.columns(2)
        doctor = c5.text_input("Doctor (optional)", max_chars=120)
        reason = c6.text_input("Reason (optional)", max_chars=160)
        notes = st.text_area("Notes (optional)", max_chars=300)
        submitted = st.form_submit_button("Add reminder")
    if submitted:
        if not title.strip():
            st.error("Please add a title for the reminder.")
        else:
            add_reminder(patient["id"], rtype, title.strip(), rdate.isoformat(),
                         rtime.strftime("%H:%M") if rtime else None, doctor.strip() or None,
                         reason.strip() or None, notes.strip() or None)
            log_action(user["id"], "reminder_added", rtype)
            st.success("Reminder added.")

    reminders = list_reminders(patient["id"])
    today = date.today().isoformat()
    upcoming = [r for r in reminders if r["remind_date"] >= today and not r["is_done"]]
    done_or_past = [r for r in reminders if r not in upcoming]
    st.markdown("#### Upcoming")
    if not upcoming:
        ui.empty_state("No upcoming reminders.")
    for rem in upcoming:
        days = (date.fromisoformat(rem["remind_date"]) - date.today()).days
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            st.markdown(f"**{rem['title']}** · {rem['reminder_type']} · {format_date(rem['remind_date'])}"
                        f"{' at ' + rem['remind_time'] if rem['remind_time'] else ''} "
                        f"<span class='hx-badge'>in {days} day(s)</span>  \n"
                        f"<small>{'Doctor: ' + rem['doctor_name'] + ' · ' if rem['doctor_name'] else ''}"
                        f"{rem['reason'] or ''}</small>", unsafe_allow_html=True)
        with c2:
            st.button("Done", key=f"rdone_{rem['id']}", on_click=_mark_done, args=(rem["id"], patient["id"]))
        with c3:
            st.button("Delete", key=f"rdel_{rem['id']}", on_click=_delete_rem, args=(rem["id"], patient["id"]))
    if done_or_past:
        with st.expander(f"Completed or past ({len(done_or_past)})"):
            for rem in done_or_past:
                st.write(f"{format_date(rem['remind_date'])} · {rem['title']} "
                         f"{'✔ done' if rem['is_done'] else '(past)'}")


def _mark_done(rem_id: int, patient_id: int) -> None:
    set_reminder_done(rem_id, patient_id, True)
    st.toast("Marked as done.")


def _delete_rem(rem_id: int, patient_id: int) -> None:
    if delete_reminder(rem_id, patient_id):
        st.toast("Reminder deleted.")

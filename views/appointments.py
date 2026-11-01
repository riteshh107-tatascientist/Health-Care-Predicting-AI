"""Appointments for each role.

Patients: book only free slots (live availability), view and cancel their own bookings.
Doctors: see only their own patients' appointments, update status and clinical notes.
Staff / admin: appointment desk with confirm, complete, cancel and reschedule actions.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import streamlit as st

import config
import ui
from database import (booked_times, cancel_patient_appointment, create_appointment, get_doctor_by_user,
                      get_patient_by_user, list_departments, list_desk_appointments, list_doctor_appointments,
                      list_doctors, list_patient_appointments, reschedule_appointment,
                      set_appointment_status, update_doctor_appointment)
from utils import age_from_dob, format_date

LOG = logging.getLogger("healthcarex.appointments")


def render(user: dict) -> None:
    role = user["role"]
    if role == "patient":
        _patient_view(user)
    elif role == "doctor":
        _doctor_view(user)
    else:
        _desk_view(user)


# ---- Patient --------------------------------------------------------------
def _patient_view(user: dict) -> None:
    ui.page_header("Appointments", "Book a free time slot and keep track of your visits.", "📅")
    patient = get_patient_by_user(user["id"])
    if not patient:
        st.warning("Your patient profile could not be found. Please contact the front desk.")
        return
    tab_book, tab_mine = st.tabs(["➕ Book an appointment", "🗂️ My appointments"])
    with tab_book:
        _booking(patient, user)
    with tab_mine:
        _my_appointments(patient, user)


def _booking(patient: dict, user: dict) -> None:
    prefill = st.session_state.pop("booking_prefill", None) or {}
    departments = list_departments()
    dept_map = {d["name"]: d["id"] for d in departments}
    dept_names = list(dept_map)
    dept_index = next((i for i, n in enumerate(dept_names) if dept_map[n] == prefill.get("department_id")), 0)
    dept_name = st.selectbox("Department", dept_names, index=dept_index, key="book_dept")
    dept_id = dept_map[dept_name]

    doctors = list_doctors(dept_id)
    if not doctors:
        ui.empty_state("No doctors are listed in this department yet. Please choose another department.")
        return
    doc_labels = {f"{d['name']} · {d['specialization']} · {config.CURRENCY}{d['consultation_fee']:,.0f}": d
                  for d in doctors}
    labels = list(doc_labels)
    doc_index = next((i for i, d in enumerate(doctors) if d["id"] == prefill.get("doctor_id")), 0)
    doctor = doc_labels[st.selectbox("Doctor", labels, index=doc_index, key=f"book_doc_{dept_id}")]

    today = date.today()
    appt_date = st.date_input("Preferred date", value=today + timedelta(days=1), min_value=today,
                              max_value=today + timedelta(days=config.MAX_BOOKING_DAYS_AHEAD), key="book_date")
    taken = booked_times(doctor["id"], appt_date.isoformat())
    free = [s for s in config.time_slots() if s not in taken]
    if appt_date.weekday() == 6:
        st.info("The clinic is closed on Sundays. Please choose another date.")
    elif not free:
        st.warning("All slots are booked on this date. Please choose another date.")
    else:
        st.caption(f"{len(free)} of {len(config.time_slots())} slots are free for this doctor on this date.")
        slot = st.selectbox("Available time slot", free, key="book_time")
        reason = st.text_area("Reason for visit", max_chars=500, placeholder="Describe your symptoms or purpose of visit")
        if st.button("Confirm appointment", type="primary"):
            if not reason.strip():
                st.error("Please describe the reason for your visit.")
            else:
                try:
                    appt_id = create_appointment(patient["id"], doctor["id"], dept_id,
                                                 appt_date.isoformat(), slot, reason.strip())
                    from database import log_action
                    log_action(user["id"], "appointment_booked", f"appointment {appt_id}")
                    st.success(f"Appointment confirmed with {doctor['name']} on {appt_date:%d %b %Y} at {slot}.")
                    st.balloons()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    LOG.exception("Booking failed")
                    st.error("We could not book this appointment. Please try again.")


def _my_appointments(patient: dict, user: dict) -> None:
    rows = list_patient_appointments(patient["id"])
    today = date.today().isoformat()
    upcoming = [r for r in rows if r["appt_date"] >= today and r["status"] in config.ACTIVE_STATUSES]
    past = [r for r in rows if r not in upcoming]
    st.markdown("#### Upcoming")
    if not upcoming:
        ui.empty_state("You have no upcoming appointments.")
    for appt in sorted(upcoming, key=lambda r: (r["appt_date"], r["appt_time"])):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f"**{format_date(appt['appt_date'])} at {appt['appt_time']}** · {appt['doctor_name']} "
                f"· {appt['department'] or ''} {ui.status_badge(appt['status'])}  \n"
                f"<small>{appt['reason'] or ''}</small>", unsafe_allow_html=True)
        with c2:
            st.button("Cancel", key=f"cancel_{appt['id']}", on_click=_cancel, args=(appt["id"], patient["id"], user["id"]))
    st.markdown("#### History")
    if not past:
        ui.empty_state("No past appointments yet.")
    for appt in past:
        st.markdown(
            f"{format_date(appt['appt_date'])} · {appt['doctor_name']} · {appt['department'] or ''} "
            f"{ui.status_badge(appt['status'])}", unsafe_allow_html=True)
        if appt["doctor_notes"] and appt["status"] == "completed":
            st.caption(f"Doctor's note: {appt['doctor_notes']}")


def _cancel(appt_id: int, patient_id: int, user_id: int) -> None:
    from database import log_action
    if cancel_patient_appointment(appt_id, patient_id):
        log_action(user_id, "appointment_cancelled", f"appointment {appt_id}")
        st.toast("Appointment cancelled.")
    else:
        st.toast("That appointment can no longer be cancelled.")


# ---- Doctor ---------------------------------------------------------------
def _doctor_view(user: dict) -> None:
    ui.page_header("My Patients & Schedule", "Only appointments assigned to you are shown. Patient records stay private.", "🗓️")
    doctor = get_doctor_by_user(user["id"])
    if not doctor:
        st.warning("No doctor profile is linked to this account.")
        return
    rows = list_doctor_appointments(doctor["id"])
    today = date.today().isoformat()
    tabs = st.tabs([f"Today ({sum(r['appt_date'] == today for r in rows)})",
                    f"Upcoming ({sum(r['appt_date'] > today for r in rows)})",
                    f"Past ({sum(r['appt_date'] < today for r in rows)})"])
    groups = [
        [r for r in rows if r["appt_date"] == today],
        [r for r in rows if r["appt_date"] > today],
        [r for r in rows if r["appt_date"] < today],
    ]
    for tab, group in zip(tabs, groups):
        with tab:
            if not group:
                ui.empty_state("Nothing to show here.")
            for appt in sorted(group, key=lambda r: (r["appt_date"], r["appt_time"])):
                age = age_from_dob(appt["date_of_birth"])
                header = (f"{appt['appt_time']} · {appt['patient_name']} "
                          f"({'—' if age is None else str(age) + ' yrs'}, {appt['gender'] or 'not stated'})")
                with st.expander(header):
                    st.markdown(f"**Reason:** {appt['reason'] or 'Not given'}  \n"
                                f"**Current status:** {ui.status_badge(appt['status'])}", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    status = c1.selectbox("Update status", config.APPOINTMENT_STATUSES,
                                          index=config.APPOINTMENT_STATUSES.index(appt["status"]),
                                          key=f"dstat_{appt['id']}")
                    notes = c2.text_area("Clinical note (visible to patient after completion)",
                                         value=appt["doctor_notes"] or "", key=f"dnote_{appt['id']}", height=100)
                    if st.button("Save", key=f"dsave_{appt['id']}"):
                        ok = update_doctor_appointment(appt["id"], doctor["id"], status, notes.strip() or None)
                        if ok:
                            st.success("Saved.")
                            st.rerun()
                        else:
                            st.error("This appointment could not be updated.")


# ---- Staff / admin desk ---------------------------------------------------
def _desk_view(user: dict) -> None:
    ui.page_header("Appointment Desk", "Confirm, complete, cancel or reschedule appointments across the clinic.", "🗓️")
    c1, c2, c3 = st.columns(3)
    status = c1.selectbox("Status", ["All"] + list(config.APPOINTMENT_STATUSES), key="desk_status")
    date_from = c2.date_input("From", value=date.today() - timedelta(days=14), key="desk_from")
    date_to = c3.date_input("To", value=date.today() + timedelta(days=30), key="desk_to")
    rows = list_desk_appointments(None if status == "All" else status, date_from.isoformat(), date_to.isoformat())
    st.caption(f"{len(rows)} appointment(s) in range")
    if not rows:
        ui.empty_state("No appointments match these filters.")
        return
    st.dataframe([{"Date": r["appt_date"], "Time": r["appt_time"], "Patient": r["patient_name"],
                   "Doctor": r["doctor_name"], "Department": r["department"], "Status": r["status"]} for r in rows],
                 hide_index=True)
    st.markdown("#### Actions")
    for r in rows:
        if r["status"] not in config.ACTIVE_STATUSES:
            continue
        with st.expander(f"{r['appt_date']} {r['appt_time']} · {r['patient_name']} → {r['doctor_name']}"):
            c1, c2, c3 = st.columns(3)
            c1.button("Confirm", key=f"conf_{r['id']}", on_click=_set_status, args=(r["id"], "confirmed", user["id"]))
            c2.button("Mark completed", key=f"done_{r['id']}", on_click=_set_status, args=(r["id"], "completed", user["id"]))
            c3.button("Cancel", key=f"canc_{r['id']}", on_click=_set_status, args=(r["id"], "cancelled", user["id"]))
            new_date = st.date_input("Reschedule to", value=date.fromisoformat(r["appt_date"]),
                                     min_value=min(date.today(), date.fromisoformat(r["appt_date"])),
                                     key=f"rs_date_{r['id']}")
            free = [s for s in config.time_slots() if s not in booked_times(r["doctor_id"], new_date.isoformat(), r["id"])]
            if free:
                new_time = st.selectbox("New time", free, key=f"rs_time_{r['id']}")
                if st.button("Save new time", key=f"rs_save_{r['id']}"):
                    try:
                        reschedule_appointment(r["id"], new_date.isoformat(), new_time)
                        st.success("Rescheduled.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                st.caption("No free slots on that date for this doctor.")


def _set_status(appt_id: int, status: str, user_id: int) -> None:
    from database import log_action
    set_appointment_status(appt_id, status)
    log_action(user_id, "appointment_status", f"appointment {appt_id} -> {status}")
    st.toast(f"Appointment marked {status}.")

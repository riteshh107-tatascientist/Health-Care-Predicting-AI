"""Patient health dashboard. Charts use only data the patient has recorded; no invented values."""
from __future__ import annotations

from collections import Counter
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
import ui
from database import (add_measurement, get_patient_by_user, list_patient_appointments,
                      list_measurements, list_medications, list_records, list_reminders, log_action)
from utils import age_from_dob, format_date


def render(user: dict) -> None:
    ui.page_header("My Health Dashboard", "A summary of your appointments, records, reminders and measurements.", "📈")
    patient = get_patient_by_user(user["id"])
    if not patient:
        st.warning("Your patient profile could not be found.")
        return
    pid = patient["id"]
    appts = list_patient_appointments(pid)
    records = list_records(pid)
    meds = list_medications(pid)
    reminders = list_reminders(pid)
    today = date.today().isoformat()
    upcoming_appts = [a for a in appts if a["appt_date"] >= today and a["status"] in config.ACTIVE_STATUSES]
    open_reminders = [r for r in reminders if not r["is_done"] and r["remind_date"] >= today]
    active_meds = [m for m in meds if not m["end_date"] or m["end_date"] >= today]

    age = age_from_dob(patient["date_of_birth"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Upcoming appointments", len(upcoming_appts))
    c2.metric("Medical documents", len(records))
    c3.metric("Active medications", len(active_meds))
    c4.metric("Open reminders", len(open_reminders))
    st.caption(f"Age {age if age is not None else '—'} · Blood group {patient['blood_group'] or 'not set'} · "
               f"Allergies: {patient['allergies'] or 'none recorded'}")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### 📅 Next appointments")
        if not upcoming_appts:
            ui.empty_state("No upcoming appointments. Book one from the Appointments page.")
        for a in sorted(upcoming_appts, key=lambda x: (x["appt_date"], x["appt_time"]))[:4]:
            ui.show_card(f"{format_date(a['appt_date'])} · {a['appt_time']}",
                         f"{a['doctor_name']} · {a['department'] or ''}", footer=a["status"].title(), icon="🗓️")
    with right:
        st.markdown("#### 🔔 Follow-up timeline")
        if not reminders:
            ui.empty_state("No reminders yet.")
        else:
            tl = pd.DataFrame([{"Date": r["remind_date"], "Reminder": r["title"],
                                "Type": r["reminder_type"], "Done": "Yes" if r["is_done"] else "No"}
                               for r in reminders])
            fig = px.scatter(tl, x="Date", y="Type", color="Done", hover_name="Reminder",
                             color_discrete_map={"Yes": "#0f9b8e", "No": "#0b3d6e"})
            fig.update_traces(marker=dict(size=14))
            fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
            st.plotly_chart(fig)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📊 Appointment history by status")
        if not appts:
            ui.empty_state("No appointment history yet.")
        else:
            counts = Counter(a["status"] for a in appts)
            fig = px.bar(x=list(counts.keys()), y=list(counts.values()),
                         labels={"x": "Status", "y": "Appointments"}, color=list(counts.keys()),
                         color_discrete_sequence=["#0f9b8e", "#0b3d6e", "#7c3aed", "#b42318"])
            fig.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig)
    with c2:
        st.markdown("#### 🗂️ Medical documents by category")
        if not records:
            ui.empty_state("No documents uploaded yet.")
        else:
            counts = Counter(r["category"] for r in records)
            fig = go.Figure(go.Pie(labels=list(counts.keys()), values=list(counts.values()), hole=0.55,
                                   marker=dict(colors=["#0b3d6e", "#0f9b8e", "#14b8a6", "#38bdf8", "#7dd3fc", "#94a3b8", "#cbd5e1"])))
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig)

    st.markdown("#### ❤️ Health measurements you have recorded")
    _measurements(pid, user)


def _measurements(pid: int, user: dict) -> None:
    with st.form("measure_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        mdate = c1.date_input("Date", value=date.today(), max_value=date.today())
        weight = c2.number_input("Weight (kg)", min_value=0.0, max_value=400.0, value=0.0, step=0.1)
        systolic = c3.number_input("Systolic BP", min_value=0, max_value=260, value=0)
        diastolic = c4.number_input("Diastolic BP", min_value=0, max_value=200, value=0)
        glucose = c5.number_input("Glucose (mg/dL)", min_value=0.0, max_value=600.0, value=0.0, step=1.0)
        submitted = st.form_submit_button("Save measurement")
    if submitted:
        if not any([weight, systolic, diastolic, glucose]):
            st.error("Enter at least one measurement.")
        else:
            add_measurement(pid, mdate.isoformat(), weight or None, systolic or None,
                            diastolic or None, glucose or None)
            log_action(user["id"], "measurement_added", "health measurement")
            st.success("Measurement saved.")

    rows = list_measurements(pid)
    if not rows:
        ui.empty_state("Record a measurement to see trends here. Charts only appear for values you enter.")
        return
    df = pd.DataFrame(rows)
    df["measured_on"] = pd.to_datetime(df["measured_on"])
    if df["weight_kg"].notna().any():
        st.plotly_chart(px.line(df.dropna(subset=["weight_kg"]), x="measured_on", y="weight_kg",
                                markers=True, title="Weight (kg)").update_layout(height=260))
    if df["systolic_bp"].notna().any():
        fig = go.Figure()
        sub = df.dropna(subset=["systolic_bp"])
        fig.add_trace(go.Scatter(x=sub["measured_on"], y=sub["systolic_bp"], mode="lines+markers", name="Systolic"))
        sub2 = df.dropna(subset=["diastolic_bp"])
        fig.add_trace(go.Scatter(x=sub2["measured_on"], y=sub2["diastolic_bp"], mode="lines+markers", name="Diastolic"))
        fig.update_layout(title="Blood pressure (mmHg)", height=260)
        st.plotly_chart(fig)
    if df["glucose_mg_dl"].notna().any():
        st.plotly_chart(px.line(df.dropna(subset=["glucose_mg_dl"]), x="measured_on", y="glucose_mg_dl",
                                markers=True, title="Glucose (mg/dL)").update_layout(height=260))

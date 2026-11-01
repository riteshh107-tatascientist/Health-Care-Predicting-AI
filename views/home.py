"""Landing page: hero, owner leadership, services, journey, tools, departments, safety."""
from __future__ import annotations

import streamlit as st

import config
import ui
from datetime import date

from database import (get_patient_by_user, list_departments, list_patient_appointments,
                      list_reminders, totals)
from navigation import go_to

STEPS = [
    ("Create your profile", "Add basic health information you choose to share, plus an emergency contact."),
    ("Find the right care", "Browse departments, doctors and services, filtered by specialty and fee."),
    ("Book and manage", "Pick a free time slot, then reschedule or cancel from one place."),
    ("Keep records together", "Store reports and prescriptions privately, with validation on every upload."),
    ("Follow through", "Track medications, follow-up reminders and your health measurements over time."),
]

TOOLS = [
    ("🧪 Report Analyzer", "Reads lab values from a PDF or pasted text and compares them with reference ranges.",
     "Educational assistance only"),
    ("🧭 Symptom Guidance", "Suggests a relevant department and flags red-flag symptoms that need urgent care.",
     "Decision-support, never a diagnosis"),
    ("📊 Risk Assessment", "A diabetes-risk model trained on the real Pima Indians Diabetes dataset.",
     "Educational ML estimate, not a clinical diagnosis"),
]


def _next_step(user: dict) -> None:
    """Patient-only card built from the patient's own data: next visit and nearest reminder."""
    patient = get_patient_by_user(user["id"])
    if not patient:
        return
    today = date.today().isoformat()
    upcoming = sorted(
        (a for a in list_patient_appointments(patient["id"])
         if a["status"] in ("scheduled", "confirmed") and a["appt_date"] >= today),
        key=lambda a: (a["appt_date"], a["appt_time"]),
    )
    reminders = sorted(
        (r for r in list_reminders(patient["id"]) if not r.get("is_done") and r["remind_date"] >= today),
        key=lambda r: (r["remind_date"], r["remind_time"] or ""),
    )
    visit = (f"<div class='big'>{upcoming[0]['appt_date']} at {upcoming[0]['appt_time']}</div>"
             f"<div>with {upcoming[0]['doctor_name']} · {upcoming[0]['department'] or 'General'}</div>"
             if upcoming else "<div class='big'>No visit booked</div><div>Find a doctor to book a free slot.</div>")
    nxt = (f"<div class='big'>{reminders[0]['remind_date']}</div><div>{reminders[0]['title']}</div>"
           if reminders else "<div class='big'>Nothing due</div><div>Your reminders will appear here.</div>")
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="hx-card hx-next"><h4>📅 Your next visit</h4>{visit}</div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="hx-card hx-next"><h4>🔔 Next reminder</h4>{nxt}</div>', unsafe_allow_html=True)


def render(user: dict) -> None:
    if st.session_state.pop("welcome_pending", False):
        ui.welcome_ribbon(user["name"])
        st.balloons()

    ui.hero(user=user)
    role = user["role"]
    if role == "patient":
        _next_step(user)

    if role == "patient":
        c1, c2, c3 = st.columns(3)
        c1.button("🩺 Find doctors & services", on_click=go_to, args=("services", role))
        c2.button("📅 Book an appointment", on_click=go_to, args=("appointments", role))
        c3.button("🧭 Check symptom guidance", on_click=go_to, args=("guidance", role))

    stats = totals()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Departments", stats.get("departments", 0))
    k2.metric("Doctors on the platform", stats.get("doctors", 0))
    k3.metric("Appointments tracked", stats.get("appointments", 0))
    k4.metric("Medical documents stored", stats.get("records", 0))
    if config.DEMO_ENABLED:
        ui.demo_badge()

    st.markdown("### ✚ Healthcare services")
    cols = st.columns(3)
    services = [
        ("Find doctors", "Search clinicians by department, specialty and consultation fee."),
        ("Book appointments", "See only genuinely free time slots, and get double-booking protection."),
        ("Medical records", "Upload PDFs and images privately. Only you can open or delete them."),
    ]
    for col, (title, body) in zip(cols, services):
        col.markdown(ui.card(title, body, icon="✚"), unsafe_allow_html=True)

    st.markdown("### Why HealthCareX?")
    cols = st.columns(3)
    reasons = [
        ("Patient-first design", "Plain language, clear next steps and accessible, readable layouts."),
        ("Privacy by default", "Records are isolated per patient, files are checked by content and renamed on disk."),
        ("Honest analytics", "Models are evaluated with cross-validation, baselines and held-out test sets."),
    ]
    for col, (title, body) in zip(cols, reasons):
        col.markdown(ui.card(title, body, icon="★"), unsafe_allow_html=True)

    st.markdown("### Patient journey")
    cols = st.columns(len(STEPS))
    for idx, (col, (title, body)) in enumerate(zip(cols, STEPS), start=1):
        col.markdown(
            f'<div class="hx-card"><div class="hx-step"><div class="hx-step-num">{idx}</div>'
            f'<div><h4>{title}</h4><p>{body}</p></div></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### AI-assisted healthcare tools")
    st.caption("Decision-support and educational assistance only. These tools do not diagnose disease.")
    cols = st.columns(3)
    for col, (title, body, note) in zip(cols, TOOLS):
        col.markdown(ui.card(title, body, footer=note), unsafe_allow_html=True)

    st.markdown("### Our departments")
    departments = list_departments()
    cols = st.columns(3)
    for idx, dept in enumerate(departments):
        cols[idx % 3].markdown(ui.card(dept["name"], dept["description"] or "Specialist care"),
                               unsafe_allow_html=True)

    st.markdown("### Patient support features")
    cols = st.columns(4)
    support = [("👥 Secure profiles", "Only what you choose to share."),
               ("💊 Medication reminders", "Personal reminders, not prescriptions."),
               ("📈 Health dashboard", "Trends from the data you record."),
               ("💬 Feedback desk", "Complaints and queries tracked to resolution.")]
    for col, (title, body) in zip(cols, support):
        col.markdown(ui.card(title, body), unsafe_allow_html=True)

    st.markdown("### Safety & privacy")
    cols = st.columns(3)
    safety = [
        ("Medical safety", "Every AI output carries a disclaimer and encourages professional review."),
        ("Account security", "bcrypt password hashing, lockout after repeated failures and idle timeout."),
        ("Audit trail", "Key actions are logged without passwords or document contents."),
    ]
    for col, (title, body) in zip(cols, safety):
        col.markdown(ui.card(title, body), unsafe_allow_html=True)

    st.markdown("### Leadership")
    ui.leadership_section()

    st.markdown("### Contact & support")
    st.markdown(
        '<div class="hx-note">Use <b>Feedback &amp; Support</b> in the sidebar for service, technical or general '
        'queries. For a medical emergency, use the <b>Emergency</b> page and your local emergency number.</div>',
        unsafe_allow_html=True,
    )

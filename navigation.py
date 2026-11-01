"""Role-based navigation. Single source of truth for sidebar labels and routing keys."""
from __future__ import annotations

PAGE_LABELS = {
    "home": "🏠 Home",
    "services": "🩺 Doctors & Services",
    "appointments": "📅 Appointments",
    "records": "📁 Medical Records",
    "analyzer": "🧪 Report Analyzer",
    "guidance": "🧭 Symptom Guidance",
    "risk": "📊 Risk Assessment",
    "medications": "💊 Medications & Reminders",
    "dashboard": "📈 Health Dashboard",
    "profile": "👤 My Profile",
    "admin": "🛠️ Admin Console",
    "feedback": "💬 Feedback & Support",
    "emergency": "🚨 Emergency",
}

ROLE_OVERRIDES = {
    ("appointments", "doctor"): "🗓️ My Patients & Schedule",
    ("appointments", "staff"): "🗓️ Appointment Desk",
    ("appointments", "admin"): "🗓️ Appointment Desk",
    ("feedback", "staff"): "💬 Feedback Desk",
    ("feedback", "admin"): "💬 Feedback Desk",
}

ROLE_PAGES = {
    "patient": ["home", "services", "appointments", "records", "analyzer", "guidance", "risk",
                "medications", "dashboard", "profile", "feedback", "emergency"],
    "doctor": ["home", "appointments", "feedback", "emergency"],
    "staff": ["home", "appointments", "services", "feedback", "emergency"],
    "admin": ["home", "admin", "appointments", "feedback", "emergency"],
}


def label_for(page: str, role: str) -> str:
    return ROLE_OVERRIDES.get((page, role), PAGE_LABELS[page])


def nav_options(role: str) -> list[tuple[str, str]]:
    """List of (sidebar label, page key) allowed for the role."""
    return [(label_for(p, role), p) for p in ROLE_PAGES.get(role, [])]


def go_to(page: str, role: str, booking: dict | None = None) -> None:
    """Button callback: switch the sidebar to another page (optionally pre-filling a booking)."""
    import streamlit as st

    st.session_state["nav"] = label_for(page, role)
    if booking is not None:
        st.session_state["booking_prefill"] = booking

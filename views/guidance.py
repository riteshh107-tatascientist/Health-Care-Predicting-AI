"""Symptom guidance: educational routing to a department with red-flag screening.

Never names a disease, never prescribes medicine. Red flags always lead to emergency advice.
"""
from __future__ import annotations

import streamlit as st

import config
import ui
from database import list_departments
from navigation import go_to


def _matches(text: str) -> list[dict]:
    return [rule for rule in config.SYMPTOM_RULES if any(kw in text for kw in rule["keywords"])]


def _red_flags(text: str) -> list[str]:
    return [phrase for phrase in config.RED_FLAG_PHRASES if phrase in text]


def render(user: dict) -> None:
    ui.page_header("Symptom Guidance", "Educational routing to the right department, with urgent-warning checks.", "🧭")
    ui.disclaimer("This tool is for educational decision support and does not replace professional medical advice. "
                  "It does not diagnose conditions or recommend medicines.")
    with st.form("guidance_form"):
        selected = st.multiselect("Select the symptoms you have", config.SYMPTOM_CHOICES,
                                  placeholder="Choose one or more")
        free_text = st.text_area("Describe anything else (optional)", height=80,
                                 placeholder="For example: chest tightness when climbing stairs")
        c1, c2 = st.columns(2)
        duration = c1.selectbox("How long has this been going on?", config.DURATION_OPTIONS)
        age_group = c2.selectbox("Age group", config.AGE_GROUPS)
        submitted = st.form_submit_button("Get guidance")
    if not submitted:
        return
    if not selected and not free_text.strip():
        st.error("Please select at least one symptom or describe what you feel.")
        return

    text = " ".join([*selected, free_text]).lower()
    flags = _red_flags(text)
    matches = _matches(text)
    st.markdown("---")

    if flags or any(p in text for p in config.MENTAL_HEALTH_CRISIS_PHRASES):
        ui.emergency_banner()
        if any(p in text for p in config.MENTAL_HEALTH_CRISIS_PHRASES):
            st.markdown(
                '<div class="hx-note"><b>If you are thinking about harming yourself</b>, please contact your local '
                'emergency number now or reach out to a crisis helpline or someone you trust. You do not have to '
                'be alone with this.</div>', unsafe_allow_html=True)
        st.error("Red-flag symptoms were mentioned: " + ", ".join(flags) + ". Seek emergency care now.")
        return

    st.markdown("### Urgency guidance")
    if duration == "More than 1 week" or (duration == "4 to 7 days" and "fever" in text):
        st.warning("🟠 Book a doctor visit within the next day or two. Symptoms lasting this long deserve a review.")
    else:
        st.success("🟢 Routine: book a consultation if symptoms persist or worsen. Seek care sooner if you feel unwell.")
    if age_group in ("Child (0-12)", "Older adult (60+)") and "fever" in text:
        st.info("For young children and older adults, fever is worth a timely professional review.")

    if not matches:
        st.info("Your description did not match a specific category. A general physician can help you work out "
                "the next steps.")
        department = "General Medicine"
    else:
        st.markdown("### Possible categories")
        st.write("These are broad categories only, not diagnoses:")
        for rule in matches:
            ui.show_card(rule["category"], rule["note"], icon="🔎")
        department = matches[0]["department"]

    st.markdown(f"### Consider discussing with: **{department}**")
    dept_id_row = next((d for d in list_departments() if d["name"] == department), None)
    if user["role"] == "patient" and dept_id_row:
        st.button(f"Book with {department}", on_click=go_to, args=("appointments", user["role"],
                                                                   {"department_id": dept_id_row["id"]}))
    st.markdown(
        '<div class="hx-note"><b>Before your visit:</b> write down when symptoms started, what makes them better or '
        'worse, any medicines you already take, and any recent test results.</div>', unsafe_allow_html=True)



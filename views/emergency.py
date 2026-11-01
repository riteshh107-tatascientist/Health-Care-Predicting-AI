"""Emergency support page. Never invents emergency numbers; admin configures local information."""
from __future__ import annotations

import streamlit as st

import config
import ui
from database import get_app_setting, get_patient_by_user


def render(user: dict) -> None:
    ui.page_header("Emergency Support", "Read this first if the situation may be life-threatening.", "🚨")
    ui.emergency_banner()
    st.markdown("### What to do now")
    st.markdown(
        "1. **Call your local emergency number** or ask someone nearby to call it for you.\n"
        "2. **Go to the nearest emergency department** if you can do so safely.\n"
        "3. **Do not drive yourself** if you feel faint, have chest pain or have trouble breathing.\n"
        "4. Stay with someone you trust, and bring your medicine list and any allergy information."
    )
    st.markdown("### Hospital emergency information")
    info = get_app_setting("emergency_info")
    phone = get_app_setting("emergency_phone")
    if info or phone:
        if info:
            st.write(info)
        if phone:
            st.markdown(f"**Emergency phone (as configured by HealthCareX):** {phone}")
    else:
        st.info("Emergency details have not been configured by the administrator yet. "
                "Please use your local emergency number and the nearest emergency department.")

    if user["role"] == "patient":
        patient = get_patient_by_user(user["id"])
        if patient and (patient["emergency_contact_name"] or patient["emergency_contact_phone"]):
            st.markdown("### Your emergency contact")
            st.markdown(f"**{patient['emergency_contact_name'] or 'Contact'}** · "
                        f"{patient['emergency_contact_phone'] or 'no phone recorded'}")
        if patient and patient["allergies"]:
            st.markdown(f"**Recorded allergies:** {patient['allergies']}")
    st.markdown("### Emergency warning")
    ui.disclaimer(config.DISCLAIMER_EMERGENCY)

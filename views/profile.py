"""Patient profile: view and edit personal health information (only what is needed)."""
from __future__ import annotations

import logging
from datetime import date

import streamlit as st

import config
import ui
from database import get_patient_by_user, update_patient_profile, update_user_name, log_action
from utils import age_from_dob, clean_text, valid_phone

LOG = logging.getLogger("healthcarex.profile")


def render(user: dict) -> None:
    ui.page_header("My Profile", "Keep your health information accurate. You control what you share.", "👤")
    patient = get_patient_by_user(user["id"])
    if not patient:
        st.warning("No patient profile was found for this account.")
        return

    age = age_from_dob(patient["date_of_birth"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Age", f"{age} years" if age is not None else "—")
    c2.metric("Blood group", patient["blood_group"] or "Not set")
    c3.metric("Gender", patient["gender"] or "Not set")
    c4.metric("Account email", patient["email"])

    allergies_default = [a.strip() for a in (patient["allergies"] or "None").split(",") if a.strip()]
    allergy_options = list(dict.fromkeys(list(config.COMMON_ALLERGIES) + allergies_default))
    with st.form("profile_form"):
        name = st.text_input("Full name", value=patient["name"])
        c1, c2 = st.columns(2)
        dob_value = date.fromisoformat(patient["date_of_birth"]) if patient["date_of_birth"] else date(1995, 1, 1)
        dob = c1.date_input("Date of birth", value=dob_value, min_value=date(1900, 1, 1), max_value=date.today())
        gender_index = config.GENDERS.index(patient["gender"]) if patient["gender"] in config.GENDERS else 0
        gender = c2.selectbox("Gender", config.GENDERS, index=gender_index)
        blood_options = ["Not known", *config.BLOOD_GROUPS]
        blood_index = blood_options.index(patient["blood_group"]) if patient["blood_group"] in blood_options else 0
        blood = st.selectbox("Blood group", blood_options, index=blood_index)
        c3, c4 = st.columns(2)
        phone = c3.text_input("Mobile number", value=patient["phone"] or "")
        city = c4.text_input("City", value=patient["address"] or "")
        allergies = st.multiselect("Known allergies", allergy_options, default=allergies_default or ["None"])
        conditions = st.text_area("Existing medical conditions", value=patient["medical_conditions"] or "", height=90)
        c5, c6 = st.columns(2)
        ec_name = c5.text_input("Emergency contact name", value=patient["emergency_contact_name"] or "")
        ec_phone = c6.text_input("Emergency contact phone", value=patient["emergency_contact_phone"] or "")
        submitted = st.form_submit_button("Save profile")

    if submitted:
        name = clean_text(name, 120)
        if len(name) < 2:
            st.error("Please enter your full name.")
        elif dob > date.today():
            st.error("Date of birth cannot be in the future.")
        elif not valid_phone(phone):
            st.error("The mobile number format looks incorrect.")
        else:
            try:
                update_user_name(user["id"], name)
                update_patient_profile(user["id"], {
                    "date_of_birth": dob.isoformat(),
                    "gender": gender,
                    "blood_group": None if blood == "Not known" else blood,
                    "phone": clean_text(phone, 20) or None,
                    "address": clean_text(city, 80) or None,
                    "allergies": ", ".join(allergies) if allergies else "None",
                    "medical_conditions": clean_text(conditions, 500) or None,
                    "emergency_contact_name": clean_text(ec_name, 120) or None,
                    "emergency_contact_phone": clean_text(ec_phone, 20) or None,
                })
                log_action(user["id"], "profile_updated", "patient profile saved")
                st.session_state["auth_user"]["name"] = name
                st.success("Your profile has been saved.")
            except Exception:
                LOG.exception("Profile update failed")
                st.error("We could not save your profile. Please try again.")

    st.markdown("#### Current summary")
    st.markdown(
        f"- **Allergies:** {patient['allergies'] or 'None recorded'}\n"
        f"- **Conditions:** {patient['medical_conditions'] or 'None recorded'}\n"
        f"- **Emergency contact:** {patient['emergency_contact_name'] or 'Not set'} "
        f"({patient['emergency_contact_phone'] or 'no phone'})"
    )

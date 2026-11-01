"""Public entry: sign in, patient registration (with welcome flow) and access information."""
from __future__ import annotations

import logging
from datetime import date

import streamlit as st

import config
import ui
from auth import authenticate, login_user
from database import create_patient_account, get_user_by_id
from security import hash_password, password_problems
from utils import clean_text, valid_email, valid_phone

LOG = logging.getLogger("healthcarex.auth_pages")


def render() -> None:
    ui.hero(compact=True)
    tab_login, tab_register, tab_info = st.tabs(["🔐 Sign in", "🆕 Create patient account", "ℹ️ About HealthCareX"])
    with tab_login:
        _login_form()
    with tab_register:
        _register_form()
    with tab_info:
        _about()
    ui.footer()


def _login_form() -> None:
    with st.form("login_form"):
        email = st.text_input("Email address", autocomplete="email")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        if not email or not password:
            st.error("Please enter your email address and password.")
            return
        user, error = authenticate(email, password)
        if error:
            st.error(error)
            return
        login_user(user)
        st.session_state["login_toast"] = True
        st.rerun()


def _register_form() -> None:
    with st.form("register_form"):
        st.caption("Your account gives you appointments, a private medical-record library, reminders and health tools.")
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        email = c2.text_input("Email address", autocomplete="email")
        c3, c4 = st.columns(2)
        password = c3.text_input("Password (8+ characters, letters and numbers)", type="password",
                                 autocomplete="new-password")
        confirm = c4.text_input("Confirm password", type="password", autocomplete="new-password")
        dob = ui.dob_picker("Date of birth *", "reg_dob", date(1995, 1, 1))
        c5, c6 = st.columns(2)
        gender = c5.selectbox("Gender *", config.GENDERS,
                              help="Used only for health-plan estimates. You can change it later in My Profile.")
        blood = c6.selectbox("Blood group", ["Not known", *config.BLOOD_GROUPS],
                             help="Choose 'Not known' if you do not know it.")
        c8, c9 = st.columns(2)
        phone = c8.text_input("Mobile number (optional)")
        city = c9.text_input("City (optional)")
        allergies = st.multiselect("Known allergies", list(config.COMMON_ALLERGIES), default=["None"])
        conditions = st.text_area("Existing medical conditions (optional)", height=80,
                                  placeholder="For example: asthma, hypertension")
        c10, c11 = st.columns(2)
        ec_name = c10.text_input("Emergency contact name (optional)")
        ec_phone = c11.text_input("Emergency contact phone (optional)")
        agree = st.checkbox("I accept the terms of use and privacy notice, and I understand HealthCareX provides "
                            "educational decision support, not a diagnosis.")
        submitted = st.form_submit_button("Create my account")

    if not submitted:
        return
    name = clean_text(name, 120)
    email = (email or "").strip().lower()
    errors = []
    if len(name) < 2:
        errors.append("Please enter your full name.")
    if not valid_email(email):
        errors.append("Please enter a valid email address.")
    problems = password_problems(password or "")
    if problems:
        errors.append("Password needs: " + ", ".join(problems) + ".")
    if password != confirm:
        errors.append("The two passwords do not match.")
    if not valid_phone(phone):
        errors.append("The mobile number format looks incorrect.")
    if dob > date.today():
        errors.append("Date of birth cannot be in the future.")
    if not agree:
        errors.append("Please accept the terms to create your account.")
    if errors:
        for message in errors:
            st.error(message)
        return

    profile = {
        "date_of_birth": dob.isoformat(),
        "gender": gender,
        "blood_group": None if blood == "Not known" else blood,
        "phone": clean_text(phone, 20) or None,
        "address": clean_text(city, 80) or None,
        "allergies": ", ".join(allergies) if allergies else "None",
        "medical_conditions": clean_text(conditions, 500) or None,
        "emergency_contact_name": clean_text(ec_name, 120) or None,
        "emergency_contact_phone": clean_text(ec_phone, 20) or None,
    }
    try:
        user_id = create_patient_account(name, email, hash_password(password), profile)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        LOG.exception("Registration failed")
        st.error("Something went wrong while creating your account. Please try again.")
        return
    login_user(get_user_by_id(user_id))
    st.session_state["welcome_pending"] = True
    st.rerun()


def _about() -> None:
    st.markdown("#### About HealthCareX")
    st.write(
        "HealthCareX is a patient-support platform: find services, manage appointments, keep medical documents "
        "organised, understand lab values in plain language, and explore educational risk estimates. "
        "It does not diagnose conditions or prescribe medicines."
    )
    ui.disclaimer()
    if config.DEMO_ENABLED:
        ui.demo_badge()
        st.markdown(
            f"**Demo patient:** `patient.demo@{config.DEMO_DOMAIN}`  \n"
            f"**Demo doctors:** any address ending `@{config.DEMO_DOMAIN}` (e.g. `ananya.sharma@{config.DEMO_DOMAIN}`)  \n"
            "**Demo password for all demo accounts:** configured by the owner (`DEMO_PASSWORD`)."
        )
    st.caption("Administrator access is provisioned by the owner through environment settings and is not shown here.")

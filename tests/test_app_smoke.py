"""End-to-end smoke tests: run the real app script headlessly and walk every page for each role."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config

APP = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 60


def _login(email, password):
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.session_state["splash_done"] = True
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.text_input[0].input(email)
    at.text_input[1].input(password)
    at.button[0].click()  # first button on the sign-in tab is the form submit
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _visit_all(at, labels):
    for label in labels:
        at.sidebar.radio[0].set_value(label).run()
        assert not at.exception, f"{label}: {[e.value for e in at.exception]}"


def test_public_landing_renders_without_errors():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.session_state["splash_done"] = True
    at.run()
    assert not at.exception
    assert len(at.tabs) == 3 and "Sign in" in at.tabs[0].label


def test_wrong_password_shows_friendly_error():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.session_state["splash_done"] = True
    at.run()
    at.text_input[0].input("nobody@example.com")
    at.text_input[1].input("wrong-password")
    at.button[0].click()
    at.run()
    assert not at.exception
    assert any("Invalid email or password" in e.value for e in at.error)


def test_patient_can_visit_every_page():
    from navigation import nav_options

    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    labels = [label for label, _ in nav_options("patient")]
    _visit_all(at, labels)


def test_doctor_workspace_renders():
    from navigation import nav_options

    at = _login(f"ananya.sharma@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    _visit_all(at, [label for label, _ in nav_options("doctor")])


def test_admin_console_renders():
    from navigation import nav_options

    at = _login(config.ADMIN_EMAIL, config.ADMIN_PASSWORD)
    _visit_all(at, [label for label, _ in nav_options("admin")])


def _button(at, label):
    for b in at.button:
        if b.label == label:
            return b
    raise AssertionError(f"button '{label}' not found; have {[b.label for b in at.button]}")


def _text_area(at, fragment):
    for t in at.text_area:
        if fragment in (t.label or ""):
            return t
    raise AssertionError(f"text area containing '{fragment}' not found")


def test_registration_creates_patient_and_shows_welcome_ribbon():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.session_state["splash_done"] = True
    at.run()
    at.text_input[2].input("Asha Verma")                 # full name (register tab)
    at.text_input[3].input("asha.verma.test@example.com")
    at.text_input[4].input("Welcome1234")
    at.text_input[5].input("Welcome1234")
    at.checkbox[0].check()
    _button(at, "Create my account").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    banners = [m.value for m in at.markdown if 'class="hx-ribbon"' in m.value]
    assert banners and "Welcome to HealthCareX, Asha Verma" in banners[0]


def test_patient_books_a_free_slot():
    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    at.sidebar.radio[0].set_value("📅 Appointments").run()
    _text_area(at, "Reason for visit").input("Mild headache since yesterday").run()
    _button(at, "Confirm appointment").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Appointment confirmed" in s.value for s in at.success)


def test_analyzer_produces_results_from_pasted_text():
    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    at.sidebar.radio[0].set_value("🧪 Report Analyzer").run()
    _text_area(at, "Paste lab values").input("Hemoglobin 13.9 g/dL (12.0 - 15.5)\nFasting glucose 104 mg/dL")
    _button(at, "Analyze report").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.dataframe) >= 1
    assert any("is above the reference range" in m.value for m in at.markdown)


def test_risk_estimate_shows_educational_probability():
    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    at.sidebar.radio[0].set_value("📊 Risk Assessment").run()
    _button(at, "Estimate").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.label == "Model probability" for m in at.metric)


def test_red_flag_symptoms_trigger_emergency_warning():
    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    at.sidebar.radio[0].set_value("🧭 Symptom Guidance").run()
    _text_area(at, "Describe anything else").input("I have chest pain and difficulty breathing")
    _button(at, "Get guidance").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Emergency warning" in m.value for m in at.markdown)
    assert not any("Consider discussing with" in m.value for m in at.markdown)


def test_fever_and_cough_routes_to_general_medicine():
    at = _login(f"patient.demo@{config.DEMO_DOMAIN}", config.DEMO_PASSWORD)
    at.sidebar.radio[0].set_value("🧭 Symptom Guidance").run()
    at.multiselect[0].select("fever").select("cough")
    _button(at, "Get guidance").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Respiratory or infectious" in m.value for m in at.markdown)
    assert any("General Medicine" in m.value for m in at.markdown)

from datetime import date, timedelta

import pytest

import config
import database as dbm
from security import hash_password

PROFILE = {"date_of_birth": "1990-01-01", "gender": "Female", "blood_group": "O+", "phone": None,
           "address": "City", "allergies": "None", "medical_conditions": None,
           "emergency_contact_name": None, "emergency_contact_phone": None}


def _patient(email, name="Test Patient"):
    uid = dbm.create_patient_account(name, email, hash_password("Passw0rd!"), PROFILE)
    return uid, dbm.get_patient_by_user(uid)["id"]


def _doctor_id():
    return dbm.list_doctors()[0]["id"]


def _future(days=3):
    return (date.today() + timedelta(days=days)).isoformat()


def test_init_seeds_reference_data(db):
    assert len(dbm.list_departments()) == len(config.DEPARTMENTS)
    assert len(dbm.list_services()) == len(config.SERVICES)
    assert len(dbm.list_doctors()) == len(config.DEMO_DOCTORS)
    assert dbm.get_user_by_email(config.ADMIN_EMAIL)["role"] == "admin"


def test_init_is_idempotent(db):
    dbm.init_db()
    dbm.init_db()
    assert len(dbm.list_departments()) == len(config.DEPARTMENTS)
    assert len(dbm.list_doctors()) == len(config.DEMO_DOCTORS)


def test_duplicate_email_rejected(db):
    _patient("dup@example.com")
    with pytest.raises(ValueError):
        _patient("DUP@example.com")


def test_double_booking_same_doctor_blocked(db):
    _, p1 = _patient("a@example.com")
    _, p2 = _patient("b@example.com", "Second")
    doc = _doctor_id()
    dbm.create_appointment(p1, doc, None, _future(), "09:00", "check")
    with pytest.raises(ValueError):
        dbm.create_appointment(p2, doc, None, _future(), "09:00", "check")


def test_same_patient_cannot_double_book(db):
    _, p1 = _patient("c@example.com")
    docs = dbm.list_doctors()
    dbm.create_appointment(p1, docs[0]["id"], None, _future(), "10:00", "a")
    with pytest.raises(ValueError):
        dbm.create_appointment(p1, docs[1]["id"], None, _future(), "10:00", "b")


def test_cancelled_slot_becomes_free_again(db):
    _, p1 = _patient("d@example.com")
    _, p2 = _patient("e@example.com", "Other")
    doc = _doctor_id()
    appt = dbm.create_appointment(p1, doc, None, _future(), "11:00", "x")
    assert dbm.cancel_patient_appointment(appt, p1)
    dbm.create_appointment(p2, doc, None, _future(), "11:00", "y")


def test_past_date_and_invalid_slot_rejected(db):
    _, p1 = _patient("f@example.com")
    doc = _doctor_id()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(ValueError):
        dbm.create_appointment(p1, doc, None, yesterday, "09:00", "x")
    with pytest.raises(ValueError):
        dbm.create_appointment(p1, doc, None, _future(), "09:15", "x")


def test_patient_cannot_cancel_someone_elses_appointment(db):
    _, p1 = _patient("g@example.com")
    _, p2 = _patient("h@example.com", "Intruder")
    appt = dbm.create_appointment(p1, _doctor_id(), None, _future(), "12:00", "x")
    assert dbm.cancel_patient_appointment(appt, p2) is False
    assert dbm.get_appointment(appt)["status"] == "scheduled"


def test_doctor_cannot_update_another_doctors_appointment(db):
    _, p1 = _patient("i@example.com")
    docs = dbm.list_doctors()
    appt = dbm.create_appointment(p1, docs[0]["id"], None, _future(), "13:00", "x")
    assert dbm.update_doctor_appointment(appt, docs[1]["id"], "completed", "note") is False
    assert dbm.update_doctor_appointment(appt, docs[0]["id"], "completed", "note") is True


def test_doctor_sees_only_own_appointments(db):
    _, p1 = _patient("j@example.com")
    docs = dbm.list_doctors()
    mine = dbm.create_appointment(p1, docs[0]["id"], None, _future(), "14:00", "x")
    own_ids = {a["id"] for a in dbm.list_doctor_appointments(docs[0]["id"])}
    other_ids = {a["id"] for a in dbm.list_doctor_appointments(docs[1]["id"])}
    assert mine in own_ids
    assert mine not in other_ids


def test_reschedule_conflict_blocked(db):
    _, p1 = _patient("k@example.com")
    _, p2 = _patient("l@example.com", "Other")
    doc = _doctor_id()
    dbm.create_appointment(p1, doc, None, _future(), "09:30", "x")
    appt2 = dbm.create_appointment(p2, doc, None, _future(), "10:30", "y")
    with pytest.raises(ValueError):
        dbm.reschedule_appointment(appt2, _future(), "09:30")


def test_records_isolated_between_patients(db):
    _, p1 = _patient("m@example.com")
    _, p2 = _patient("n@example.com", "Other")
    rid = dbm.add_record(p1, "report.pdf", "stored-a.pdf", ".pdf", 10, "Lab report", None)
    assert dbm.get_record(rid, p2) is None
    assert dbm.delete_record(rid, p2) is None
    assert dbm.get_record(rid, p1) is not None
    assert dbm.delete_record(rid, p1) == "stored-a.pdf"


def test_feedback_status_validation(db):
    uid, _ = _patient("o@example.com")
    fid = dbm.add_feedback(uid, "General feedback", "Helpful service today")
    dbm.update_feedback(fid, "resolved", "Thanks")
    assert dbm.list_all_feedback("resolved")[0]["response"] == "Thanks"
    with pytest.raises(ValueError):
        dbm.update_feedback(fid, "bogus", None)


def test_settings_round_trip(db):
    dbm.set_app_setting("emergency_phone", "000-TEST")
    dbm.set_app_setting("emergency_phone", "111-TEST")
    assert dbm.get_app_setting("emergency_phone") == "111-TEST"
    assert dbm.get_app_setting("missing", "fallback") == "fallback"


def test_demo_data_seeded_and_labelled(db):
    demo = dbm.get_user_by_email(f"patient.demo@{config.DEMO_DOMAIN}")
    assert demo and demo["role"] == "patient"
    assert any(d["is_demo"] for d in dbm.list_doctors())
    assert dbm.totals()["appointments"] >= 4

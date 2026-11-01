import json
from datetime import date

import database as db


def _patient_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "hp.db"))
    db.init_db()
    row = db.query_one("SELECT id FROM patients LIMIT 1")
    assert row, "a patient profile must exist to test the health plan"
    return row["id"]


def test_save_and_update_health_plan(tmp_path, monkeypatch):
    pid = _patient_id(tmp_path, monkeypatch)
    inputs = {"sex": "Female", "age": 30, "height_cm": 160, "weight_kg": 55, "activity_label": "x",
              "goal": "Maintain my weight", "diet": "Vegetarian", "budget": "Lower-income family"}
    db.save_health_plan(pid, inputs, "Lower-income family", "Vegetarian")
    db.save_health_plan(pid, {**inputs, "weight_kg": 58}, "Middle-income family", "Vegetarian")
    plan = db.get_health_plan(pid)
    assert json.loads(plan["inputs_json"])["weight_kg"] == 58
    assert plan["budget_tier"] == "Middle-income family"
    assert db.query_one("SELECT COUNT(*) AS n FROM health_plans WHERE patient_id = ?", (pid,))["n"] == 1


def test_daily_log_upsert_and_recent(tmp_path, monkeypatch):
    pid = _patient_id(tmp_path, monkeypatch)
    today = date.today().isoformat()
    db.save_daily_log(pid, today, 4, 10, ["breakfast"])
    db.save_daily_log(pid, today, 9, 30, ["breakfast", "lunch"])
    log = db.get_daily_log(pid, today)
    assert log["water_glasses"] == 9 and log["walk_minutes"] == 30 and log["meals_done"] == "breakfast,lunch"
    assert len(db.recent_daily_logs(pid, 7)) == 1


def test_admin_user_rows_filter_and_tier_counts(tmp_path, monkeypatch):
    pid = _patient_id(tmp_path, monkeypatch)
    db.save_health_plan(pid, {"age": 30}, "High-income family", "Non-vegetarian")
    rows = db.admin_user_rows()
    assert any(r["budget_tier"] == "High-income family" for r in rows)
    assert all(r["role"] == "patient" for r in db.admin_user_rows(role="patient"))
    assert db.admin_user_rows(search="no-such-person-xyz") == []
    assert {c["budget_tier"] for c in db.plan_tier_counts()} == {"High-income family"}

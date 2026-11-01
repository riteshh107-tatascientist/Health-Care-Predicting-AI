"""Automation and v2.1 additions: booking reminder, demo staff login, owner portrait."""
import os
from datetime import date, timedelta
from pathlib import Path

import database as db


def test_booking_creates_automatic_reminder(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.db"))
    db.init_db()
    pat = db.query_one("SELECT p.id, p.user_id FROM patients p JOIN users u ON u.id=p.user_id WHERE u.role='patient' LIMIT 1")
    doc = db.query_one("SELECT id FROM doctors LIMIT 1")
    visit = date.today() + timedelta(days=5)
    before = len(db.list_reminders(pat["id"]))
    db.create_appointment(pat["id"], doc["id"], None, visit.isoformat(), "11:30", "Automation test visit")
    after = db.list_reminders(pat["id"])
    assert len(after) == before + 1
    auto = [r for r in after if r["reminder_type"] == "Appointment" and r["remind_date"] == (visit - timedelta(days=1)).isoformat()]
    assert auto, "reminder should be created the day before the visit"


def test_demo_staff_account_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "s.db"))
    db.init_db()
    staff = db.get_user_by_email(f"staff.demo@{__import__('config').DEMO_DOMAIN}")
    assert staff and staff["role"] == "staff"


def test_owner_portrait_present_and_not_distorted():
    from PIL import Image
    path = Path(__file__).resolve().parents[1] / "assets" / "owner" / "portrait.jpg"
    assert path.exists() and path.stat().st_size > 10_000
    from PIL import ImageStat
    img = Image.open(path)
    w, h = img.size
    assert w == h, "headshot crop must be square (no stretching)"
    assert sum(ImageStat.Stat(img.convert("L")).stddev) > 10, "portrait must not be blank"

"""SQLite data layer.

Every query uses bound parameters. Ownership-sensitive queries also filter by the owner's
id (patient_id / doctor_id), so one user cannot read or change another user's rows even if
they guess an identifier.
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

import config
from security import hash_password

LOG = logging.getLogger("healthcarex.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('patient','doctor','staff','admin')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    cost REAL NOT NULL DEFAULT 0,
    description TEXT,
    is_available INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth TEXT,
    gender TEXT,
    blood_group TEXT,
    phone TEXT,
    address TEXT,
    allergies TEXT,
    medical_conditions TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department_id INTEGER REFERENCES departments(id),
    specialization TEXT NOT NULL,
    qualification TEXT,
    experience_years INTEGER NOT NULL DEFAULT 0,
    consultation_fee REAL NOT NULL DEFAULT 0,
    availability TEXT NOT NULL DEFAULT 'Mon-Sat, 09:00-17:00',
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
    department_id INTEGER REFERENCES departments(id),
    appt_date TEXT NOT NULL,
    appt_time TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','confirmed','completed','cancelled')),
    doctor_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Database-level double-booking protection for active appointments.
CREATE UNIQUE INDEX IF NOT EXISTS uq_doctor_slot ON appointments(doctor_id, appt_date, appt_time)
    WHERE status IN ('scheduled','confirmed');
CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_slot ON appointments(patient_id, appt_date, appt_time)
    WHERE status IN ('scheduled','confirmed');
CREATE TABLE IF NOT EXISTS medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    file_ext TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medicine_name TEXT NOT NULL,
    frequency TEXT,
    start_date TEXT,
    end_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    reminder_type TEXT NOT NULL,
    title TEXT NOT NULL,
    remind_date TEXT NOT NULL,
    remind_time TEXT,
    doctor_name TEXT,
    reason TEXT,
    notes TEXT,
    is_done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS health_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    measured_on TEXT NOT NULL,
    weight_kg REAL,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    glucose_mg_dl REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in progress','resolved')),
    response TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS health_plans (
    patient_id INTEGER PRIMARY KEY REFERENCES patients(id) ON DELETE CASCADE,
    inputs_json TEXT NOT NULL,
    budget_tier TEXT NOT NULL,
    diet TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,
    water_glasses INTEGER NOT NULL DEFAULT 0,
    walk_minutes INTEGER NOT NULL DEFAULT 0,
    meals_done TEXT NOT NULL DEFAULT '',
    UNIQUE (patient_id, log_date)
);
"""

PATIENT_FIELDS = (
    "date_of_birth", "gender", "blood_group", "phone", "address", "allergies",
    "medical_conditions", "emergency_contact_name", "emergency_contact_phone",
)


@contextmanager
def get_conn():
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write statement and return the affected row count."""
    with get_conn() as conn:
        return conn.execute(sql, params).rowcount


# ---- Startup --------------------------------------------------------------
def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    _seed_reference_data()
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD:
        _ensure_admin()
    if config.DEMO_ENABLED:
        _seed_demo_data()
        _ensure_demo_staff()


def _ensure_demo_staff() -> None:
    """Clearly labelled demo staff login (front desk). Created once if missing."""
    email = f"staff.demo@{config.DEMO_DOMAIN}"
    if get_user_by_email(email) is None:
        create_staff_account("Demo Front Desk", email, hash_password(config.DEMO_PASSWORD))


def _seed_reference_data() -> None:
    with get_conn() as conn:
        for name, description in config.DEPARTMENTS.items():
            conn.execute("INSERT OR IGNORE INTO departments(name, description) VALUES (?, ?)", (name, description))
        existing = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
        if existing == 0:
            dept_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM departments")}
            for name, dept, cost, desc in config.SERVICES:
                conn.execute(
                    "INSERT INTO services(name, department_id, cost, description) VALUES (?,?,?,?)",
                    (name, dept_ids.get(dept), cost, desc),
                )


def _ensure_admin() -> None:
    email = config.ADMIN_EMAIL.strip().lower()
    if query_one("SELECT id FROM users WHERE email = ?", (email,)):
        return
    create_user(config.ADMIN_NAME, email, hash_password(config.ADMIN_PASSWORD), "admin")
    LOG.info("Administrator account created from environment settings.")


def _seed_demo_data() -> None:
    """Clearly labelled demo data for testing and demonstration only."""
    if query_one("SELECT id FROM users WHERE email = ?", (f"patient.demo@{config.DEMO_DOMAIN}",)):
        return
    password_hash = hash_password(config.DEMO_PASSWORD)
    dept_ids = {r["name"]: r["id"] for r in query("SELECT id, name FROM departments")}
    doctor_ids = []
    with get_conn() as conn:
        for doc in config.DEMO_DOCTORS:
            cur = conn.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES (?,?,?, 'doctor')",
                (doc["name"], doc["email"], password_hash),
            )
            cur2 = conn.execute(
                """INSERT INTO doctors(user_id, department_id, specialization, qualification,
                   experience_years, consultation_fee, is_demo) VALUES (?,?,?,?,?,?,1)""",
                (cur.lastrowid, dept_ids.get(doc["department"]), doc["specialization"],
                 doc["qualification"], doc["experience"], doc["fee"]),
            )
            doctor_ids.append((cur2.lastrowid, dept_ids.get(doc["department"])))
    patient_user = create_patient_account(
        "Demo Patient", f"patient.demo@{config.DEMO_DOMAIN}", password_hash,
        {"date_of_birth": "1988-06-14", "gender": "Female", "blood_group": "B+", "phone": "",
         "address": "Demo City", "allergies": "None", "medical_conditions": "Demo entry only",
         "emergency_contact_name": "Demo Contact", "emergency_contact_phone": ""},
    )
    patient = query_one("SELECT id FROM patients WHERE user_id = ?", (patient_user,))
    pid = patient["id"]
    today = date.today()
    with get_conn() as conn:
        rows = [
            (pid, doctor_ids[0][0], doctor_ids[0][1], (today + timedelta(days=2)).isoformat(), "09:00",
             "Demo: fever and cough for two days", "scheduled", None),
            (pid, doctor_ids[1][0], doctor_ids[1][1], (today + timedelta(days=7)).isoformat(), "11:00",
             "Demo: routine heart-risk review", "confirmed", None),
            (pid, doctor_ids[0][0], doctor_ids[0][1], (today - timedelta(days=14)).isoformat(), "10:00",
             "Demo: general check-up", "completed", "Demo note: symptoms resolved; review if they return."),
            (pid, doctor_ids[1][0], doctor_ids[1][1], (today - timedelta(days=3)).isoformat(), "14:00",
             "Demo: cancelled visit", "cancelled", None),
        ]
        conn.executemany(
            """INSERT INTO appointments(patient_id, doctor_id, department_id, appt_date, appt_time, reason,
               status, doctor_notes) VALUES (?,?,?,?,?,?,?,?)""", rows)
        conn.execute(
            """INSERT INTO medications(patient_id, medicine_name, frequency, start_date, notes)
               VALUES (?, 'Demo medicine A (sample entry)', 'Once daily', ?, 'Demo entry only')""",
            (pid, today.isoformat()),
        )
        conn.execute(
            """INSERT INTO reminders(patient_id, reminder_type, title, remind_date, remind_time, doctor_name, reason)
               VALUES (?, 'Follow-up visit', 'Demo follow-up review', ?, '09:30', 'Dr. Ananya Sharma', 'Demo follow-up')""",
            (pid, (today + timedelta(days=14)).isoformat()),
        )
        conn.executemany(
            """INSERT INTO health_measurements(patient_id, measured_on, weight_kg, systolic_bp, diastolic_bp, glucose_mg_dl)
               VALUES (?,?,?,?,?,?)""",
            [(pid, (today - timedelta(days=60 - i * 15)).isoformat(), 68 + i * 0.4, 120 + i, 78, 96 + i * 2)
             for i in range(4)],
        )
        conn.execute(
            "INSERT INTO feedback(user_id, category, message) VALUES (?, 'General feedback', 'Demo: booking was easy to follow.')",
            (patient_user,),
        )


# ---- Users and accounts ---------------------------------------------------
def get_user_by_email(email: str) -> dict | None:
    return query_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))


def get_user_by_id(user_id: int) -> dict | None:
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def create_user(name: str, email: str, password_hash: str, role: str) -> int:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES (?,?,?,?)",
                (name, email.strip().lower(), password_hash, role),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email address already exists.") from exc
        return cur.lastrowid


def create_patient_account(name: str, email: str, password_hash: str, profile: dict) -> int:
    """Create a user and its patient profile in one transaction."""
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES (?,?,?, 'patient')",
                (name, email.strip().lower(), password_hash),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email address already exists.") from exc
        user_id = cur.lastrowid
        values = [profile.get(f) or None for f in PATIENT_FIELDS]
        conn.execute(
            f"INSERT INTO patients(user_id, {', '.join(PATIENT_FIELDS)}) VALUES (?, {', '.join('?' * len(PATIENT_FIELDS))})",
            (user_id, *values),
        )
        return user_id


def create_doctor_account(name, email, password_hash, department_id, specialization,
                          qualification, experience_years, fee) -> int:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES (?,?,?, 'doctor')",
                (name, email.strip().lower(), password_hash),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email address already exists.") from exc
        conn.execute(
            """INSERT INTO doctors(user_id, department_id, specialization, qualification,
               experience_years, consultation_fee) VALUES (?,?,?,?,?,?)""",
            (cur.lastrowid, department_id, specialization, qualification, experience_years, fee),
        )
        return cur.lastrowid


def list_users() -> list[dict]:
    return query("SELECT id, name, email, role, is_active, created_at FROM users ORDER BY created_at DESC")


def set_user_active(user_id: int, active: bool) -> None:
    execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if active else 0, user_id))


def set_user_password(user_id: int, password_hash: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


def set_user_role(user_id: int, role: str) -> None:
    if role not in config.ROLES:
        raise ValueError("Unknown role.")
    execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def create_staff_account(name, email, password_hash) -> int:
    return create_user(name, email, password_hash, "staff")


def update_user_name(user_id: int, name: str) -> None:
    execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))


# ---- Patients -------------------------------------------------------------
def get_patient_by_user(user_id: int) -> dict | None:
    return query_one(
        """SELECT p.*, u.name, u.email FROM patients p JOIN users u ON u.id = p.user_id
           WHERE p.user_id = ?""", (user_id,))


def update_patient_profile(user_id: int, profile: dict) -> None:
    assignments = ", ".join(f"{f} = ?" for f in PATIENT_FIELDS)
    values = [profile.get(f) or None for f in PATIENT_FIELDS]
    execute(
        f"UPDATE patients SET {assignments}, updated_at = datetime('now') WHERE user_id = ?",
        (*values, user_id),
    )


# ---- Departments, doctors, services --------------------------------------
def list_departments() -> list[dict]:
    return query("SELECT * FROM departments ORDER BY name")


def add_department(name: str, description: str) -> None:
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO departments(name, description) VALUES (?, ?)", (name, description))
    except sqlite3.IntegrityError as exc:
        raise ValueError("That department already exists.") from exc


_DOCTOR_SELECT = """
SELECT d.id, d.user_id, u.name, u.email, d.specialization, d.qualification,
       d.experience_years, d.consultation_fee, d.availability, d.department_id,
       d.is_demo, dep.name AS department
FROM doctors d
JOIN users u ON u.id = d.user_id
LEFT JOIN departments dep ON dep.id = d.department_id
"""


def list_doctors(department_id: int | None = None, search: str | None = None, active_only: bool = True) -> list[dict]:
    sql = _DOCTOR_SELECT + " WHERE 1=1"
    params: list = []
    if active_only:
        sql += " AND u.is_active = 1"
    if department_id:
        sql += " AND d.department_id = ?"
        params.append(department_id)
    if search:
        like = f"%{search.lower()}%"
        sql += " AND (LOWER(d.specialization) LIKE ? OR LOWER(u.name) LIKE ?)"
        params += [like, like]
    sql += " ORDER BY u.name"
    return query(sql, tuple(params))


def get_doctor(doctor_id: int) -> dict | None:
    return query_one(_DOCTOR_SELECT + " WHERE d.id = ?", (doctor_id,))


def get_doctor_by_user(user_id: int) -> dict | None:
    return query_one(_DOCTOR_SELECT + " WHERE d.user_id = ?", (user_id,))


def list_services(department_id: int | None = None, search: str | None = None) -> list[dict]:
    sql = """SELECT s.*, dep.name AS department FROM services s
             LEFT JOIN departments dep ON dep.id = s.department_id WHERE s.is_available = 1"""
    params: list = []
    if department_id:
        sql += " AND s.department_id = ?"
        params.append(department_id)
    if search:
        sql += " AND LOWER(s.name) LIKE ?"
        params.append(f"%{search.lower()}%")
    return query(sql + " ORDER BY s.name", tuple(params))


def add_service(name: str, department_id: int | None, cost: float, description: str) -> None:
    execute("INSERT INTO services(name, department_id, cost, description) VALUES (?,?,?,?)",
            (name, department_id, cost, description))


# ---- Appointments ---------------------------------------------------------
def _validate_slot(appt_date: str, appt_time: str) -> None:
    try:
        day = date.fromisoformat(appt_date)
    except ValueError as exc:
        raise ValueError("Please choose a valid date.") from exc
    today = date.today()
    if day < today:
        raise ValueError("Appointments must be booked for today or a future date.")
    if day > today + timedelta(days=config.MAX_BOOKING_DAYS_AHEAD):
        raise ValueError(f"Appointments can be booked up to {config.MAX_BOOKING_DAYS_AHEAD} days ahead.")
    if appt_time not in config.time_slots():
        raise ValueError("Please choose one of the clinic time slots.")


def booked_times(doctor_id: int, appt_date: str, exclude_id: int | None = None) -> set[str]:
    rows = query(
        """SELECT appt_time FROM appointments WHERE doctor_id = ? AND appt_date = ?
           AND status IN ('scheduled','confirmed') AND id IS NOT ?""",
        (doctor_id, appt_date, exclude_id),
    )
    return {r["appt_time"] for r in rows}


_SLOT_TAKEN = "That time slot is no longer available. Please choose another time."


def create_appointment(patient_id: int, doctor_id: int, department_id: int | None,
                       appt_date: str, appt_time: str, reason: str) -> int:
    _validate_slot(appt_date, appt_time)
    with get_conn() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO appointments(patient_id, doctor_id, department_id, appt_date, appt_time, reason)
                   VALUES (?,?,?,?,?,?)""",
                (patient_id, doctor_id, department_id, appt_date, appt_time, reason),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(_SLOT_TAKEN) from exc
        appt_id = cur.lastrowid
    _auto_reminder_for_appointment(patient_id, doctor_id, appt_date, appt_time, reason)
    return appt_id


def _auto_reminder_for_appointment(patient_id: int, doctor_id: int, appt_date: str, appt_time: str,
                                   reason: str) -> None:
    """Automation: create a reminder the day before a booked visit (today, if the visit is tomorrow)."""
    doc = query_one("SELECT u.name FROM doctors d JOIN users u ON u.id = d.user_id WHERE d.id = ?", (doctor_id,))
    doctor_name = doc["name"] if doc else "your doctor"
    visit_day = date.fromisoformat(appt_date)
    remind_on = max(visit_day - timedelta(days=1), date.today())
    add_reminder(patient_id, "Appointment", f"Visit with {doctor_name}", remind_on.isoformat(), appt_time,
                 doctor_name, reason, "Created automatically when you booked this visit.")


_PATIENT_APPT_SELECT = """
SELECT a.id, a.appt_date, a.appt_time, a.status, a.reason, a.doctor_notes, a.doctor_id,
       u.name AS doctor_name, dep.name AS department
FROM appointments a
JOIN doctors d ON d.id = a.doctor_id
JOIN users u ON u.id = d.user_id
LEFT JOIN departments dep ON dep.id = a.department_id
"""


def list_patient_appointments(patient_id: int) -> list[dict]:
    return query(_PATIENT_APPT_SELECT + " WHERE a.patient_id = ? ORDER BY a.appt_date DESC, a.appt_time DESC",
                 (patient_id,))


def cancel_patient_appointment(appointment_id: int, patient_id: int) -> bool:
    return execute(
        """UPDATE appointments SET status = 'cancelled', updated_at = datetime('now')
           WHERE id = ? AND patient_id = ? AND status IN ('scheduled','confirmed')""",
        (appointment_id, patient_id),
    ) > 0


def list_doctor_appointments(doctor_id: int) -> list[dict]:
    """Only appointments assigned to this doctor. Patient identity fields only, no records."""
    return query(
        """SELECT a.id, a.appt_date, a.appt_time, a.status, a.reason, a.doctor_notes,
                  pu.name AS patient_name, p.gender, p.date_of_birth
           FROM appointments a
           JOIN patients p ON p.id = a.patient_id
           JOIN users pu ON pu.id = p.user_id
           WHERE a.doctor_id = ?
           ORDER BY a.appt_date DESC, a.appt_time DESC""",
        (doctor_id,),
    )


def update_doctor_appointment(appointment_id: int, doctor_id: int, status: str, notes: str | None) -> bool:
    if status not in config.APPOINTMENT_STATUSES:
        raise ValueError("Unknown appointment status.")
    return execute(
        """UPDATE appointments SET status = ?, doctor_notes = COALESCE(?, doctor_notes),
           updated_at = datetime('now') WHERE id = ? AND doctor_id = ?""",
        (status, notes, appointment_id, doctor_id),
    ) > 0


def list_desk_appointments(status: str | None = None, date_from: str | None = None,
                           date_to: str | None = None) -> list[dict]:
    sql = """SELECT a.id, a.appt_date, a.appt_time, a.status, a.reason, a.doctor_id,
                    pu.name AS patient_name, du.name AS doctor_name, dep.name AS department
             FROM appointments a
             JOIN patients p ON p.id = a.patient_id
             JOIN users pu ON pu.id = p.user_id
             JOIN doctors d ON d.id = a.doctor_id
             JOIN users du ON du.id = d.user_id
             LEFT JOIN departments dep ON dep.id = a.department_id WHERE 1=1"""
    params: list = []
    if status:
        sql += " AND a.status = ?"
        params.append(status)
    if date_from:
        sql += " AND a.appt_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND a.appt_date <= ?"
        params.append(date_to)
    return query(sql + " ORDER BY a.appt_date, a.appt_time", tuple(params))


def get_appointment(appointment_id: int) -> dict | None:
    return query_one("SELECT * FROM appointments WHERE id = ?", (appointment_id,))


def set_appointment_status(appointment_id: int, status: str) -> None:
    if status not in config.APPOINTMENT_STATUSES:
        raise ValueError("Unknown appointment status.")
    execute("UPDATE appointments SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, appointment_id))


def reschedule_appointment(appointment_id: int, appt_date: str, appt_time: str) -> None:
    appt = get_appointment(appointment_id)
    if not appt or appt["status"] not in config.ACTIVE_STATUSES:
        raise ValueError("Only scheduled or confirmed appointments can be rescheduled.")
    _validate_slot(appt_date, appt_time)
    with get_conn() as conn:
        try:
            conn.execute(
                """UPDATE appointments SET appt_date = ?, appt_time = ?, updated_at = datetime('now')
                   WHERE id = ?""", (appt_date, appt_time, appointment_id))
        except sqlite3.IntegrityError as exc:
            raise ValueError(_SLOT_TAKEN) from exc


# ---- Medical records ------------------------------------------------------
def add_record(patient_id, original_name, stored_name, ext, size, category, description) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO medical_records(patient_id, original_name, stored_name, file_ext, size_bytes,
               category, description) VALUES (?,?,?,?,?,?,?)""",
            (patient_id, original_name, stored_name, ext, size, category, description),
        )
        return cur.lastrowid


def list_records(patient_id: int) -> list[dict]:
    return query("SELECT * FROM medical_records WHERE patient_id = ? ORDER BY uploaded_at DESC", (patient_id,))


def get_record(record_id: int, patient_id: int) -> dict | None:
    return query_one("SELECT * FROM medical_records WHERE id = ? AND patient_id = ?", (record_id, patient_id))


def delete_record(record_id: int, patient_id: int) -> str | None:
    """Delete only if the record belongs to this patient. Returns the stored file name."""
    record = get_record(record_id, patient_id)
    if not record:
        return None
    execute("DELETE FROM medical_records WHERE id = ? AND patient_id = ?", (record_id, patient_id))
    return record["stored_name"]


# ---- Medications, reminders, measurements --------------------------------
def add_medication(patient_id, name, frequency, start_date, end_date, notes) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO medications(patient_id, medicine_name, frequency, start_date, end_date, notes) VALUES (?,?,?,?,?,?)",
            (patient_id, name, frequency, start_date, end_date, notes))
        return cur.lastrowid


def list_medications(patient_id: int) -> list[dict]:
    return query("SELECT * FROM medications WHERE patient_id = ? ORDER BY start_date DESC", (patient_id,))


def delete_medication(medication_id: int, patient_id: int) -> bool:
    return execute("DELETE FROM medications WHERE id = ? AND patient_id = ?", (medication_id, patient_id)) > 0


def add_reminder(patient_id, reminder_type, title, remind_date, remind_time, doctor_name, reason, notes) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reminders(patient_id, reminder_type, title, remind_date, remind_time, doctor_name,
               reason, notes) VALUES (?,?,?,?,?,?,?,?)""",
            (patient_id, reminder_type, title, remind_date, remind_time, doctor_name, reason, notes))
        return cur.lastrowid


def list_reminders(patient_id: int) -> list[dict]:
    return query("SELECT * FROM reminders WHERE patient_id = ? ORDER BY remind_date, remind_time", (patient_id,))


def set_reminder_done(reminder_id: int, patient_id: int, done: bool) -> bool:
    return execute("UPDATE reminders SET is_done = ? WHERE id = ? AND patient_id = ?",
                   (1 if done else 0, reminder_id, patient_id)) > 0


def delete_reminder(reminder_id: int, patient_id: int) -> bool:
    return execute("DELETE FROM reminders WHERE id = ? AND patient_id = ?", (reminder_id, patient_id)) > 0


def add_measurement(patient_id, measured_on, weight, systolic, diastolic, glucose) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO health_measurements(patient_id, measured_on, weight_kg, systolic_bp, diastolic_bp,
               glucose_mg_dl) VALUES (?,?,?,?,?,?)""",
            (patient_id, measured_on, weight, systolic, diastolic, glucose))
        return cur.lastrowid


def list_measurements(patient_id: int) -> list[dict]:
    return query("SELECT * FROM health_measurements WHERE patient_id = ? ORDER BY measured_on", (patient_id,))


# ---- Feedback, audit, settings -------------------------------------------
def add_feedback(user_id: int, category: str, message: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO feedback(user_id, category, message) VALUES (?,?,?)",
                           (user_id, category, message))
        return cur.lastrowid


def list_own_feedback(user_id: int) -> list[dict]:
    return query("SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC", (user_id,))


def list_all_feedback(status: str | None = None) -> list[dict]:
    sql = """SELECT f.*, u.name, u.email, u.role FROM feedback f JOIN users u ON u.id = f.user_id"""
    params: tuple = ()
    if status:
        sql += " WHERE f.status = ?"
        params = (status,)
    return query(sql + " ORDER BY f.created_at DESC", params)


def update_feedback(feedback_id: int, status: str, response: str | None) -> None:
    if status not in config.FEEDBACK_STATUSES:
        raise ValueError("Unknown feedback status.")
    execute("UPDATE feedback SET status = ?, response = COALESCE(?, response), updated_at = datetime('now') WHERE id = ?",
            (status, response, feedback_id))


def log_action(user_id: int | None, action: str, details: str = "") -> None:
    """Audit trail. Callers must never pass passwords or document contents."""
    try:
        execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?,?,?)", (user_id, action, details[:300]))
    except sqlite3.Error:
        LOG.exception("Audit write failed for action %s", action)


def get_app_setting(key: str, default: str = "") -> str:
    row = query_one("SELECT value FROM app_settings WHERE key = ?", (key,))
    return row["value"] if row and row["value"] is not None else default


def set_app_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO app_settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                     (key, value))


# ---- Analytics (aggregates only; no document content) ---------------------
def totals() -> dict:
    return query_one(
        """SELECT
           (SELECT COUNT(*) FROM patients) AS patients,
           (SELECT COUNT(*) FROM doctors) AS doctors,
           (SELECT COUNT(*) FROM appointments) AS appointments,
           (SELECT COUNT(*) FROM appointments WHERE status = 'completed') AS completed,
           (SELECT COUNT(*) FROM appointments WHERE status = 'cancelled') AS cancelled,
           (SELECT COUNT(*) FROM medical_records) AS records,
           (SELECT COUNT(*) FROM feedback WHERE status != 'resolved') AS open_feedback,
           (SELECT COUNT(*) FROM users WHERE is_active = 1) AS active_users,
           (SELECT COUNT(*) FROM departments) AS departments""") or {}


def appointment_status_counts() -> list[dict]:
    return query("SELECT status, COUNT(*) AS count FROM appointments GROUP BY status")


def appointments_per_day() -> list[dict]:
    return query("SELECT appt_date AS day, COUNT(*) AS count FROM appointments GROUP BY appt_date ORDER BY appt_date")


def department_demand() -> list[dict]:
    return query(
        """SELECT COALESCE(dep.name, 'Unassigned') AS department, COUNT(*) AS count
           FROM appointments a LEFT JOIN departments dep ON dep.id = a.department_id
           GROUP BY COALESCE(dep.name, 'Unassigned') ORDER BY count DESC""")


def doctor_workload() -> list[dict]:
    return query(
        """SELECT u.name AS doctor, COUNT(a.id) AS count FROM doctors d
           JOIN users u ON u.id = d.user_id LEFT JOIN appointments a ON a.doctor_id = d.id
           GROUP BY d.id ORDER BY count DESC""")


def patient_dobs() -> list[str]:
    rows = query("SELECT date_of_birth FROM patients WHERE date_of_birth IS NOT NULL AND date_of_birth != ''")
    return [r["date_of_birth"] for r in rows]


def record_category_counts() -> list[dict]:
    return query("SELECT category, COUNT(*) AS count FROM medical_records GROUP BY category ORDER BY count DESC")


def feedback_status_counts() -> list[dict]:
    return query("SELECT status, COUNT(*) AS count FROM feedback GROUP BY status")


def patient_growth() -> list[dict]:
    return query(
        """SELECT substr(u.created_at, 1, 10) AS day, COUNT(*) AS count FROM patients p
           JOIN users u ON u.id = p.user_id GROUP BY day ORDER BY day""")


# ---------- diet & health plan ----------
def get_health_plan(patient_id: int) -> dict | None:
    return query_one("SELECT * FROM health_plans WHERE patient_id = ?", (patient_id,))


def save_health_plan(patient_id: int, inputs: dict, budget: str, diet: str) -> None:
    import json
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO health_plans (patient_id, inputs_json, budget_tier, diet, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(patient_id) DO UPDATE SET inputs_json = excluded.inputs_json,
                   budget_tier = excluded.budget_tier, diet = excluded.diet, updated_at = excluded.updated_at""",
            (patient_id, json.dumps(inputs), budget, diet))


def get_daily_log(patient_id: int, log_date: str) -> dict | None:
    return query_one("SELECT * FROM daily_logs WHERE patient_id = ? AND log_date = ?", (patient_id, log_date))


def save_daily_log(patient_id: int, log_date: str, water_glasses: int, walk_minutes: int, meal_keys: list) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_logs (patient_id, log_date, water_glasses, walk_minutes, meals_done)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(patient_id, log_date) DO UPDATE SET water_glasses = excluded.water_glasses,
                   walk_minutes = excluded.walk_minutes, meals_done = excluded.meals_done""",
            (patient_id, log_date, water_glasses, walk_minutes, ",".join(meal_keys)))


def recent_daily_logs(patient_id: int, days: int = 14) -> list[dict]:
    return query("SELECT * FROM daily_logs WHERE patient_id = ? ORDER BY log_date DESC LIMIT ?", (patient_id, days))


def plan_tier_counts() -> list[dict]:
    return query("SELECT budget_tier, COUNT(*) AS n FROM health_plans GROUP BY budget_tier")


def admin_user_rows(search: str = "", role: str = "", active: bool | None = None) -> list[dict]:
    sql = """SELECT u.id, u.name, u.email, u.role, u.is_active, u.created_at, hp.budget_tier,
                    (SELECT COUNT(*) FROM appointments a JOIN patients p ON p.id = a.patient_id
                     WHERE p.user_id = u.id) AS appt_count
             FROM users u
             LEFT JOIN patients p ON p.user_id = u.id
             LEFT JOIN health_plans hp ON hp.patient_id = p.id
             WHERE 1 = 1"""
    params: list = []
    if search:
        sql += " AND (u.name LIKE ? OR u.email LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if role:
        sql += " AND u.role = ?"
        params.append(role)
    if active is not None:
        sql += " AND u.is_active = ?"
        params.append(1 if active else 0)
    sql += " ORDER BY u.created_at DESC, u.id DESC"
    return query(sql, tuple(params))

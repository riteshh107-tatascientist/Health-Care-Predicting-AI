"""Central configuration.

Secrets are read from Streamlit Community Cloud secrets first, then from environment
variables (or a local .env file). No secret or password lives in source code.
"""
from __future__ import annotations

import os
from datetime import time as dtime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def get_setting(key: str, default: str | None = None) -> str | None:
    """Streamlit secrets first (Community Cloud), then environment variables, then default."""
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # no secrets file, or running outside `streamlit run`
        pass
    value = os.getenv(key)
    return value if value not in (None, "") else default


# ---- Branding -------------------------------------------------------------
APP_NAME = "HealthCareX Medical & Wellness Center"
APP_SHORT_NAME = "HealthCareX"
APP_VERSION = "2.1.0"
TAGLINE = "Compassionate Care. Smarter Healthcare. Better Patient Support."
OWNER_NAME = "Ritesh Kumar Singh"
OWNER_TITLE = "Founder, Owner & CEO"
OWNER_STATEMENT = "Technology-driven healthcare support designed around patients, accessibility and informed care."
CURRENCY = "₹"

# ---- Paths ----------------------------------------------------------------
DATABASE_PATH = BASE_DIR / (get_setting("DATABASE_PATH", "data/healthcarex.db") or "data/healthcarex.db")
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_DIR = BASE_DIR / "logs"
PORTRAIT_PATH = BASE_DIR / "assets" / "owner" / "portrait.jpg"
DATASET_PATH = BASE_DIR / "data" / "diabetes.csv"
MODEL_DIR = BASE_DIR / "models"

# ---- Accounts and demo data ----------------------------------------------
ADMIN_EMAIL = get_setting("ADMIN_EMAIL")
ADMIN_PASSWORD = get_setting("ADMIN_PASSWORD")
ADMIN_NAME = get_setting("ADMIN_NAME", "System Administrator")
SEED_DEMO_DATA = (get_setting("SEED_DEMO_DATA", "false") or "false").lower() == "true"
DEMO_PASSWORD = get_setting("DEMO_PASSWORD")  # no default: demo accounts need an explicit password
DEMO_DOMAIN = "healthcarex-demo.example"
DEMO_ENABLED = SEED_DEMO_DATA and bool(DEMO_PASSWORD)

# ---- Security and limits --------------------------------------------------
MAX_UPLOAD_MB = 10
ALLOWED_UPLOAD_TYPES = (".pdf", ".png", ".jpg", ".jpeg")
SESSION_TIMEOUT_MINUTES = 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300

# ---- Clinic scheduling ----------------------------------------------------
CLINIC_START = dtime(9, 0)
CLINIC_END = dtime(17, 0)
SLOT_MINUTES = 30
MAX_BOOKING_DAYS_AHEAD = 60


def time_slots() -> list[str]:
    """Bookable 'HH:MM' start times between clinic start and end."""
    slots, minutes = [], CLINIC_START.hour * 60 + CLINIC_START.minute
    end = CLINIC_END.hour * 60 + CLINIC_END.minute
    while minutes + SLOT_MINUTES <= end:
        slots.append(f"{minutes // 60:02d}:{minutes % 60:02d}")
        minutes += SLOT_MINUTES
    return slots


# ---- Enumerations ---------------------------------------------------------
ROLES = ("patient", "doctor", "staff", "admin")
APPOINTMENT_STATUSES = ("scheduled", "confirmed", "completed", "cancelled")
ACTIVE_STATUSES = ("scheduled", "confirmed")
FEEDBACK_STATUSES = ("open", "in progress", "resolved")
FEEDBACK_CATEGORIES = ("General feedback", "Service complaint", "Technical issue", "General query", "Compliment")
RECORD_CATEGORIES = (
    "Lab report", "Prescription", "Imaging / X-ray", "Doctor's note",
    "Discharge summary", "Vaccination", "Other",
)
BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
GENDERS = ("Female", "Male", "Other", "Prefer not to say")
COMMON_ALLERGIES = ("None", "Penicillin", "Aspirin", "Latex", "Peanuts", "Tree nuts", "Shellfish", "Milk", "Eggs", "Other")
MEDICATION_FREQUENCIES = (
    "Once daily", "Twice daily", "Three times daily", "Every 8 hours",
    "Once weekly", "As directed by my doctor", "As needed",
)
REMINDER_TYPES = ("Medication reminder", "Follow-up visit", "Lab test", "Doctor appointment", "Other")

# ---- Departments, services, demo doctors ---------------------------------
DEPARTMENTS = {
    "General Medicine": "Primary consultations, fever, infections and general health concerns.",
    "Cardiology": "Heart and blood-vessel care, ECG and cardiac risk review.",
    "Neurology": "Brain, nerve and headache-related evaluation.",
    "Orthopedics": "Bone, joint, muscle and back-pain care.",
    "Pediatrics": "Healthcare for infants, children and adolescents.",
    "Gynecology": "Women's reproductive and general gynecological health.",
    "Psychiatry": "Mental wellbeing, stress, sleep and mood support.",
    "Dermatology": "Skin, hair and nail conditions.",
    "ENT": "Ear, nose and throat conditions.",
    "Ophthalmology": "Eye examination and vision care.",
    "Emergency Medicine": "Urgent and emergency assessment, 24 hours.",
}

# (service name, department, cost in INR, description)
SERVICES = [
    ("General consultation", "General Medicine", 300, "Initial assessment with a physician"),
    ("Complete blood count (CBC)", "General Medicine", 350, "Routine blood test panel"),
    ("Lipid profile", "Cardiology", 600, "Cholesterol and triglyceride panel"),
    ("ECG", "Cardiology", 400, "Electrocardiogram recording"),
    ("Echocardiography", "Cardiology", 2200, "Ultrasound of the heart"),
    ("EEG", "Neurology", 1500, "Electroencephalogram recording"),
    ("X-ray (chest / limb)", "Orthopedics", 500, "Plain radiography"),
    ("Physiotherapy session", "Orthopedics", 700, "Supervised rehabilitation session"),
    ("Pediatric vaccination", "Pediatrics", 250, "Immunisation visit per schedule"),
    ("Pap smear", "Gynecology", 900, "Cervical screening test"),
    ("Dermoscopy review", "Dermatology", 800, "Magnified skin examination"),
    ("Audiometry", "ENT", 650, "Hearing assessment"),
]

DEMO_DOCTORS = [
    {"name": "Dr. Ananya Sharma", "email": "ananya.sharma@" + DEMO_DOMAIN, "department": "General Medicine",
     "specialization": "General Physician", "qualification": "MBBS, MD", "experience": 12, "fee": 300},
    {"name": "Dr. Rajesh Kumar", "email": "rajesh.kumar@" + DEMO_DOMAIN, "department": "Cardiology",
     "specialization": "Cardiology", "qualification": "MBBS, MD, DM", "experience": 15, "fee": 800},
    {"name": "Dr. Priya Menon", "email": "priya.menon@" + DEMO_DOMAIN, "department": "Pediatrics",
     "specialization": "Pediatrics", "qualification": "MBBS, MD", "experience": 10, "fee": 600},
    {"name": "Dr. Vikram Singh", "email": "vikram.singh@" + DEMO_DOMAIN, "department": "Orthopedics",
     "specialization": "Orthopedic Surgery", "qualification": "MBBS, MS (Ortho)", "experience": 14, "fee": 700},
    {"name": "Dr. Neha Gupta", "email": "neha.gupta@" + DEMO_DOMAIN, "department": "Neurology",
     "specialization": "Neurology", "qualification": "MBBS, MD, DM", "experience": 11, "fee": 900},
    {"name": "Dr. Imran Ali", "email": "imran.ali@" + DEMO_DOMAIN, "department": "Dermatology",
     "specialization": "Dermatology", "qualification": "MBBS, DVD", "experience": 9, "fee": 650},
    {"name": "Dr. Sunita Rao", "email": "sunita.rao@" + DEMO_DOMAIN, "department": "Gynecology",
     "specialization": "Obstetrics & Gynecology", "qualification": "MBBS, MS (OBG)", "experience": 13, "fee": 800},
    {"name": "Dr. Arjun Mehta", "email": "arjun.mehta@" + DEMO_DOMAIN, "department": "Emergency Medicine",
     "specialization": "Emergency Medicine", "qualification": "MBBS, MD (EM)", "experience": 8, "fee": 500},
]

# ---- Lab reference ranges (ILLUSTRATIVE adult ranges; labs differ) -------
# ranges: {sex or "default": (low, high)}; None means no bound on that side.
LAB_REFERENCE = {
    "hemoglobin": {"label": "Hemoglobin", "unit": "g/dL",
                   "synonyms": ["hemoglobin", "haemoglobin", "hgb", "hb"], "exclude": ["a1c"],
                   "ranges": {"male": (13.5, 17.5), "female": (12.0, 15.5)}},
    "wbc": {"label": "White blood cells (WBC)", "unit": "x10^9/L",
            "synonyms": ["white blood cell count", "total leucocyte count", "total leukocyte count", "wbc", "tlc"],
            "exclude": [], "ranges": {"default": (4.0, 11.0)}},
    "platelets": {"label": "Platelets", "unit": "x10^9/L",
                  "synonyms": ["platelet count", "platelets"], "exclude": [],
                  "ranges": {"default": (150, 400)}},
    "fasting_glucose": {"label": "Fasting glucose", "unit": "mg/dL",
                        "synonyms": ["fasting blood sugar", "fasting glucose", "glucose (fasting)", "glucose fasting", "fbs"],
                        "exclude": [], "ranges": {"default": (70, 99)}},
    "hba1c": {"label": "HbA1c", "unit": "%",
              "synonyms": ["hba1c", "glycated hemoglobin", "glycosylated hemoglobin", "hemoglobin a1c"],
              "exclude": [], "ranges": {"default": (None, 5.7)}},
    "total_cholesterol": {"label": "Total cholesterol", "unit": "mg/dL",
                          "synonyms": ["total cholesterol", "cholesterol (total)", "serum cholesterol"],
                          "exclude": [], "ranges": {"default": (None, 200)}},
    "ldl": {"label": "LDL cholesterol", "unit": "mg/dL",
            "synonyms": ["ldl cholesterol", "ldl-c", "ldl"], "exclude": [],
            "ranges": {"default": (None, 100)}},
    "hdl": {"label": "HDL cholesterol", "unit": "mg/dL",
            "synonyms": ["hdl cholesterol", "hdl-c", "hdl"], "exclude": [],
            "ranges": {"male": (40, None), "female": (50, None)}},
    "triglycerides": {"label": "Triglycerides", "unit": "mg/dL",
                      "synonyms": ["triglycerides", "triglyceride"], "exclude": [],
                      "ranges": {"default": (None, 150)}},
    "creatinine": {"label": "Creatinine", "unit": "mg/dL",
                   "synonyms": ["serum creatinine", "creatinine"], "exclude": [],
                   "ranges": {"male": (0.7, 1.3), "female": (0.6, 1.1)}},
    "urea": {"label": "Blood urea", "unit": "mg/dL",
             "synonyms": ["blood urea nitrogen", "blood urea", "urea"], "exclude": [],
             "ranges": {"default": (15, 45)}},
    "sodium": {"label": "Sodium", "unit": "mmol/L",
               "synonyms": ["sodium"], "exclude": [], "ranges": {"default": (136, 145)}},
    "potassium": {"label": "Potassium", "unit": "mmol/L",
                  "synonyms": ["potassium"], "exclude": [], "ranges": {"default": (3.5, 5.1)}},
}

# ---- Symptom guidance rules (educational routing only; never diagnostic) --
SYMPTOM_RULES = [
    {"category": "Respiratory or infectious", "department": "General Medicine",
     "keywords": ["fever", "cough", "sore throat", "runny nose", "cold", "body ache"],
     "note": "These symptoms are often associated with respiratory or infectious conditions."},
    {"category": "Cardiovascular", "department": "Cardiology",
     "keywords": ["palpitations", "leg swelling", "dizziness", "high blood pressure"],
     "note": "Some of these symptoms can relate to heart or circulation issues and merit clinical review."},
    {"category": "Neurological", "department": "Neurology",
     "keywords": ["headache", "numbness", "tingling", "memory problems", "tremor"],
     "note": "These symptoms can have many causes and benefit from a neurology or general review."},
    {"category": "Gastrointestinal", "department": "General Medicine",
     "keywords": ["nausea", "vomiting", "abdominal pain", "diarrhea", "constipation", "acidity"],
     "note": "Digestive symptoms are commonly assessed by a general physician first."},
    {"category": "Musculoskeletal", "department": "Orthopedics",
     "keywords": ["joint pain", "back pain", "knee pain", "muscle pain", "stiffness"],
     "note": "Joint and muscle symptoms can be evaluated by an orthopedic or general clinician."},
    {"category": "Skin", "department": "Dermatology",
     "keywords": ["rash", "itching", "hives", "acne", "skin lesion"],
     "note": "Skin symptoms are best examined in person by a dermatologist."},
    {"category": "Ear, nose and throat", "department": "ENT",
     "keywords": ["ear pain", "sinus pain", "hearing loss", "nasal blockage"],
     "note": "Ear, nose and throat symptoms can be assessed by an ENT specialist."},
    {"category": "Eye", "department": "Ophthalmology",
     "keywords": ["eye pain", "blurred vision", "red eye"],
     "note": "Eye symptoms should be checked in person, particularly when vision changes."},
    {"category": "Mental wellbeing", "department": "Psychiatry",
     "keywords": ["anxiety", "low mood", "sleep problems", "stress"],
     "note": "Persistent mood, stress or sleep concerns are worth discussing with a mental-health professional."},
]

RED_FLAG_PHRASES = [
    "chest pain", "difficulty breathing", "shortness of breath", "unable to breathe", "fainting",
    "unconscious", "seizure", "confusion", "severe bleeding", "face drooping", "slurred speech",
    "sudden severe headache", "coughing blood", "vomiting blood", "blue lips", "severe allergic reaction",
    "suicidal", "self-harm",
]
MENTAL_HEALTH_CRISIS_PHRASES = ["suicidal", "self-harm"]
SYMPTOM_CHOICES = sorted({kw for rule in SYMPTOM_RULES for kw in rule["keywords"]})
DURATION_OPTIONS = ("Less than 24 hours", "1 to 3 days", "4 to 7 days", "More than 1 week")
AGE_GROUPS = ("Child (0-12)", "Teen (13-19)", "Adult (20-59)", "Older adult (60+)")

# ---- Disclaimers ----------------------------------------------------------
DISCLAIMER_GENERAL = (
    "HealthCareX provides educational and administrative support tools. AI-generated information and "
    "risk estimates are not medical diagnoses and do not replace evaluation by a qualified healthcare professional."
)
DISCLAIMER_EMERGENCY = (
    "If this may be a life-threatening emergency, contact your local emergency service or go to the "
    "nearest emergency department immediately. Do not wait for an appointment."
)
DISCLAIMER_ML = "Educational ML estimate — not a clinical diagnosis."

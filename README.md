# HealthCareX Medical & Wellness Center

**Smart Healthcare Services & Patient Support System** · Version 2.0.0
Founded & Managed by **Ritesh Kumar Singh**

*Compassionate Care. Smarter Healthcare. Better Patient Support.*

HealthCareX is a Streamlit patient-support platform. Patients find services, book free appointment slots,
keep medical documents private, understand lab values in plain language, check symptoms for routing
guidance, and explore a risk model trained on a real public clinical dataset. Doctors, staff and
administrators each get a role-specific workspace.

> **Medical safety.** HealthCareX provides educational and administrative support tools. AI-generated
> information and risk estimates are **not medical diagnoses** and do not replace evaluation by a qualified
> healthcare professional. The app never names a disease from symptoms, never prescribes medicine, and
> directs every red-flag symptom to emergency care. For a life-threatening emergency, contact your local
> emergency service or go to the nearest emergency department.

---

## 1. Features by role

| Area | Patient | Doctor | Staff | Admin |
|---|---|---|---|---|
| Landing splash, home page, owner leadership section | ✔ | ✔ | ✔ | ✔ |
| Registration with welcome ribbon and balloons | ✔ | – | – | – |
| Doctors, departments, services finder (filters, search) | ✔ book | – | ✔ view | – |
| Appointments: book free slots, cancel, history | ✔ | – | – | – |
| Own patients' schedule, status, clinical notes | – | ✔ own only | – | – |
| Appointment desk: confirm, complete, cancel, reschedule | – | – | ✔ | ✔ |
| Medical record library (PDF/PNG/JPEG, validated, private) | ✔ | – | – | – |
| Lab report analyzer (PDF text or pasted values) | ✔ | – | – | – |
| Symptom guidance with red-flag screening | ✔ | – | – | – |
| Diabetes risk assessment on the real Pima dataset | ✔ | – | – | – |
| Medications and follow-up reminders | ✔ | – | – | – |
| Health dashboard (charts from recorded data only) | ✔ | – | – | – |
| Feedback and support (submit, track, resolve) | ✔ | ✔ submit | ✔ desk | ✔ desk |
| Admin analytics, users, doctors, departments, services | – | – | – | ✔ |
| Emergency information page | ✔ | ✔ | ✔ | ✔ (configures) |

Analytics show aggregates only. Admins have no route to patient documents or clinical notes.

## 2. Machine learning (real public data)

**Dataset:** Pima Indians Diabetes Database (NIDDK, via the UCI Machine Learning Repository), included
in `data/diabetes.csv`. 768 women aged 21+ of Pima Indian heritage; 268 positive and 500 negative cases.
It is an old, small, single-population dataset, so results do not generalise to other populations,
sexes or ages.

**Pipeline (all inside one scikit-learn `Pipeline`, fitted on training folds only):**
zero-as-missing cleaning → median imputation → standard scaling → model.
Impossible zeros in Glucose, BloodPressure, SkinThickness, Insulin and BMI are treated as "not recorded".

**Evaluation protocol:** stratified 80/20 split (614 train / 154 test, random_state=42).
Model selection uses 5-fold stratified cross-validation on the training split only. The held-out test
set is used once for the final report.

**Results from the training run (`python -m ml.train`):**

| Model | CV ROC-AUC (mean ± std) | Test accuracy | Test precision | Test recall | Test F1 | Test ROC-AUC | Brier (lower better) |
|---|---|---|---|---|---|---|---|
| Logistic Regression (**selected**) | 0.844 ± 0.016 | 0.734 | 0.603 | 0.704 | 0.650 | 0.813 | 0.181 |
| Random Forest | 0.831 ± 0.023 | 0.766 | 0.661 | 0.685 | 0.673 | 0.823 | 0.162 |

- **Baseline** (always predict the majority class): 0.649 accuracy. This is why accuracy is not used to
  select a model.
- **Selection rule:** the model with the higher cross-validated ROC-AUC on training data is chosen,
  so Logistic Regression is selected. Random Forest has a slightly higher test ROC-AUC. That difference
  is within the noise of a 154-row test set, and it was not used to choose the model.
- **Confusion matrix, selected model (test set, threshold 0.5):** [[75 TN, 25 FP], [16 FN, 38 TP]].

The UI labels every output "Educational ML estimate — not a clinical diagnosis." Feature importance
shows what the model relied on, not what causes diabetes.

## 3. Architecture

```
HealthCareX/
├── app.py                 # entry point: splash → bootstrap → auth gate → role routing
├── config.py              # settings, reference ranges, symptom rules, departments (no secrets)
├── navigation.py          # role-based sidebar menu (single source of truth)
├── auth.py                # sign-in, lockout after failures, idle timeout, account re-check
├── security.py            # bcrypt hashing and password policy
├── database.py            # SQLite schema, parameterised queries, ownership filters, analytics
├── utils.py               # validation, secure uploads (signature check), safe file paths, logging
├── lab_analysis.py        # report parsing and reference-range comparison
├── ui.py                  # theme, splash, hero, ribbon, cards, disclaimers
├── views/                 # one module per page (home, appointments, records, risk, admin, …)
├── ml/train.py            # real-data pipeline, cross-validation, metrics, model saving
├── data/diabetes.csv      # Pima Indians Diabetes dataset (see data/README.md)
├── assets/owner/portrait.jpg  # leadership portrait (used only in the Leadership section)
├── .streamlit/config.toml # light healthcare theme, 10 MB upload limit
├── tests/                 # 53 automated tests, including headless walkthroughs of every role
├── requirements.txt       # pinned runtime dependencies
└── requirements-dev.txt   # adds pytest
```

Startup: the splash animation appears first, then the database is created and reference data seeded once
per server process. Each page renders inside a guard, so an unexpected error shows a friendly message and
is logged to `logs/app.log`, never as a traceback in the browser.

**Database** (SQLite, foreign keys on): `users`, `patients`, `doctors`, `departments`, `services`,
`appointments`, `medical_records`, `medications`, `reminders`, `health_measurements`, `feedback`,
`audit_logs`, `app_settings`. Appointments carry partial unique indexes on active doctor-slot and
patient-slot pairs, so double-booking is blocked by the database itself, not just by the UI.

## 4. Security and privacy

- Passwords hashed with bcrypt (cost 12). Plain-text passwords are never stored or logged.
- Lockout for 5 minutes after 5 failed sign-ins. Sessions expire after 60 minutes idle, and each request
  re-checks that the account is still active.
- Role checks on every page, and ownership checks in queries: patients only see their own records,
  appointments and reminders; doctors only see appointments assigned to them.
- Uploads: 10 MB limit, extension allow-list (PDF, PNG, JPEG), and **content signature verification**, so
  a renamed executable is rejected. Files are stored under random server-side names inside a per-patient
  folder, with path-traversal protection. Original names are sanitised and only shown as labels.
- Audit log records actions (sign-in, bookings, uploads, admin changes) without passwords or document content.
- **No credentials in source code.** Admin and demo passwords come from environment variables or
  Streamlit secrets. Demo accounts are created only when `DEMO_PASSWORD` is set.
- Patient registration collects only what the platform needs. Health fields are optional.

## 5. Local setup

Use **Python 3.11 or 3.12** (the pinned NumPy 2.4 and pandas 3 require 3.11+).

```bash
cd HealthCareX
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then edit ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_PASSWORD
streamlit run app.py
```

Open http://localhost:8501. The database is created automatically at `data/healthcarex.db`.

**Run the tests:**

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

**Regenerate the model report** (optional; writes `models/metrics.json` and `models/best_model.joblib`):

```bash
python -m ml.train
```

## 6. Configuration (environment variables or Streamlit secrets)

| Key | Required | Purpose |
|---|---|---|
| `ADMIN_EMAIL` | for admin access | Administrator sign-in email (created once at first start) |
| `ADMIN_PASSWORD` | for admin access | Administrator password. Use a strong, unique value |
| `ADMIN_NAME` | no | Display name for the administrator |
| `DEMO_PASSWORD` | to enable demo | Password for demo accounts. Unset = no demo accounts |
| `SEED_DEMO_DATA` | no (default `true`) | Set `false` to disable demo data even when `DEMO_PASSWORD` is set |
| `DATABASE_PATH` | no | SQLite file location (default `data/healthcarex.db`) |

Demo data is always labelled "Demo data for educational / testing purposes." For a production-style
database, leave `DEMO_PASSWORD` unset.

## 7. Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository. `.gitignore` excludes `.env`, databases, uploads and logs.
2. In Streamlit Community Cloud, choose **New app** → your repository → branch → main file `app.py`.
   Under **Advanced settings**, select **Python 3.12**.
3. Open **Settings → Secrets** and add, in TOML format:
   ```toml
   ADMIN_EMAIL = "admin@your-clinic.example"
   ADMIN_PASSWORD = "a-strong-unique-password"
   DEMO_PASSWORD = "a-demo-only-password"     # optional; omit for no demo accounts
   SEED_DEMO_DATA = "true"                    # optional
   ```
4. Deploy. The app reads secrets through `st.secrets` first, then environment variables.

**Important limitation.** Streamlit Community Cloud's file system is ephemeral. SQLite data and uploaded
documents are lost when the app restarts or is redeployed. This build is suitable for demonstrations,
pilots and coursework. Before handling real patient data, move the database to a managed PostgreSQL
service and store documents in encrypted object storage, with backups and access logging.

## 8. Known limitations (stated plainly)

- **Image OCR is not included.** PDFs with a text layer are read directly. For scanned images, paste the
  values into the text tab. OCR was left out to keep the install lightweight and reliable.
- **Reference ranges are illustrative adult ranges**, edited in `config.py`. Ranges stated in a report
  are used in preference and labelled as such.
- **Symptom guidance is rule-based routing**, not a validated clinical triage system. It is deliberately
  conservative: any red-flag phrase produces an emergency warning.
- **The risk model is an educational demonstration.** It uses one small dataset from one population and
  has not been clinically validated. It must not inform any real medical decision.
- **Payments, SMS/email notifications, video consultation and insurance are not included.**
- **No multi-factor authentication** yet. Recommended before real deployment.
- **SQLite is single-writer.** Suitable for a small clinic or pilot; use PostgreSQL for higher concurrency.

## 9. Future improvements

PostgreSQL and encrypted object storage; email/SMS appointment reminders; OCR for scanned reports
(e.g. Tesseract, opt-in); multi-factor authentication; clinician-validated reference ranges per lab;
calibrated risk probabilities with decision-curve analysis; audit-log viewer for admins; accessibility
audit (WCAG 2.1 AA) with screen-reader testing.

## 10. Acknowledgements

Dataset: Pima Indians Diabetes Database, National Institute of Diabetes and Digestive and Kidney Diseases,
via the UCI Machine Learning Repository.

---

**HealthCareX Medical & Wellness Center** · Founded & Managed by Ritesh Kumar Singh
*Technology-driven healthcare support designed around patients, accessibility and informed care.*

## Going live (production checklist)

- Set `SEED_DEMO_DATA=false` (default). No demo patients, doctors or passwords are created.
- Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the hosting secrets. The owner account is created from them on first start.
- Create doctor and staff accounts from **Admin Console → Manage hospital**. Use **Reset password** to issue temporary passwords privately.
- Enter real hospital emergency contacts under **Admin Console → Emergency settings**. The app does not invent emergency numbers.
- Host the database and uploads on persistent storage (PostgreSQL and object storage). Streamlit Community Cloud resets local files on restart.
- Have clinical, legal and data-protection review completed before real patient data is stored.

"""Administrator console: analytics, users, doctors, departments, services and emergency settings.

Admins see aggregate analytics and account administration. They do not get routes to patients'
medical documents or clinical notes.
"""
from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
import ui
from auth import require_role
from database import (add_department, add_service, appointment_status_counts, appointments_per_day,
                      create_doctor_account, create_staff_account, department_demand, doctor_workload,
                      feedback_status_counts, get_app_setting, get_user_by_email, list_departments, list_doctors,
                      list_services, list_users, log_action, patient_dobs, patient_growth,
                      record_category_counts, set_app_setting, set_user_active, set_user_role, totals)
from security import hash_password, password_problems
from utils import age_from_dob, clean_text, valid_email

LOG = logging.getLogger("healthcarex.admin")


def render(user: dict) -> None:
    if not require_role(user, ("admin",)):
        return
    ui.page_header("Admin Console", "Operational analytics and administration. Patient documents are not shown here.", "🛠️")
    tab_an, tab_users, tab_docs, tab_dept, tab_serv, tab_em = st.tabs(
        ["📊 Analytics", "👥 Users", "👨‍⚕️ Doctors", "🏢 Departments", "🔬 Services", "🚨 Emergency settings"])
    with tab_an:
        _analytics()
    with tab_users:
        _users(user)
    with tab_docs:
        _doctors(user)
    with tab_dept:
        _departments(user)
    with tab_serv:
        _services(user)
    with tab_em:
        _emergency(user)


def _analytics() -> None:
    t = totals()
    k = st.columns(6)
    k[0].metric("Patients", t.get("patients", 0))
    k[1].metric("Doctors", t.get("doctors", 0))
    k[2].metric("Appointments", t.get("appointments", 0))
    k[3].metric("Completed", t.get("completed", 0))
    k[4].metric("Cancelled", t.get("cancelled", 0))
    k[5].metric("Open feedback", t.get("open_feedback", 0))
    k2 = st.columns(2)
    k2[0].metric("Uploaded documents", t.get("records", 0))
    k2[1].metric("Active accounts", t.get("active_users", 0))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Appointments over time")
        per_day = appointments_per_day()
        if per_day:
            df = pd.DataFrame(per_day)
            st.plotly_chart(px.line(df, x="day", y="count", markers=True,
                                    labels={"day": "Date", "count": "Appointments"}).update_layout(height=300))
        else:
            ui.empty_state("No appointments yet.")
    with c2:
        st.markdown("#### Appointment status")
        statuses = appointment_status_counts()
        if statuses:
            fig = go.Figure(go.Pie(labels=[s["status"].title() for s in statuses],
                                   values=[s["count"] for s in statuses], hole=0.5))
            fig.update_layout(height=300)
            st.plotly_chart(fig)
        else:
            ui.empty_state("No appointment statuses yet.")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Department demand")
        demand = department_demand()
        if demand:
            st.plotly_chart(px.bar(pd.DataFrame(demand), x="department", y="count",
                                   labels={"department": "Department", "count": "Appointments"},
                                   color_discrete_sequence=["#0f9b8e"]).update_layout(height=300))
        else:
            ui.empty_state("No department demand data yet.")
    with c4:
        st.markdown("#### Service utilisation (doctor workload)")
        workload = doctor_workload()
        if workload:
            st.plotly_chart(px.bar(pd.DataFrame(workload), x="doctor", y="count",
                                   labels={"doctor": "Doctor", "count": "Appointments"},
                                   color_discrete_sequence=["#0b3d6e"]).update_layout(height=300))
        else:
            ui.empty_state("No doctor workload data yet.")

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### Patient age distribution")
        ages = [a for a in (age_from_dob(d) for d in patient_dobs()) if a is not None]
        if ages:
            st.plotly_chart(px.histogram(x=ages, nbins=12, labels={"x": "Age (years)", "y": "Patients"},
                                         color_discrete_sequence=["#14b8a6"]).update_layout(height=300))
        else:
            ui.empty_state("No patient birth dates recorded yet.")
    with c6:
        st.markdown("#### Feedback status")
        fb = feedback_status_counts()
        if fb:
            st.plotly_chart(px.pie(pd.DataFrame(fb), names="status", values="count", hole=0.5)
                            .update_layout(height=300))
        else:
            ui.empty_state("No feedback yet.")

    c7, c8 = st.columns(2)
    with c7:
        st.markdown("#### Patient growth")
        growth = patient_growth()
        if growth:
            df = pd.DataFrame(growth)
            df["cumulative"] = df["count"].cumsum()
            st.plotly_chart(px.line(df, x="day", y="cumulative", markers=True,
                                    labels={"day": "Date", "cumulative": "Patients"}).update_layout(height=280))
        else:
            ui.empty_state("No patient registrations yet.")
    with c8:
        st.markdown("#### Uploaded document categories")
        cats = record_category_counts()
        if cats:
            st.plotly_chart(px.bar(pd.DataFrame(cats), x="category", y="count",
                                   labels={"category": "Category", "count": "Documents"},
                                   color_discrete_sequence=["#0b3d6e"]).update_layout(height=280))
        else:
            ui.empty_state("No documents uploaded yet.")


def _users(user: dict) -> None:
    import pandas as pd
    from database import admin_user_rows, query, set_user_password

    st.markdown("#### Find and manage users")
    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("Search by name or email", key="adm_search", placeholder="e.g. ritesh or gmail")
    role_pick = c2.selectbox("Role", ["All", *config.ROLES], key="adm_role_f")
    status_pick = c3.selectbox("Status", ["All", "Active", "Suspended"], key="adm_status_f")
    active_filter = {"All": None, "Active": True, "Suspended": False}[status_pick]
    rows = admin_user_rows(search.strip(), "" if role_pick == "All" else role_pick, active_filter)
    counts = {r: sum(1 for x in rows if x["role"] == r) for r in config.ROLES}
    st.caption(f"Showing {len(rows)} user(s) | patients {counts['patient']} | doctors {counts['doctor']} | "
               f"staff {counts['staff']} | admins {counts['admin']}")
    if not rows:
        ui.empty_state("No users match these filters.")
    else:
        table = pd.DataFrame([{
            "Name": r["name"], "Email": r["email"], "Role": r["role"],
            "Status": "Active" if r["is_active"] else "Suspended",
            "Health plan": r["budget_tier"] or "Not created",
            "Appointments": r["appt_count"], "Joined": r["created_at"][:10],
        } for r in rows])
        st.dataframe(table, hide_index=True)
        st.download_button("⬇️ Export this list (CSV)", table.to_csv(index=False).encode("utf-8"),
                           "healthcarex_users.csv", "text/csv", key="adm_export")

    options = {f"{r['name']} · {r['email']} · {r['role']}": r for r in rows if r["id"] != user["id"]}
    if options:
        st.markdown("#### Manage a user")
        target = options[st.selectbox("Choose a user", list(options), key="adm_user")]
        st.write(f"**{target['name']}** | role **{target['role']}** | status "
                 f"**{'Active' if target['is_active'] else 'Suspended'}** | joined {target['created_at'][:10]}")
        activity = query("SELECT * FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT 10", (target["id"],))
        with st.expander("Recent activity (last 10 actions)"):
            if activity:
                st.dataframe(pd.DataFrame(activity), hide_index=True)
            else:
                st.caption("No recorded activity yet.")
        c1, c2 = st.columns(2)
        new_role = c1.selectbox("Role", list(config.ROLES), index=list(config.ROLES).index(target["role"]),
                                key="adm_role")
        active = c2.checkbox("Account active (untick to suspend)", value=bool(target["is_active"]), key="adm_active")
        if st.button("Save user changes", key="adm_save_user", type="primary"):
            set_user_role(target["id"], new_role)
            set_user_active(target["id"], active)
            log_action(user["id"], "admin_user_update", f"user {target['id']} role={new_role} active={active}")
            st.success("User updated.")
            st.rerun()
        if st.button("Generate temporary password", key="adm_reset_pw"):
            import secrets
            temp = secrets.token_urlsafe(9) + "1a"
            set_user_password(target["id"], hash_password(temp))
            log_action(user["id"], "admin_password_reset", f"user {target['id']}")
            st.success(f"Temporary password for {target['email']} (shown once):")
            st.code(temp)

    st.markdown("#### Create a staff account")
    with st.form("staff_form", clear_on_submit=True):
        name = st.text_input("Full name *")
        email = st.text_input("Email address *")
        password = st.text_input("Temporary password *", type="password",
                                 help="8+ characters with letters and numbers. Ask the staff member to change it.")
        submitted = st.form_submit_button("Create staff account")
    if submitted:
        _create_account(user, name, email, password, lambda n, e, h: create_staff_account(n, e, h), "staff")


def _create_account(admin: dict, name: str, email: str, password: str, creator, label: str) -> None:
    name = clean_text(name, 120)
    email = (email or "").strip().lower()
    problems = password_problems(password or "")
    if len(name) < 2:
        st.error("Please enter a name.")
    elif not valid_email(email):
        st.error("Please enter a valid email address.")
    elif problems:
        st.error("Password needs: " + ", ".join(problems) + ".")
    else:
        try:
            creator(name, email, hash_password(password))
            log_action(admin["id"], f"admin_create_{label}", f"email domain {email.split('@')[-1]}")
            st.success(f"{label.title()} account created.")
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            LOG.exception("Account creation failed")
            st.error("The account could not be created. Please try again.")


def _doctors(user: dict) -> None:
    doctors = list_doctors(active_only=False)
    st.dataframe([{"Name": d["name"], "Department": d["department"], "Specialization": d["specialization"],
                   "Experience (yrs)": d["experience_years"], "Fee": f"{config.CURRENCY}{d['consultation_fee']:,.0f}",
                   "Demo": "Yes" if d["is_demo"] else "No"} for d in doctors], hide_index=True)
    st.markdown("#### Add a doctor")
    depts = list_departments()
    with st.form("doctor_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        email = c2.text_input("Email address")
        c3, c4 = st.columns(2)
        dept = c3.selectbox("Department", [d["name"] for d in depts])
        spec = c4.text_input("Specialization", placeholder="e.g. Interventional Cardiology")
        c5, c6, c7 = st.columns(3)
        qual = c5.text_input("Qualification", placeholder="MBBS, MD")
        years = c6.number_input("Years of experience", min_value=0, max_value=70, value=5)
        fee = c7.number_input(f"Consultation fee ({config.CURRENCY})", min_value=0.0, max_value=50000.0, value=500.0, step=50.0)
        password = st.text_input("Temporary password", type="password")
        submitted = st.form_submit_button("Add doctor")
    if submitted:
        dept_id = next(d["id"] for d in depts if d["name"] == dept)
        if not spec.strip():
            st.error("Please enter a specialization.")
        else:
            _create_account(user, name, email, password,
                            lambda n, e, h: create_doctor_account(n, e, h, dept_id, spec.strip(),
                                                                 qual.strip(), int(years), float(fee)), "doctor")


def _departments(user: dict) -> None:
    st.dataframe([{"Department": d["name"], "Description": d["description"]} for d in list_departments()],
                 hide_index=True)
    with st.form("dept_form", clear_on_submit=True):
        name = st.text_input("New department name", max_chars=80)
        desc = st.text_input("Description", max_chars=200)
        submitted = st.form_submit_button("Add department")
    if submitted:
        if not name.strip():
            st.error("Please enter a department name.")
        else:
            try:
                add_department(name.strip(), desc.strip())
                log_action(user["id"], "admin_add_department", name.strip())
                st.success("Department added.")
            except ValueError as exc:
                st.error(str(exc))


def _services(user: dict) -> None:
    st.dataframe([{"Service": s["name"], "Department": s["department"], "Indicative cost": f"{config.CURRENCY}{s['cost']:,.0f}"}
                  for s in list_services()], hide_index=True)
    depts = list_departments()
    with st.form("service_form", clear_on_submit=True):
        name = st.text_input("Service name", max_chars=120)
        dept = st.selectbox("Department", [d["name"] for d in depts])
        cost = st.number_input(f"Indicative cost ({config.CURRENCY})", min_value=0.0, max_value=500000.0, value=300.0, step=50.0)
        desc = st.text_input("Description", max_chars=200)
        submitted = st.form_submit_button("Add service")
    if submitted:
        if not name.strip():
            st.error("Please enter a service name.")
        else:
            dept_id = next(d["id"] for d in depts if d["name"] == dept)
            add_service(name.strip(), dept_id, float(cost), desc.strip())
            log_action(user["id"], "admin_add_service", name.strip())
            st.success("Service added.")


def _emergency(user: dict) -> None:
    st.caption("Configure the emergency information shown on the Emergency page. Leave blank if not applicable. "
               "HealthCareX does not publish emergency numbers on your behalf.")
    with st.form("emergency_form"):
        info = st.text_area("Hospital emergency information", value=get_app_setting("emergency_info"), height=120,
                            placeholder="e.g. Emergency department location and entrance instructions")
        phone = st.text_input("Emergency phone number for patients", value=get_app_setting("emergency_phone"))
        submitted = st.form_submit_button("Save emergency information")
    if submitted:
        set_app_setting("emergency_info", info.strip())
        set_app_setting("emergency_phone", phone.strip())
        log_action(user["id"], "admin_emergency_update", "emergency settings changed")
        st.success("Saved.")

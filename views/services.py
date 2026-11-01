"""Doctor, department and service finder. Patients can book directly from here."""
from __future__ import annotations

import streamlit as st

import config
import ui
from database import list_departments, list_doctors, list_services
from navigation import go_to


def render(user: dict) -> None:
    role = user["role"]
    ui.page_header("Doctors & Services", "Find the right department and clinician, then book a time that is free.", "🩺")
    if config.DEMO_ENABLED:
        ui.demo_badge()
    departments = list_departments()
    dept_names = ["All departments"] + [d["name"] for d in departments]
    dept_ids = {d["name"]: d["id"] for d in departments}
    tab_doc, tab_dept, tab_service = st.tabs(["👨‍⚕️ Doctors", "🏢 Departments", "🔬 Services & tests"])

    with tab_doc:
        c1, c2 = st.columns(2)
        choice = c1.selectbox("Department", dept_names, key="svc_dept")
        search = c2.text_input("Search by name or specialty", placeholder="e.g. Cardiology or Priya", key="svc_search")
        department_id = dept_ids.get(choice)
        doctors = list_doctors(department_id, search.strip() or None)
        if not doctors:
            ui.empty_state("No doctors match these filters. Try another department or search term.")
        for doc in doctors:
            left, mid, right = st.columns([3, 2, 1])
            with left:
                ui.show_card(doc["name"], f'{doc["specialization"]} · {doc["department"] or "General"}',
                             footer=doc["qualification"] or "", icon="👨‍⚕️")
            with mid:
                st.markdown(f"**Experience:** {doc['experience_years']} years  \n"
                            f"**Consultation fee:** {config.CURRENCY}{doc['consultation_fee']:,.0f}  \n"
                            f"**Availability:** {doc['availability']}")
                if doc["is_demo"]:
                    ui.demo_badge()
            with right:
                if role == "patient":
                    st.button("Book", key=f"book_doc_{doc['id']}", on_click=go_to,
                              args=("appointments", role,
                                    {"department_id": doc["department_id"], "doctor_id": doc["id"]}))

    with tab_dept:
        cols = st.columns(3)
        for idx, dept in enumerate(departments):
            count = len(list_doctors(dept["id"]))
            cols[idx % 3].markdown(
                ui.card(dept["name"], dept["description"] or "Specialist care",
                        footer=f"{count} doctor(s) listed"),
                unsafe_allow_html=True,
            )

    with tab_service:
        c1, c2 = st.columns(2)
        service_dept = c1.selectbox("Department", dept_names, key="svc_service_dept")
        service_search = c2.text_input("Search services", placeholder="e.g. ECG, blood", key="svc_service_search")
        services = list_services(dept_ids.get(service_dept), service_search.strip() or None)
        if not services:
            ui.empty_state("No services match these filters.")
        for svc in services:
            left, right = st.columns([4, 1])
            with left:
                ui.show_card(svc["name"], svc["description"] or "", footer=f'{svc["department"]} · '
                             f'{config.CURRENCY}{svc["cost"]:,.0f} (indicative)', icon="🔬")
            with right:
                if role == "patient":
                    st.button("Book", key=f"book_svc_{svc['id']}", on_click=go_to,
                              args=("appointments", role, {"department_id": svc["department_id"]}))

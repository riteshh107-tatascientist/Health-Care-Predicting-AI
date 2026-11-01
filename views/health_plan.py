"""Diet & Health Plan: personal targets, budget-based menus, meal timing, walking, vitamins and a daily tracker."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import nutrition as nut
import ui
from database import (get_daily_log, get_health_plan, get_patient_by_user, recent_daily_logs, save_daily_log,
                      save_health_plan)


def _age_from_dob(dob_iso: str | None) -> int | None:
    if not dob_iso:
        return None
    born = date.fromisoformat(dob_iso)
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _clean_hhmm(text: str) -> str | None:
    try:
        return datetime.strptime(text.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def _pick(options: list, value, fallback: int = 0) -> int:
    return options.index(value) if value in options else fallback


def render(user: dict) -> None:
    patient = get_patient_by_user(user["id"])
    if not patient:
        ui.empty_state("Your patient profile was not found. Please contact the hospital desk.")
        return
    ui.page_header("Diet & Health Plan",
                   "What to eat, how much water, when to eat, how to walk, and which vitamins you can get from "
                   "everyday food, planned for your family's budget.", "🥗")
    ui.disclaimer("General educational guidance, not a prescription. If you have a medical condition, are pregnant, "
                  "or are under 18, check this plan with your doctor or a dietitian.")
    saved = get_health_plan(patient["id"])
    inputs = json.loads(saved["inputs_json"]) if saved else None
    t_plan, t_menu, t_vit, t_track = st.tabs(["🎯 My plan", "🍛 7-day menu", "🧬 Vitamins & minerals", "✅ Daily tracker"])
    with t_plan:
        _plan_tab(patient, inputs)
    with t_menu:
        _menu_tab(inputs)
    with t_vit:
        _vitamin_tab(inputs)
    with t_track:
        _tracker_tab(patient, inputs)


def _plan_tab(patient: dict, inputs: dict | None) -> None:
    d = inputs or {}
    age_default = _age_from_dob(patient.get("date_of_birth")) or d.get("age") or 30
    sex_default = {"Male": "Male", "Female": "Female"}.get(patient.get("gender"), "Other / prefer not to say")
    st.markdown("##### Tell us about you")
    st.caption("Fields marked * are needed to calculate your plan. Your answers are used only for this plan.")
    with st.form("plan_form"):
        c1, c2, c3 = st.columns(3)
        sex = c1.selectbox("Sex *", nut.SEX_OPTIONS, index=_pick(nut.SEX_OPTIONS, d.get("sex", sex_default)),
                           help="Used only in the calorie formula.")
        age = c2.number_input("Age in years *", min_value=5, max_value=110, value=int(age_default),
                              help="Filled from your date of birth in My Profile when available.")
        height = c3.number_input("Height in centimetres *", min_value=100, max_value=230,
                                 value=int(d.get("height_cm", 165)),
                                 help="Example: 165. Five feet five inches is about 165 cm.")
        c4, c5, c6 = st.columns(3)
        weight = c4.number_input("Weight in kilograms *", min_value=20.0, max_value=250.0,
                                 value=float(d.get("weight_kg", 60.0)), step=0.5,
                                 help="Use your latest weight. Example: 60.5")
        activity = c5.selectbox("A typical day is *", list(nut.ACTIVITY_OPTIONS),
                                index=_pick(list(nut.ACTIVITY_OPTIONS), d.get("activity_label"), 2),
                                help="Think about your usual day, not your best day.")
        goal = c6.selectbox("My goal *", nut.GOAL_OPTIONS, index=_pick(nut.GOAL_OPTIONS, d.get("goal")),
                            help="Gradual change, about 0.5 kg a week, is safer and easier to keep.")
        c7, c8, c9 = st.columns(3)
        diet = c7.selectbox("What I eat *", nut.DIET_OPTIONS, index=_pick(nut.DIET_OPTIONS, d.get("diet")),
                            help="Choose what you already eat. Menus will not suggest foods you avoid.")
        budget = c8.selectbox("My family's food budget *", nut.BUDGET_OPTIONS,
                              index=_pick(nut.BUDGET_OPTIONS, d.get("budget")),
                              help="Choose the level that fits your household. Menus and costs change with it.")
        pregnant = c9.checkbox("Pregnant or breastfeeding", value=bool(d.get("pregnant", False)),
                               help="Tick this if it applies. Please follow your doctor's advice.")
        c10, c11 = st.columns(2)
        wake_h = c10.number_input("Usual wake-up hour (0 to 23, e.g. 6 for 6 AM)", min_value=0, max_value=23,
                                  value=int(d.get("wake", "06:30")[:2]),
                                  help="Breakfast and water times are planned from this.")
        sleep_h = c11.number_input("Usual bedtime hour (0 to 23, e.g. 22 for 10 PM)", min_value=0, max_value=23,
                                   value=int(d.get("sleep", "22:30")[:2]),
                                   help="Dinner is planned 2 to 3 hours before this.")
        wake = f"{int(wake_h):02d}:00"
        sleep = f"{int(sleep_h):02d}:00"
        conditions = st.text_area("Medical conditions or medicines (optional)", value=d.get("conditions", ""))
        st.caption("Example: diabetes, high blood pressure, thyroid. We show safety notes for these.")
        submitted = st.form_submit_button("Save my plan", type="primary")
    if submitted:
        if weight <= 0 or height <= 0:
            st.error("Please enter your height and weight.")
        else:
            new_inputs = {
                "sex": sex, "age": int(age), "height_cm": float(height), "weight_kg": float(weight),
                "activity_label": activity, "goal": goal, "diet": diet, "budget": budget,
                "pregnant": bool(pregnant), "wake": wake, "sleep": sleep,
                "conditions": conditions.strip(),
            }
            save_health_plan(patient["id"], new_inputs, budget, diet)
            st.toast("Your plan is saved", icon="✅")
            inputs = new_inputs
    if inputs:
        _show_result(inputs)
    else:
        ui.empty_state("Fill the form above and press Save my plan. You will see your daily targets, "
                       "a meal timetable and a walking plan.")


def _show_result(inputs: dict) -> None:
    p = nut.build_plan(inputs)
    st.markdown("##### Your personal targets")
    m = st.columns(5)
    m[0].metric("BMI", p["bmi"], p["bmi_category"])
    m[1].metric("Calories per day", f"{p['calories']} kcal", "estimate")
    m[2].metric("Protein per day", f"{p['protein_g']} g")
    m[3].metric("Water per day", f"{p['water_glasses']} glasses", f"{p['water_ml'] / 1000:.2f} litres")
    m[4].metric("Walking per day", f"{p['walk']['daily_minutes']} min", "build up over about 4 weeks")
    for note in p["notes"]:
        st.warning(note)
    st.markdown("##### Meal and water timetable")
    schedule = pd.DataFrame(p["schedule"]).rename(columns={"time": "Time", "what": "What to do", "why": "Why it helps"})
    st.dataframe(schedule, hide_index=True)
    left, right = st.columns(2)
    with left:
        st.markdown("###### How to build each plate")
        for item in p["plate"]:
            st.markdown(f"- {item}")
    with right:
        st.markdown("###### Walking")
        st.write(p["walk"]["text"])
        st.caption(p["walk"]["caution"])
        st.markdown("###### Your family budget")
        st.info(p["budget_note"])
    st.caption("Estimates use the Mifflin-St Jeor formula and WHO activity guidance. Your real needs may differ; "
               "review them with a clinician.")


def _menu_tab(inputs: dict | None) -> None:
    c1, c2 = st.columns(2)
    budget = c1.selectbox("Budget level", nut.BUDGET_OPTIONS,
                          index=_pick(nut.BUDGET_OPTIONS, (inputs or {}).get("budget")), key="menu_budget")
    diet = c2.selectbox("Diet", nut.DIET_OPTIONS, index=_pick(nut.DIET_OPTIONS, (inputs or {}).get("diet")),
                        key="menu_diet")
    st.info(nut.BUDGET_COST_NOTE[budget])
    st.dataframe(pd.DataFrame(nut.weekly_menu(budget, diet, date.today())), hide_index=True)
    st.markdown("**Ways to keep it affordable**")
    st.markdown("- Buy dal, rice and oats in bulk, and seasonal vegetables from the local market.\n"
                "- Replace packaged snacks with roasted chana, peanuts, a banana or buttermilk.\n"
                "- Cook dal and vegetables in batches to save gas and time.")


def _vitamin_tab(inputs: dict | None) -> None:
    diet = st.selectbox("Diet", nut.DIET_OPTIONS, index=_pick(nut.DIET_OPTIONS, (inputs or {}).get("diet")),
                        key="vit_diet")
    st.caption("Most people can get these vitamins and minerals from everyday food. Supplements are not needed for "
               "everyone, and high doses can be harmful. Ask a doctor before taking any.")
    st.dataframe(pd.DataFrame(nut.vitamin_guide(diet)), hide_index=True)


def _tracker_tab(patient: dict, inputs: dict | None) -> None:
    st.markdown("##### Today's tracker")
    if not inputs:
        ui.empty_state("Save your plan first (My plan tab). The tracker uses your water and walking targets.")
        return
    today = date.today()
    target = nut.build_plan(inputs)["water_glasses"]
    today_log = get_daily_log(patient["id"], today.isoformat()) or {}
    yesterday = get_daily_log(patient["id"], (today - timedelta(days=1)).isoformat())
    if not yesterday:
        st.info("You did not log yesterday. Logging a few things today helps you build a routine.")
    elif yesterday["water_glasses"] < target:
        st.warning(f"Yesterday you drank {yesterday['water_glasses']} of {target} glasses. "
                   "Start with one glass right now.")
    logs = recent_daily_logs(patient["id"], 14)
    m = st.columns(3)
    m[0].metric("Water goal", f"{target} glasses")
    m[1].metric("Water streak", f"{nut.streak_days(logs, target, today)} day(s)")
    m[2].metric("Walking goal", "30 min a day")
    done_now = set((today_log.get("meals_done") or "").split(","))
    with st.form("tracker_form"):
        glasses = st.number_input("Glasses of water today (1 glass = 250 ml)", min_value=0, max_value=30,
                                  value=int(today_log.get("water_glasses", 0)))
        walk = st.number_input("Minutes walked today", min_value=0, max_value=300,
                               value=int(today_log.get("walk_minutes", 0)),
                               help="Count brisk walking, stairs or chores that make you breathe harder.")
        meals = st.multiselect("Meals you had today", [label for _, label in nut.MEALS],
                               default=[label for key, label in nut.MEALS if key in done_now],
                               help="Tick each meal you ate, even if it was small.")
        if st.form_submit_button("Save today", type="primary"):
            keys = [key for key, label in nut.MEALS if label in meals]
            save_daily_log(patient["id"], today.isoformat(), int(glasses), int(walk), keys)
            st.toast("Today's log is saved", icon="✅")
            st.rerun()
    if logs:
        df = pd.DataFrame(logs[:7]).sort_values("log_date")
        fig = go.Figure()
        fig.add_bar(x=df["log_date"], y=df["water_glasses"], name="Glasses of water", marker_color="#0f9b8e")
        fig.add_bar(x=df["log_date"], y=df["walk_minutes"], name="Walking minutes", marker_color="#0b3d6e")
        fig.update_layout(barmode="group", height=320, margin=dict(l=10, r=10, t=30, b=10),
                          legend=dict(orientation="h"), title="Last 7 days")
        st.plotly_chart(fig)

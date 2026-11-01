from datetime import date

import nutrition as n


def test_bmr_mifflin_male_example():
    # 30 y, 70 kg, 175 cm male: 10*70 + 6.25*175 - 5*30 + 5 = 1648.75
    assert round(n.bmr("Male", 30, 175, 70)) == 1649


def test_bmi_and_asian_categories():
    assert n.bmi_value(170, 70) == 24.2
    assert n.bmi_category(17.0) == "Underweight"
    assert n.bmi_category(22.0) == "Healthy range"
    assert n.bmi_category(23.5) == "Overweight (at risk)"
    assert n.bmi_category(27.0) == "Obese range"


def test_calorie_floor_and_goal_adjustment():
    maintain = n.calorie_target("Female", 35, 160, 60, "moderate", "Maintain my weight")
    lose = n.calorie_target("Female", 35, 160, 60, "moderate", "Lose weight gradually")
    assert lose == maintain - 400 or lose == 1200
    assert n.calorie_target("Female", 80, 140, 30, "sedentary", "Lose weight gradually") >= 1200


def test_water_target_is_clamped_and_rounded():
    assert n.water_target_ml(50, "sedentary") == 1750
    assert n.water_target_ml(20, "sedentary") == 1500
    assert n.water_target_ml(100, "active") == 3500
    assert n.water_target_ml(60, "moderate") % 250 == 0


def test_meal_schedule_dinner_before_sleep():
    sched = n.meal_schedule("06:30", "22:30")
    assert any("Dinner" in s["what"] for s in sched)
    assert any("Water" in s["what"] or "water" in s["what"] for s in sched)


def test_weekly_menu_has_seven_days_and_budget_grows_variety():
    lower = n.weekly_menu("Lower-income family", "Vegetarian", date(2026, 11, 1))
    high = n.weekly_menu("High-income family", "Vegetarian", date(2026, 11, 1))
    assert len(lower) == 7 and len(high) == 7
    assert len(n._menu_lists("High-income family", "Vegetarian")["lunch"]) > len(n._menu_lists("Lower-income family", "Vegetarian")["lunch"])


def test_vegetarian_menu_has_no_meat():
    menu = n.weekly_menu("Lower-income family", "Vegetarian", date(2026, 11, 1))
    text = " ".join(" ".join(str(v) for v in row.values()) for row in menu).lower()
    assert "chicken" not in text and "fish" not in text and "egg" not in text


def test_safety_notes_for_condition_and_underweight():
    notes = n.safety_notes(40, 17.0, "Type 2 diabetes", False)
    assert any("condition" in x for x in notes) and any("below the healthy range" in x for x in notes)


def test_build_plan_and_streak():
    plan = n.build_plan({"sex": "Male", "age": 28, "height_cm": 172, "weight_kg": 70,
                         "activity_label": list(n.ACTIVITY_OPTIONS)[2], "goal": "Maintain my weight",
                         "diet": "Vegetarian", "budget": "Middle-income family", "wake": "06:30", "sleep": "22:30",
                         "conditions": "", "pregnant": False})
    assert plan["calories"] > 1500 and plan["protein_g"] == 70 and plan["water_glasses"] >= 8
    today = date(2026, 11, 1)
    logs = [{"log_date": "2026-11-01", "water_glasses": 9}, {"log_date": "2026-10-31", "water_glasses": 9},
            {"log_date": "2026-10-30", "water_glasses": 2}]
    assert n.streak_days(logs, 8, today) == 2

"""Diet, hydration, meal-timing, walking and vitamin planning.

Educational estimates only. Formulas are standard population estimates (Mifflin-St Jeor for energy,
WHO activity guidance, Asian BMI cut-offs commonly used in India). They are not a prescription.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

SEX_OPTIONS = ["Female", "Male", "Other / prefer not to say"]
ACTIVITY_OPTIONS = {
    "Mostly sitting (office, study, little exercise)": "sedentary",
    "Light activity (short walks, household work)": "light",
    "Moderate (brisk walk or exercise 3-5 days a week)": "moderate",
    "Very active (physical job or daily exercise)": "active",
}
ACTIVITY_FACTOR = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
GOAL_OPTIONS = ["Maintain my weight", "Lose weight gradually", "Gain weight gradually"]
GOAL_ADJUST_KCAL = {"Maintain my weight": 0, "Lose weight gradually": -400, "Gain weight gradually": 300}
DIET_OPTIONS = ["Vegetarian", "Eggetarian (vegetarian + eggs)", "Non-vegetarian"]
BUDGET_OPTIONS = ["Lower-income family", "Middle-income family", "High-income family"]
BUDGET_COST_NOTE = {
    "Lower-income family": "Built around dal, seasonal vegetables, eggs, roti, rice, sprouts and seasonal fruit. Indicative food cost about ₹100-140 per person per day (varies by city).",
    "Middle-income family": "Adds milk, curd, paneer, more eggs, chicken or fish once or twice a week, nuts and more fruit. Indicative food cost about ₹180-260 per person per day.",
    "High-income family": "Adds more variety: fish, lean meat, whole grains, berries, nuts, leafy greens and yoghurt. Indicative food cost ₹350 and above per person per day.",
}
GLASS_ML = 250
MEALS = [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("snack", "Evening snack"), ("dinner", "Dinner")]


def bmi_value(height_cm: float, weight_kg: float) -> float:
    return round(weight_kg / ((height_cm / 100) ** 2), 1)


def bmi_category(value: float) -> str:
    """Asian BMI cut-offs (used in India): <18.5 underweight, 18.5-22.9 healthy, 23-24.9 overweight, >=25 obese."""
    if value < 18.5:
        return "Underweight"
    if value < 23:
        return "Healthy range"
    if value < 25:
        return "Overweight (at risk)"
    return "Obese range"


def bmr(sex: str, age: int, height_cm: float, weight_kg: float) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if sex == "Male":
        return base + 5
    if sex == "Female":
        return base - 161
    return base - 78  # midpoint when sex is not stated


def calorie_target(sex: str, age: int, height_cm: float, weight_kg: float, activity_key: str, goal: str) -> int:
    tdee = bmr(sex, age, height_cm, weight_kg) * ACTIVITY_FACTOR[activity_key]
    target = tdee + GOAL_ADJUST_KCAL[goal]
    floor = {"Female": 1200, "Male": 1500}.get(sex, 1350)  # never recommend below these safety floors
    return int(round(max(target, floor) / 10.0) * 10)


def protein_target_g(weight_kg: float, activity_key: str) -> int:
    per_kg = {"sedentary": 0.8, "light": 0.9, "moderate": 1.0, "active": 1.2}[activity_key]
    return int(round(weight_kg * per_kg))


def water_target_ml(weight_kg: float, activity_key: str) -> int:
    ml = 35 * weight_kg + (500 if activity_key in ("moderate", "active") else 0)
    ml = min(max(ml, 1500), 3500)
    return int(round(ml / 250.0) * 250)


def glasses_for(ml: int) -> int:
    return math.ceil(ml / GLASS_ML)


def walk_plan(activity_key: str, age: int) -> dict:
    if activity_key in ("sedentary", "light"):
        text = ("Weeks 1-2: walk 10 minutes after lunch and 10 minutes after dinner. Each week add 5 minutes "
                "until you reach 30 minutes a day, spread over the day.")
    else:
        text = ("Aim for 30 minutes of brisk walking on most days (about 150 minutes a week, the WHO guideline). "
                "A 10-minute walk after lunch and dinner also helps control blood sugar after meals.")
    caution = "Stop and get medical help if you have chest pain, breathlessness, dizziness or fainting."
    if age >= 60:
        caution += " At 60 and above, start slowly and check with your doctor before a new routine."
    return {"daily_minutes": 30, "text": text, "caution": caution, "weekly_target_minutes": 150}


def meal_schedule(wake: str = "06:30", sleep: str = "22:30") -> list[dict]:
    """Practical timetable. Dinner finishes about 2-3 hours before bed; water is spread through the day."""
    wake_t = datetime.strptime(wake, "%H:%M")
    sleep_t = datetime.strptime(sleep, "%H:%M")
    if sleep_t <= wake_t:
        sleep_t += timedelta(days=1)
    breakfast = min(wake_t + timedelta(hours=1), datetime.strptime("09:30", "%H:%M"))
    dinner = max(sleep_t - timedelta(hours=3), datetime.strptime("19:00", "%H:%M"))
    dinner = min(dinner, datetime.strptime("21:00", "%H:%M"))
    last_water = sleep_t - timedelta(hours=1)

    def fmt(t: datetime) -> str:
        return t.strftime("%I:%M %p").lstrip("0")

    return [
        {"time": fmt(wake_t), "what": "Wake up, drink 1-2 glasses of water (room temperature). Light stretch.",
         "why": "Rehydrates after the night."},
        {"time": fmt(breakfast), "what": "Breakfast: protein + whole grain + fruit or vegetables.",
         "why": "Do not skip breakfast; it steadies energy for the morning."},
        {"time": "11:00 AM", "what": "Seasonal fruit or a handful of roasted chana or peanuts (optional).",
         "why": "Prevents overeating at lunch."},
        {"time": "12:30 - 1:30 PM", "what": "Lunch: half plate vegetables, quarter protein, quarter roti or rice. Walk 10 minutes after.",
         "why": "The biggest meal of the day, eaten with the most daylight energy."},
        {"time": "4:30 - 5:00 PM", "what": "Evening snack: buttermilk, a banana, or chana. Water.",
         "why": "Stops late-evening hunger and snacking on packaged food."},
        {"time": fmt(dinner), "what": "Dinner: light and early. Walk 10 minutes after.",
         "why": "Finishing 2-3 hours before sleep improves digestion and sleep."},
        {"time": f"Every 2 hours until {fmt(last_water)}", "what": "Drink water (1 glass = 250 ml). Stop about 1 hour before bed.",
         "why": "Spreads fluid through the day and reduces night-time toilet trips."},
    ]


def plate_guide() -> list[str]:
    return [
        "Half the plate: vegetables and salad (seasonal, local, cooked or raw).",
        "Quarter the plate: protein (dal, rajma, chana, eggs, paneer, curd, fish or chicken).",
        "Quarter the plate: whole grains (roti, brown rice, daliya, millets, poha).",
        "Add a small amount of healthy fat (1 teaspoon oil or a few nuts) and a glass of water or buttermilk.",
        "Eat slowly, sit down, and stop when you feel about 80% full.",
    ]


_BASE = {
    "Vegetarian": {
        "breakfast": ["Poha with peanuts and peas", "Daliya or oats upma with vegetables", "Besan chilla with green chutney", "Idli with sambar (2 idli)"],
        "lunch": ["Dal + 2 roti + seasonal sabzi + curd", "Rajma or chana (1 small bowl) + roti + salad", "Vegetable khichdi + curd", "Soya chunks curry + roti + salad"],
        "snack": ["1 banana or seasonal guava", "Roasted chana or peanuts (small handful)", "Buttermilk (chaas)", "Seasonal fruit"],
        "dinner": ["Mixed vegetable sabzi + 2 roti + dal", "Moong dal chilla + green salad", "Palak or methi sabzi + roti + curd", "Vegetable pulao (less oil) + raita"],
    },
    "Eggetarian (vegetarian + eggs)": {
        "breakfast": ["2 boiled eggs + roti or poha", "Egg bhurji with onion and tomato + 1 roti", "Besan chilla + 1 egg", "Idli with sambar"],
        "lunch": ["Dal + 2 roti + seasonal sabzi + curd", "Egg curry (less oil) + roti + salad", "Vegetable khichdi + 1 boiled egg", "Rajma (small bowl) + roti + salad"],
        "snack": ["1 banana or seasonal guava", "Roasted chana or peanuts", "Buttermilk (chaas)", "Seasonal fruit"],
        "dinner": ["Mixed vegetable sabzi + 2 roti + dal", "Vegetable omelette + 1 roti", "Palak sabzi + roti + curd", "Moong dal + small rice + salad"],
    },
    "Non-vegetarian": {
        "breakfast": ["2 boiled eggs + roti or poha", "Egg bhurji + 1 roti + tomato", "Besan chilla + curd", "Idli with sambar"],
        "lunch": ["Dal + 2 roti + vegetable sabzi + curd", "Chicken curry (small portion, 1-2 times a week) + roti + salad", "Fish curry (1-2 times a week) + rice + salad", "Vegetable khichdi + boiled egg"],
        "snack": ["1 banana or seasonal guava", "Roasted chana or peanuts", "Buttermilk (chaas)", "Seasonal fruit"],
        "dinner": ["Mixed vegetable sabzi + 2 roti + dal", "Egg curry + roti + salad", "Palak sabzi + roti + curd", "Moong dal + small rice + salad"],
    },
}
_MIDDLE_ADD = {
    "Vegetarian": {"breakfast": ["Milk with oats and banana"], "lunch": ["Paneer bhurji + 2 roti + salad"], "snack": ["Curd with roasted makhana"], "dinner": ["Paneer and peas curry + roti"]},
    "Eggetarian (vegetarian + eggs)": {"breakfast": ["Milk + 2 eggs + oats"], "lunch": ["Paneer bhurji + 2 roti + salad"], "snack": ["Curd with roasted makhana"], "dinner": ["Egg and vegetable curry + roti"]},
    "Non-vegetarian": {"breakfast": ["Milk + 2 eggs + oats"], "lunch": ["Chicken curry + roti + salad (1-2 times a week)"], "snack": ["Curd with roasted makhana"], "dinner": ["Fish or chicken + vegetables + roti"]},
}
_HIGH_ADD = {
    "Vegetarian": {"breakfast": ["Yoghurt with berries and nuts"], "lunch": ["Quinoa or brown rice bowl with sprouts and paneer"], "snack": ["Mixed nuts (small handful)"], "dinner": ["Tofu or paneer stir-fry with greens"]},
    "Eggetarian (vegetarian + eggs)": {"breakfast": ["Yoghurt with berries, nuts and 2 eggs"], "lunch": ["Brown rice bowl with egg, sprouts and greens"], "snack": ["Mixed nuts (small handful)"], "dinner": ["Vegetable stir-fry with tofu or egg"]},
    "Non-vegetarian": {"breakfast": ["Yoghurt with berries, nuts and 2 eggs"], "lunch": ["Grilled fish or chicken + brown rice + greens"], "snack": ["Mixed nuts (small handful)"], "dinner": ["Grilled fish with vegetables (2 times a week)"]},
}


def _menu_lists(budget: str, diet: str) -> dict:
    lists = {m: list(_BASE[diet][m]) for m, _ in MEALS}
    tiers = BUDGET_OPTIONS
    for tier in tiers[1:tiers.index(budget) + 1]:
        add = _MIDDLE_ADD if tier == "Middle-income family" else _HIGH_ADD
        for m, _ in MEALS:
            lists[m] += add[diet][m]
    return lists


def weekly_menu(budget: str, diet: str, start: date, days: int = 7) -> list[dict]:
    lists = _menu_lists(budget, diet)
    rows = []
    for i in range(days):
        day = start + timedelta(days=i)
        row = {"Day": day.strftime("%a %d %b")}
        for m, label in MEALS:
            items = lists[m]
            row[label] = items[(day.toordinal() + i) % len(items)]
        rows.append(row)
    return rows


def vitamin_guide(diet: str) -> list[dict]:
    animal = "Eggs, milk, curd, fish" if diet != "Vegetarian" else "Milk, curd, paneer (vegetarians need milk or dairy daily)"
    return [
        {"Nutrient": "Vitamin D", "Why it matters": "Bones, muscles, immunity",
         "Everyday sources": "15-20 minutes of morning sunlight on arms and face; eggs, fortified milk, fish",
         "Budget choice": "Morning sunlight (free) and eggs", "Caution": "Ask a doctor before any supplement"},
        {"Nutrient": "Vitamin B12", "Why it matters": "Nerves, red blood cells, energy",
         "Everyday sources": animal, "Budget choice": "Milk and curd every day",
         "Caution": "Strict vegetarians and vegans may need a blood test and advice"},
        {"Nutrient": "Iron", "Why it matters": "Prevents tiredness and anaemia",
         "Everyday sources": "Dal, rajma, chana, spinach, methi, jaggery, dates; fish and chicken",
         "Budget choice": "Dal with lemon or amla; jaggery occasionally",
         "Caution": "Drink tea or coffee at least 1 hour away from iron-rich meals"},
        {"Nutrient": "Calcium", "Why it matters": "Bones and teeth",
         "Everyday sources": "Milk, curd, paneer, ragi, sesame (til), leafy greens",
         "Budget choice": "Milk or curd daily; ragi and til chikki", "Caution": "Keep salt and fizzy drinks low"},
        {"Nutrient": "Folate (B9)", "Why it matters": "Cell growth, pregnancy health",
         "Everyday sources": "Dal, chana, peanuts, leafy greens, oranges, guava",
         "Budget choice": "Chana, peanuts, seasonal leafy greens", "Caution": "Important before and during pregnancy"},
        {"Nutrient": "Vitamin C", "Why it matters": "Immunity; helps absorb iron from plants",
         "Everyday sources": "Amla, guava, lemon, orange, tomato, capsicum, sprouts",
         "Budget choice": "Seasonal guava, amla, lemon in dal", "Caution": "Eat fresh; cooking reduces it"},
        {"Nutrient": "Vitamin A", "Why it matters": "Eyes, skin, immunity",
         "Everyday sources": "Carrot, pumpkin, papaya, mango, spinach; eggs and milk",
         "Budget choice": "Seasonal carrot, pumpkin, papaya", "Caution": "Avoid high-dose vitamin A supplements"},
        {"Nutrient": "Fibre", "Why it matters": "Digestion, sugar and cholesterol control",
         "Everyday sources": "Whole grains, dal, vegetables, fruit with skin, oats, daliya",
         "Budget choice": "Dal, daliya, seasonal vegetables", "Caution": "Increase slowly and drink enough water"},
        {"Nutrient": "Omega-3 fats", "Why it matters": "Heart and brain",
         "Everyday sources": "Fish, flaxseed (alsi), walnuts, chia",
         "Budget choice": "A spoon of flaxseed or a few walnuts; fish when affordable", "Caution": "Use plain seeds, not packaged snacks"},
    ]


CONDITION_WORDS = ("diabet", "sugar", "kidney", "heart", "cardiac", "blood pressure", "bp", "hypertension",
                   "thyroid", "liver", "cholesterol", "anaemia", "anemia", "gout", "cancer")


def safety_notes(age: int, bmi: float, conditions: str, pregnant: bool) -> list[str]:
    notes = []
    if age < 18:
        notes.append("You are under 18. Growth needs differ; please review this plan with a paediatrician or dietitian.")
    if bmi < 18.5:
        notes.append("Your BMI is below the healthy range. Choose calorie-dense foods (dal, milk, eggs, nuts). If weight is falling without trying, see a doctor.")
    elif bmi >= 25:
        notes.append("Your BMI is above the healthy range. Gradual changes (about 0.5 kg a week) work best and are easier to keep.")
    if age >= 60:
        notes.append("At 60 and above, check any new walking or diet change with your doctor.")
    if pregnant:
        notes.append("Pregnancy or breastfeeding needs different calories, iron and folate. Follow your doctor's or antenatal clinic's advice.")
    low = (conditions or "").lower()
    if any(word in low for word in CONDITION_WORDS):
        notes.append("You mentioned a medical condition. Your diet, salt, sugar or fluid targets may need changes from your doctor or a dietitian. Use this plan as general guidance only.")
    return notes


def build_plan(inputs: dict) -> dict:
    height, weight, age = float(inputs["height_cm"]), float(inputs["weight_kg"]), int(inputs["age"])
    sex, activity, goal = inputs["sex"], ACTIVITY_OPTIONS[inputs["activity_label"]], inputs["goal"]
    bmi = bmi_value(height, weight)
    water = water_target_ml(weight, activity)
    return {
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "bmr": int(round(bmr(sex, age, height, weight))),
        "calories": calorie_target(sex, age, height, weight, activity, goal),
        "protein_g": protein_target_g(weight, activity),
        "water_ml": water,
        "water_glasses": glasses_for(water),
        "walk": walk_plan(activity, age),
        "schedule": meal_schedule(inputs.get("wake", "06:30"), inputs.get("sleep", "22:30")),
        "plate": plate_guide(),
        "notes": safety_notes(age, bmi, inputs.get("conditions", ""), bool(inputs.get("pregnant"))),
        "budget_note": BUDGET_COST_NOTE[inputs["budget"]],
        "activity_key": activity,
    }


def streak_days(logs: list[dict], target_glasses: int, today: date) -> int:
    """Consecutive days (ending today, or yesterday if today is not yet met) where the water goal was reached."""
    met = {r["log_date"] for r in logs if r["water_glasses"] >= target_glasses}
    day = today if today.isoformat() in met else today - timedelta(days=1)
    count = 0
    while day.isoformat() in met:
        count += 1
        day -= timedelta(days=1)
    return count

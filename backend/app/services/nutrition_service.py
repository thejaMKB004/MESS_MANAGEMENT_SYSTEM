"""Nutrition: dish nutrition data, meal totals, diet/allergy warnings, and the personal intake log.

All numbers are APPROXIMATE values for one regular mess portion. They are starting estimates that the
mess admin or kitchen should check and edit; this is not medical or dietetic advice.
"""
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..config import PORTION_MULTIPLIER
from ..timeutil import today_local

MEALS = ["breakfast", "lunch", "dinner"]
MACROS = ("kcal", "protein_g", "carbs_g", "fat_g")

# Starting estimates for the seeded dishes (one regular mess portion). Edit them on the Nutrition data page.
DEFAULT_DISHES = {
    "Idli Sambar":          dict(kcal=300, protein_g=10, carbs_g=55, fat_g=4,  fibre_g=6, food_type="veg"),
    "Poha":                 dict(kcal=270, protein_g=6,  carbs_g=45, fat_g=8,  fibre_g=3, food_type="veg", allergens=["peanuts"]),
    "Bread Omelette":       dict(kcal=330, protein_g=17, carbs_g=28, fat_g=16, fibre_g=2, food_type="egg", allergens=["gluten", "egg"]),
    "Upma":                 dict(kcal=280, protein_g=7,  carbs_g=42, fat_g=9,  fibre_g=3, food_type="veg", allergens=["gluten"]),
    "Rice & Dal":           dict(kcal=420, protein_g=14, carbs_g=78, fat_g=6,  fibre_g=7, food_type="veg"),
    "Chicken Curry":        dict(kcal=280, protein_g=25, carbs_g=8,  fat_g=16, fibre_g=2, food_type="non_veg"),
    "Paneer Butter Masala": dict(kcal=380, protein_g=14, carbs_g=12, fat_g=30, fibre_g=2, food_type="veg", allergens=["dairy", "tree_nuts"]),
    "Curd Rice":            dict(kcal=320, protein_g=9,  carbs_g=52, fat_g=8,  fibre_g=1, food_type="veg", allergens=["dairy"]),
    "Chapati & Sabzi":      dict(kcal=400, protein_g=11, carbs_g=62, fat_g=12, fibre_g=9, food_type="veg", allergens=["gluten"]),
    "Veg Biryani":          dict(kcal=450, protein_g=10, carbs_g=70, fat_g=14, fibre_g=5, food_type="veg"),
    "Egg Curry":            dict(kcal=260, protein_g=14, carbs_g=9,  fat_g=18, fibre_g=2, food_type="egg", allergens=["egg"]),
    "Khichdi":              dict(kcal=330, protein_g=12, carbs_g=55, fat_g=7,  fibre_g=5, food_type="veg"),
}


def ensure_defaults(db: Session) -> int:
    """Insert the starting estimates for any seeded dish that has no nutrition row yet. Safe to run on
    every start-up: it never overwrites values an admin has edited."""
    have = {name for (name,) in db.query(models.DishNutrition.dish_name).all()}
    added = 0
    for name, values in DEFAULT_DISHES.items():
        if name not in have:
            db.add(models.DishNutrition(dish_name=name, allergens=values.get("allergens", []),
                                        **{k: v for k, v in values.items() if k != "allergens"}))
            added += 1
    if added:
        db.commit()
    return added


def dish_to_dict(d: models.DishNutrition) -> dict:
    return {"dish_name": d.dish_name, "kcal": d.kcal, "protein_g": d.protein_g, "carbs_g": d.carbs_g,
            "fat_g": d.fat_g, "fibre_g": d.fibre_g, "food_type": d.food_type, "allergens": d.allergens or []}


def _dish_map(db: Session) -> dict:
    return {d.dish_name: d for d in db.query(models.DishNutrition).all()}


def conflicts_for(user: models.User, dish: models.DishNutrition) -> list:
    """Plain-language reasons this dish may not suit the student, based on their own profile."""
    out = []
    allergies = set(user.allergies or [])
    diet = set(user.diet_restrictions or [])
    for a in (dish.allergens or []):
        if a in allergies:
            out.append(f"contains {a.replace('_', ' ')}")
    if dish.food_type == "non_veg" and diet & {"vegetarian", "vegan", "eggetarian", "jain"}:
        out.append("non-vegetarian")
    if dish.food_type == "egg" and diet & {"vegetarian", "vegan", "jain"}:
        out.append("contains egg")
    if "vegan" in diet and "dairy" in (dish.allergens or []) and "dairy" not in allergies:
        out.append("contains dairy")
    return sorted(set(out))


def meal_nutrition(db: Session, menu: models.Menu, user=None, dishes=None) -> dict:
    """Totals for one regular portion of a whole menu meal, plus per-dish detail and warnings."""
    dishes = dishes if dishes is not None else _dish_map(db)
    totals = {k: 0.0 for k in MACROS}
    items, missing, warnings = [], [], []
    for name in (menu.dishes or []):
        d = dishes.get(name)
        if not d:
            missing.append(name)
            continue
        for k in MACROS:
            totals[k] += getattr(d, k) or 0
        item = dish_to_dict(d)
        if user is not None:
            item["conflicts"] = conflicts_for(user, d)
            for c in item["conflicts"]:
                warnings.append(f"{name}: {c}")
        items.append(item)
    meal_type = menu.meal_type.value if hasattr(menu.meal_type, "value") else menu.meal_type
    return {"date": str(menu.date), "meal_type": meal_type, "dishes": items,
            "totals": {k: round(v, 1) for k, v in totals.items()},
            "missing_dishes": missing, "warnings": warnings}


def meals_in_range(db: Session, user, d_from, d_to) -> list:
    menus = db.query(models.Menu).filter(models.Menu.date >= d_from, models.Menu.date <= d_to).order_by(models.Menu.date).all()
    dishes = _dish_map(db)
    return [meal_nutrition(db, m, user, dishes) for m in menus]


# ---------------------------------------------------------------- intake log

def _validate_date(d):
    today = today_local()
    if d > today:
        raise HTTPException(status_code=400, detail="You can't log food for a future date.")
    if d < today - timedelta(days=30):
        raise HTTPException(status_code=400, detail="You can only log food from the last 30 days.")


def add_intake(db: Session, user, payload) -> models.IntakeEntry:
    _validate_date(payload.date)

    if payload.source == "mess":
        if payload.meal_type == "snack":
            raise HTTPException(status_code=400, detail="Mess entries must be breakfast, lunch or dinner.")
        dup = db.query(models.IntakeEntry).filter(
            models.IntakeEntry.user_id == user.id, models.IntakeEntry.date == payload.date,
            models.IntakeEntry.meal_type == payload.meal_type, models.IntakeEntry.source == "mess").first()
        if dup:
            raise HTTPException(status_code=400, detail=f"You've already logged this {payload.meal_type}. Delete it first to change it.")
        menu = db.query(models.Menu).filter(models.Menu.date == payload.date, models.Menu.meal_type == payload.meal_type).first()
        if not menu or not menu.dishes:
            raise HTTPException(status_code=400, detail="There's no menu for that meal.")

        portion = payload.portion
        if portion is None:   # default to the portion the student confirmed, if any
            att = db.query(models.Attendance).filter(
                models.Attendance.user_id == user.id, models.Attendance.date == payload.date,
                models.Attendance.meal_type == payload.meal_type).first()
            portion = (att.portion if att and att.portion else "regular")
        factor = PORTION_MULTIPLIER[portion]
        meal = meal_nutrition(db, menu)
        if meal["missing_dishes"] and not meal["dishes"]:
            raise HTTPException(status_code=400, detail="This meal has no nutrition data yet. Ask the mess to add it.")
        entry = models.IntakeEntry(
            user_id=user.id, date=payload.date, meal_type=payload.meal_type, source="mess",
            description=", ".join(menu.dishes), portion=portion,
            **{k: round(meal["totals"][k] * factor, 1) for k in MACROS},
        )
    else:
        if not payload.description or not payload.description.strip():
            raise HTTPException(status_code=400, detail="Describe what you ate.")
        if payload.kcal is None:
            raise HTTPException(status_code=400, detail="Enter the calories (kcal).")
        entry = models.IntakeEntry(
            user_id=user.id, date=payload.date, meal_type=payload.meal_type, source="other",
            description=payload.description.strip(), kcal=payload.kcal,
            protein_g=payload.protein_g or 0, carbs_g=payload.carbs_g or 0, fat_g=payload.fat_g or 0,
        )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_intake(db: Session, user, entry_id: int):
    # filter by owner too: a student can never delete (or learn about) someone else's entry
    entry = db.query(models.IntakeEntry).filter(models.IntakeEntry.id == entry_id, models.IntakeEntry.user_id == user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
    db.delete(entry)
    db.commit()


def entry_to_dict(e: models.IntakeEntry) -> dict:
    return {"id": e.id, "date": str(e.date), "meal_type": e.meal_type, "source": e.source,
            "description": e.description, "portion": e.portion,
            **{k: getattr(e, k) for k in MACROS}}


def goal_for(db: Session, user) -> dict:
    g = db.query(models.NutritionGoal).filter(models.NutritionGoal.user_id == user.id).first()
    return {"kcal_target": g.kcal_target if g else None, "protein_target_g": g.protein_target_g if g else None}


def set_goal(db: Session, user, payload) -> dict:
    g = db.query(models.NutritionGoal).filter(models.NutritionGoal.user_id == user.id).first()
    if not g:
        g = models.NutritionGoal(user_id=user.id)
        db.add(g)
    g.kcal_target = payload.kcal_target
    g.protein_target_g = payload.protein_target_g
    db.commit()
    return goal_for(db, user)


def day_view(db: Session, user, day) -> dict:
    entries = db.query(models.IntakeEntry).filter(
        models.IntakeEntry.user_id == user.id, models.IntakeEntry.date == day
    ).order_by(models.IntakeEntry.created_at).all()
    totals = {k: round(sum(getattr(e, k) or 0 for e in entries), 1) for k in MACROS}

    logged = {e.meal_type for e in entries if e.source == "mess"}
    att = {a.meal_type.value: a for a in db.query(models.Attendance).filter(
        models.Attendance.user_id == user.id, models.Attendance.date == day).all()}
    dishes = _dish_map(db)
    loggable = []
    for meal in MEALS:
        menu = db.query(models.Menu).filter(models.Menu.date == day, models.Menu.meal_type == meal).first()
        if not menu:
            continue
        a = att.get(meal)
        n = meal_nutrition(db, menu, user, dishes)
        loggable.append({
            **n,
            "already_logged": meal in logged,
            "attendance": a.status.value if a else None,
            "confirmed_portion": (a.portion if a and a.portion else None),
        })
    return {"date": str(day), "entries": [entry_to_dict(e) for e in entries], "totals": totals,
            "goal": goal_for(db, user), "mess_meals": loggable}


def summary(db: Session, user, days: int = 7) -> dict:
    end = today_local()
    start = end - timedelta(days=days - 1)
    rows = db.query(models.IntakeEntry).filter(
        models.IntakeEntry.user_id == user.id, models.IntakeEntry.date >= start, models.IntakeEntry.date <= end).all()
    per_day = {}
    for i in range(days):
        d = start + timedelta(days=i)
        per_day[str(d)] = {"date": str(d), **{k: 0.0 for k in MACROS}, "mess_kcal": 0.0, "other_kcal": 0.0}
    for e in rows:
        row = per_day[str(e.date)]
        for k in MACROS:
            row[k] += getattr(e, k) or 0
        row["mess_kcal" if e.source == "mess" else "other_kcal"] += e.kcal or 0
    days_list = [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()} for r in per_day.values()]
    logged_days = [r for r in days_list if r["kcal"] > 0]
    avg = round(sum(r["kcal"] for r in logged_days) / len(logged_days)) if logged_days else None
    return {"days": days_list, "average_kcal_on_logged_days": avg, "days_logged": len(logged_days), "goal": goal_for(db, user)}


def seed_intake(db: Session, students, today):
    """Demo history: students log the mess meals they actually collected over the last week."""
    dishes = _dish_map(db)
    for s in students:
        for offset in range(-6, 1):
            d = today + timedelta(days=offset)
            for meal in MEALS:
                a = db.query(models.Attendance).filter(
                    models.Attendance.user_id == s.id, models.Attendance.date == d,
                    models.Attendance.meal_type == meal, models.Attendance.status == "will_eat").first()
                if not a or (offset == 0 and meal != "breakfast"):
                    continue
                menu = db.query(models.Menu).filter(models.Menu.date == d, models.Menu.meal_type == meal).first()
                if not menu:
                    continue
                n = meal_nutrition(db, menu, None, dishes)
                factor = PORTION_MULTIPLIER[a.portion or "regular"]
                db.add(models.IntakeEntry(user_id=s.id, date=d, meal_type=meal, source="mess",
                                          description=", ".join(menu.dishes), portion=a.portion or "regular",
                                          **{k: round(n["totals"][k] * factor, 1) for k in MACROS}))
            if offset in (-5, -2):
                db.add(models.IntakeEntry(user_id=s.id, date=d, meal_type="snack", source="other",
                                          description="Tea and biscuits", kcal=180, protein_g=3, carbs_g=28, fat_g=6))
    db.commit()

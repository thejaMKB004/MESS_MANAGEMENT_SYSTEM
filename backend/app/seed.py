"""Populate the database with demo data so the prototype is immediately explorable.
Run with:  python -m app.seed
"""
import random
from datetime import date, timedelta, datetime

from .database import SessionLocal, Base, engine
from . import models
from .security import hash_password
from .timeutil import today_local

Base.metadata.create_all(bind=engine)
db = SessionLocal()

random.seed(42)

DISHES = {
    "breakfast": ["Idli Sambar", "Poha", "Bread Omelette", "Upma"],
    "lunch": ["Rice & Dal", "Chicken Curry", "Paneer Butter Masala", "Curd Rice"],
    "dinner": ["Chapati & Sabzi", "Veg Biryani", "Egg Curry", "Khichdi"],
}
SKIP_REASONS = ["dont_like_menu", "eating_out", "not_on_campus", "not_hungry_health", "other"]
HOSTELS = ["Hostel A", "Hostel B", "Hostel C"]


def wipe():
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def seed():
    wipe()

    admin = models.User(
        name="Mess Admin", email="admin@mess.local", hashed_password=hash_password("admin123"),
        role="admin", hostel=None,
    )
    kitchen = models.User(
        name="Kitchen Staff", email="kitchen@mess.local", hashed_password=hash_password("kitchen123"),
        role="kitchen",
    )
    db.add_all([admin, kitchen])
    db.commit()

    students = []
    for i in range(1, 21):
        s = models.User(
            name=f"Student {i}",
            email=f"student{i}@mess.local",
            hashed_password=hash_password("student123"),
            roll_no=f"R{1000+i}",
            hostel=random.choice(HOSTELS),
            role="student",
            diet_restrictions=random.choice([[], ["vegetarian"], ["vegan"], []]),
            allergies=random.choice([[], [], ["peanuts"], ["gluten"]]),
        )
        students.append(s)
    db.add_all(students)
    db.commit()

    # inventory
    items = {
        "rice": models.InventoryItem(name="Rice", unit="kg", cost_per_unit=60, stock_qty=200),
        "dal": models.InventoryItem(name="Dal", unit="kg", cost_per_unit=110, stock_qty=80),
        "chicken": models.InventoryItem(name="Chicken", unit="kg", cost_per_unit=220, stock_qty=50),
        "paneer": models.InventoryItem(name="Paneer", unit="kg", cost_per_unit=320, stock_qty=20),
        "flour": models.InventoryItem(name="Wheat Flour", unit="kg", cost_per_unit=45, stock_qty=100),
        "veg_mix": models.InventoryItem(name="Mixed Vegetables", unit="kg", cost_per_unit=40, stock_qty=60),
    }
    db.add_all(items.values())
    db.commit()

    dish_links = [
        ("Rice & Dal", items["rice"], 0.15),
        ("Rice & Dal", items["dal"], 0.08),
        ("Chicken Curry", items["chicken"], 0.18),
        ("Paneer Butter Masala", items["paneer"], 0.12),
        ("Chapati & Sabzi", items["flour"], 0.1),
        ("Chapati & Sabzi", items["veg_mix"], 0.15),
        ("Veg Biryani", items["rice"], 0.2),
        ("Veg Biryani", items["veg_mix"], 0.18),
    ]
    for dish_name, item, qty in dish_links:
        db.add(models.DishIngredient(dish_name=dish_name, item_id=item.id, qty_per_serving=qty))
    db.commit()

    # menus + attendance + feedback for the past 14 days and next 3 days
    today = today_local()
    all_students = students
    for offset in range(-14, 4):
        d = today + timedelta(days=offset)
        for meal_type in ["breakfast", "lunch", "dinner"]:
            dish_choices = random.sample(DISHES[meal_type], k=2)
            menu = models.Menu(date=d, meal_type=meal_type, dishes=dish_choices, created_by=admin.id)
            db.add(menu)
            db.flush()

            if offset > 0:
                continue  # don't fabricate attendance for future days

            # make "Egg Curry" days on dinner artificially unpopular to feed the optimizer demo
            unpopular = meal_type == "dinner" and "Egg Curry" in dish_choices

            for student in all_students:
                skip_chance = 0.45 if unpopular else 0.2
                will_skip = random.random() < skip_chance
                if will_skip:
                    reason = "dont_like_menu" if unpopular and random.random() < 0.7 else random.choice(SKIP_REASONS)
                    att = models.Attendance(user_id=student.id, date=d, meal_type=meal_type, status="skip", reason=reason)
                else:
                    att = models.Attendance(
                        user_id=student.id, date=d, meal_type=meal_type, status="will_eat",
                        portion=random.choice(["half", "regular", "regular", "large"]),
                    )
                    db.add(att)
                    db.flush()
                    # ~80% of confirmed meals get an actual check-in (rest = no-show waste)
                    if random.random() < 0.8:
                        db.add(models.MealCheckin(attendance_id=att.id, method=random.choice(["qr", "manual"])))
                    continue
                db.add(att)

            db.flush()
            # feedback: a handful of students rate each dish
            for dish in dish_choices:
                for student in random.sample(all_students, k=6):
                    rating = random.randint(1, 2) if unpopular and dish == "Egg Curry" else random.randint(3, 5)
                    tags = ["too salty"] if rating <= 2 and random.random() < 0.5 else []
                    db.add(models.Feedback(
                        user_id=student.id, date=d, meal_type=meal_type, dish_name=dish,
                        rating=rating, tags=tags,
                    ))
    db.commit()

    # a few complaints with varying sentiment
    from .services.sentiment_service import score_sentiment
    complaint_texts = [
        ("hygiene", "high", "The dining hall floor was dirty and there was hair in my food, very unhygienic."),
        ("food_quality", "medium", "The rice was cold and bland today."),
        ("service", "low", "Serving was a bit slow but staff was friendly and helpful."),
        ("suggestion", "low", "It would be great to have fresh fruit at breakfast."),
    ]
    for i, (cat, sev, desc) in enumerate(complaint_texts):
        db.add(models.Complaint(
            user_id=all_students[i].id, category=cat, severity=sev, description=desc,
            sentiment_score=score_sentiment(desc),
            status="resolved" if i == 2 else "open",
        ))
    db.commit()


    # ------------------------------------------------------------------
    # NGO partners, kitchen logs and rescue history for the past 14 days
    # (example.org addresses are reserved for documentation, so no real inbox is ever emailed)
    # ------------------------------------------------------------------
    import math, secrets
    from datetime import time as dtime
    from .config import MEAL_START_TIMES

    ngos = [
        models.NGOPartner(name="Annapurna Food Bank", contact_person="R. Menon", email="annapurna@example.org", phone="+91 90000 00001", area="City centre", active=True),
        models.NGOPartner(name="Hope Kitchen Trust", contact_person="S. Iyer", email="hope@example.org", phone="+91 90000 00002", area="Station road", active=True),
        models.NGOPartner(name="Seva Shelter", contact_person="A. Khan", email="seva@example.org", phone="+91 90000 00003", area="Old town", active=False),
    ]
    db.add_all(ngos)
    db.commit()

    used_codes = set()
    for offset in range(-14, 0):
        d = today + timedelta(days=offset)
        for meal_type in ["breakfast", "lunch", "dinner"]:
            confirmed = db.query(models.Attendance).filter(
                models.Attendance.date == d, models.Attendance.meal_type == meal_type,
                models.Attendance.status == "will_eat").count()
            checked = db.query(models.MealCheckin).join(models.Attendance).filter(
                models.Attendance.date == d, models.Attendance.meal_type == meal_type).count()
            served = checked + random.randint(0, 3)                      # a few unconfirmed walk-ins
            cooked = max(served, int(confirmed * random.uniform(1.0, 1.35)) + random.randint(0, 3))
            leftover = cooked - served
            reason = None
            if leftover >= max(3, int(0.1 * cooked)):
                reason = random.choice(["over_production", "over_production", "unpopular_dish", "low_turnout"])
            db.add(models.KitchenLog(
                date=d, meal_type=meal_type, cooked_portions=cooked, served_portions=served, leftover_portions=leftover,
                recommended_portions=math.ceil(confirmed * 1.05), waste_reason=reason, logged_by=kitchen.id,
            ))

            if leftover >= 4 and meal_type != "breakfast":
                menu = db.query(models.Menu).filter(models.Menu.date == d, models.Menu.meal_type == meal_type).first()
                cooked_at = datetime.combine(d, dtime(MEAL_START_TIMES[meal_type] + 2, 0))
                listing = models.SurplusListing(
                    date=d, meal_type=meal_type, dish_description=", ".join(menu.dishes) if menu else "Leftover meal",
                    portions_total=leftover, portions_remaining=0, cooked_at=cooked_at,
                    safe_until=cooked_at + timedelta(hours=3), student_window_ends=cooked_at + timedelta(minutes=30),
                    held_safely=True, status="closed", created_by=kitchen.id, created_at=cooked_at,
                )
                db.add(listing)
                db.flush()
                claimed = random.randint(0, min(5, leftover))
                for student in random.sample(all_students, k=claimed):
                    code = secrets.token_hex(3).upper()
                    while code in used_codes:
                        code = secrets.token_hex(3).upper()
                    used_codes.add(code)
                    db.add(models.SurplusClaim(
                        listing_id=listing.id, user_id=student.id, portions=1, code=code, status="picked_up",
                        expires_at=cooked_at + timedelta(minutes=30), created_at=cooked_at, picked_up_at=cooked_at + timedelta(minutes=10)))
                remaining = leftover - claimed
                if remaining > 0 and random.random() < 0.7:
                    db.add(models.Donation(
                        listing_id=listing.id, ngo_id=random.choice(ngos[:2]).id, portions=remaining, status="picked_up",
                        token=secrets.token_urlsafe(8), portions_picked=remaining, offered_at=cooked_at + timedelta(minutes=30),
                        responded_at=cooked_at + timedelta(minutes=45), picked_up_at=cooked_at + timedelta(minutes=80)))
    db.commit()

    from .services.nutrition_service import ensure_defaults, seed_intake
    ensure_defaults(db)
    seed_intake(db, all_students[:8], today)

    print("Seed complete.")
    print("Admin login:   admin@mess.local / admin123")
    print("Kitchen login: kitchen@mess.local / kitchen123")
    print("NGO partners seeded: 2 active, 1 inactive (example.org addresses).")
    print("Student login: student1@mess.local ... student20@mess.local / student123")


if __name__ == "__main__":
    seed()
    db.close()

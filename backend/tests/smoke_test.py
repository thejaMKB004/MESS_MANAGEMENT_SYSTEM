"""End-to-end check of the kitchen log, surplus rescue and automation features.

Run from the backend folder (needs: pip install -r requirements-dev.txt):
    python -m tests.smoke_test

It uses a throwaway database (test_tmp.db), so your real mess.db is never touched.
Time-dependent behaviour is tested by passing a fake `now` to the services, so there is no waiting.
"""
import os
import sys
from datetime import timedelta, time as dtime, datetime

os.environ["DATABASE_URL"] = "sqlite:///./test_tmp.db"
os.environ["AUTOMATION_ENABLED"] = "false"
if os.path.exists("test_tmp.db"):
    os.remove("test_tmp.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import seed, models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import surplus_service, automation_service  # noqa: E402
from app.timeutil import now_local, today_local  # noqa: E402

passed = 0


def check(label, condition, extra=""):
    global passed
    if not condition:
        print(f"FAIL: {label} {extra}")
        sys.exit(1)
    passed += 1
    print(f"  ok  {label}")


seed.seed()
client = TestClient(app)


def login(email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


kitchen, admin = login("kitchen@mess.local", "kitchen123"), login("admin@mess.local", "admin123")
s1, s2, s3 = (login(f"student{i}@mess.local", "student123") for i in (1, 2, 3))
today = str(today_local())

print("Kitchen log and cooking sheet")
r = client.get(f"/kitchen/cooking-sheet?date={today}&meal_type=lunch", headers=kitchen)
check("cooking sheet returns a recommendation", r.status_code == 200 and r.json()["recommended_portions"] > 0, r.text)
check("student cannot read the cooking sheet", client.get(f"/kitchen/cooking-sheet?date={today}&meal_type=lunch", headers=s1).status_code == 403)
check("bad meal type is rejected", client.get(f"/kitchen/cooking-sheet?date={today}&meal_type=brunch", headers=kitchen).status_code == 422)

bad = client.put("/kitchen/logs", headers=kitchen, json={"date": today, "meal_type": "lunch", "cooked_portions": 50, "served_portions": 60})
check("served > cooked is rejected", bad.status_code == 400)
future = str(today_local() + timedelta(days=2))
check("future date is rejected", client.put("/kitchen/logs", headers=kitchen, json={"date": future, "meal_type": "lunch", "cooked_portions": 5, "served_portions": 1}).status_code == 400)

r = client.put("/kitchen/logs", headers=kitchen, json={"date": today, "meal_type": "lunch", "cooked_portions": 80, "served_portions": 65, "waste_reason": "over_production"})
check("log saved with leftover computed", r.status_code == 200 and r.json()["leftover_portions"] == 15, r.text)
check("over-production % is calculated", r.json()["over_production_pct"] is not None)

print("Surplus rescue: listing and last call")
no_confirm = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "lunch", "dish_description": "Rice and dal", "portions": 10, "held_safely": False})
check("listing needs the food-safety confirmation", no_confirm.status_code == 400)
too_many = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "lunch", "dish_description": "Rice and dal", "portions": 99, "held_safely": True})
check("can't list more than the leftover", too_many.status_code == 400)
old_food = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "lunch", "dish_description": "Rice and dal", "portions": 5, "held_safely": True, "cooked_minutes_ago": 200})
check("food past its safe window is refused", old_food.status_code == 400, old_food.text)

r = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "lunch", "dish_description": "Rice and dal", "portions": 10, "held_safely": True})
check("listing created", r.status_code == 200 and r.json()["status"] == "open_students", r.text)
listing_id = r.json()["id"]
inbox = client.get("/notifications/mine", headers=s1).json()
check("students get a last-call notification", any(n["kind"] == "last_call" for n in inbox["items"]) and inbox["unread"] >= 1)
check("open listing is visible to students", any(l["id"] == listing_id for l in client.get("/surplus/open", headers=s1).json()))

impact_before = client.get("/impact/me", headers=s1).json()["meals_rescued"]
print("Claims and counter pickup")
c1 = client.post(f"/surplus/listings/{listing_id}/claim", headers=s1, json={"portions": 1})
check("student claims a portion and gets a code", c1.status_code == 200 and len(c1.json()["code"]) == 6, c1.text)
check("per-student limit is enforced", client.post(f"/surplus/listings/{listing_id}/claim", headers=s1, json={"portions": 1}).status_code == 400)
c2 = client.post(f"/surplus/listings/{listing_id}/claim", headers=s2, json={"portions": 1})
check("second student can claim", c2.status_code == 200)
check("kitchen staff cannot claim as a student", client.post(f"/surplus/listings/{listing_id}/claim", headers=kitchen, json={"portions": 1}).status_code == 403)
check("wrong code is rejected", client.post("/surplus/claims/pickup", headers=kitchen, json={"code": "ZZZZZZ"}).status_code == 404)
p = client.post("/surplus/claims/pickup", headers=kitchen, json={"code": c1.json()["code"].lower()})
check("pickup with the code works (case-insensitive)", p.status_code == 200, p.text)
check("a code can't be used twice", client.post("/surplus/claims/pickup", headers=kitchen, json={"code": c1.json()["code"]}).status_code == 400)

print("Clock jumps forward: student window ends, listing goes to NGOs")
db = SessionLocal()
listing = db.get(models.SurplusListing, listing_id)
after_window = listing.student_window_ends + timedelta(minutes=1)
try:
    surplus_service.claim(db, db.get(models.User, 5), listing_id, 1, now=after_window)
    check("late claim refused", False)
except Exception as e:
    check("late claim refused", "closed" in str(e.detail))

out = surplus_service.maintenance(db, now=after_window)
check("automation escalates the leftovers to NGOs", out["listings_escalated"] == 1, str(out))
db.expire_all()
listing = db.get(models.SurplusListing, listing_id)
check("listing is now offered_ngo", listing.status == "offered_ngo")
offers = [d for d in listing.donations]
check("only active NGOs were offered the food", len(offers) == 2 and all(d.status == "offered" for d in offers))

ob = client.get("/notifications/outbox", headers=admin).json()
offer_mail = [n for n in ob if n["kind"] == "donation_offer"]
check("outbox holds the NGO emails with response links", len(offer_mail) == 2 and "/ngo/respond/" in offer_mail[0]["link"])
check("email is 'skipped' when SMTP isn't configured", offer_mail[0]["email_status"] == "skipped")

print("NGO responds with no login")
tok_a, tok_b = offers[0].token, offers[1].token
v = client.get(f"/public/donations/{tok_a}")
check("NGO can view the offer from the link", v.status_code == 200 and v.json()["portions"] == listing.portions_remaining)
check("invalid link gives 404", client.get("/public/donations/not-a-token").status_code == 404)
acc = client.post(f"/public/donations/{tok_a}/respond", json={"action": "accept"})
check("first NGO accepts", acc.status_code == 200 and acc.json()["status"] == "accepted", acc.text)
late = client.post(f"/public/donations/{tok_b}/respond", json={"action": "accept"})
check("second NGO is too late (first to accept wins)", late.status_code == 400)
check("kitchen is notified of the acceptance", any(n["kind"] == "donation_accepted" for n in client.get("/notifications/mine", headers=kitchen).json()["items"]))

don_id = offers[0].id
pk = client.post(f"/donations/{don_id}/pickup", headers=kitchen, json={})
check("kitchen records the pickup", pk.status_code == 200, pk.text)
db.expire_all()
check("listing closes once everything is handed over", db.get(models.SurplusListing, listing_id).status == "closed")

print("Real waste accounting")
rw = client.get(f"/analytics/real-waste?from={today}&to={today}", headers=admin).json()
# 15 left over, 10 listed. Student 2 never collected, so that portion went back and was donated (9 to the NGO).
# The 5 never listed count as waste: wasted = leftover - rescued = 15 - (1 + 9).
check("leftover 15, rescued 1 by a student + 9 by the NGO, wasted 5",
      rw["leftover"] == 15 and rw["rescued_by_students"] == 1 and rw["rescued_by_ngos"] == 9 and rw["wasted"] == 5, str(rw))
imp = client.get("/impact/me", headers=s1).json()
check("student's impact page counts the newly rescued meal", imp["meals_rescued"] == impact_before + 1, str(imp))

print("Expiry: unsafe food is never left on offer")
client.put("/kitchen/logs", headers=kitchen, json={"date": today, "meal_type": "dinner", "cooked_portions": 40, "served_portions": 30})
r2 = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "dinner", "dish_description": "Veg biryani", "portions": 6, "held_safely": True})
l2 = r2.json()["id"]
cl = client.post(f"/surplus/listings/{l2}/claim", headers=s3, json={"portions": 1}).json()
t_late = now_local() + timedelta(hours=4)
out = surplus_service.maintenance(db, now=t_late)
db.expire_all()
check("unclaimed hold expired and listing expired after the safe window", out["claims_expired"] == 1 and out["listings_expired"] == 1, str(out))
check("expired claim code no longer works", client.post("/surplus/claims/pickup", headers=kitchen, json={"code": cl["code"]}).status_code == 400)

print("Automation jobs with a fake clock")
d0 = today_local()
lunch_deadline = datetime.combine(d0, dtime(0, 0)) + timedelta(hours=11)      # lunch 13:00 minus 2h
res = automation_service.job_cooking_sheets(db, lunch_deadline + timedelta(minutes=1))
check("cooking sheet is sent right after the deadline", any(r["meal"] == "lunch" for r in res), str(res))
again = automation_service.job_cooking_sheets(db, lunch_deadline + timedelta(minutes=2))
check("the same job does NOT run twice (idempotent)", not any(r["meal"] == "lunch" for r in again), str(again))
check("kitchen received the cooking sheet", any(n["kind"] == "cooking_sheet" for n in client.get("/notifications/mine", headers=kitchen).json()["items"]))

early = automation_service.job_cooking_sheets(db, lunch_deadline - timedelta(hours=3))
check("nothing is sent before the deadline", not any(r["meal"] == "lunch" for r in early))

# reminders only go to students who haven't answered
dinner_deadline = datetime.combine(d0, dtime(0, 0)) + timedelta(hours=18)
db.query(models.Attendance).filter(models.Attendance.date == d0, models.Attendance.meal_type == "dinner", models.Attendance.user_id == 7).delete()
db.commit()
res = automation_service.job_deadline_reminders(db, dinner_deadline - timedelta(minutes=30))
dinner = [r for r in res if r["meal"] == "dinner"]
check("reminder goes only to students who haven't answered", dinner and 1 <= dinner[0]["reminded"] < 20, str(res))

forced = automation_service.run_all(db, force=True)
check("'Run now' (force) triggers every job", {"deadline_reminder", "cooking_sheet", "low_stock", "weekly_report"} <= set(forced), str(list(forced)))
check("weekly report was stored", db.query(models.Report).count() >= 1)
runs = client.get("/automation/runs", headers=admin).json()
check("every run is logged", len(runs) >= 5)
check("students can't see automation logs", client.get("/automation/runs", headers=s1).status_code == 403)


print("Bug-fix regression checks")
import threading
from datetime import timedelta as _td

# public sign-up can never create staff
r = client.post("/auth/register", json={"name": "Mallory", "email": "m@x.com", "password": "pw12345", "role": "admin"})
check("public sign-up ignores a requested admin role", r.status_code == 200 and r.json()["role"] == "student", r.text)
staff_body = {"name": "Cook", "email": "cook@x.com", "password": "pw12345", "role": "kitchen"}
check("a student cannot create staff accounts", client.post("/auth/staff", headers=s1, json=staff_body).status_code == 403)
check("an admin can create a kitchen account", client.post("/auth/staff", headers=admin, json=staff_body).json()["role"] == "kitchen")

# viewing the weekly report must not write to the database
n_before = db.query(models.Report).count()
for _ in range(3):
    client.get(f"/analytics/weekly-report?week_start={d0 - _td(days=7)}", headers=admin)
db.expire_all()
check("viewing the weekly report does not store new rows", db.query(models.Report).count() == n_before)

# check-in only for today's meals
old = db.query(models.Attendance).filter(models.Attendance.date == d0 - _td(days=5), models.Attendance.status == "will_eat").first()
for ci in db.query(models.MealCheckin).filter(models.MealCheckin.attendance_id == old.id).all():
    db.delete(ci)
db.commit()
check("check-in of an old meal is refused", client.post("/attendance/checkin", headers=kitchen, json={"attendance_id": old.id}).status_code == 400)
mine = db.query(models.Attendance).filter(models.Attendance.date == d0, models.Attendance.status == "will_eat").first()
for ci in db.query(models.MealCheckin).filter(models.MealCheckin.attendance_id == mine.id).all():
    db.delete(ci)
db.commit()
check("check-in of today's meal still works", client.post("/attendance/checkin", headers=kitchen, json={"attendance_id": mine.id}).status_code == 200)

# nonsense values are rejected with a clear 422
check("unknown complaint severity is rejected", client.post("/complaints", headers=s1, json={"category": "x", "severity": "banana", "description": "t"}).status_code == 422)
tomorrow = str(d0 + _td(days=1))
check("unknown portion size is rejected", client.post("/attendance/confirm", headers=s1, json={"date": tomorrow, "meal_type": "lunch", "status": "will_eat", "portion": "gigantic"}).status_code == 422)

# the race: many students claim ONE portion at the same moment; exactly one may win
for run in range(3):
    lid = client.post("/surplus/listings", headers=kitchen, json={"date": today, "meal_type": "lunch", "dish_description": f"Race {run}", "portions": 1, "held_safely": True}).json()["id"]
    ids = [u.id for u in db.query(models.User).filter(models.User.role == "student").limit(10).all()]
    won, gate = [], threading.Barrier(len(ids), timeout=20)
    def go(uid):
        sess = SessionLocal()
        try:
            gate.wait()
            surplus_service.claim(sess, sess.get(models.User, uid), lid, 1)
            won.append(uid)
        except Exception:
            pass
        finally:
            sess.close()
    th = [threading.Thread(target=go, args=(i,), daemon=True) for i in ids]
    [t.start() for t in th]
    [t.join(timeout=40) for t in th]
    db.expire_all()
    check(f"race {run + 1}: 10 students, 1 portion, exactly 1 winner", len(won) == 1 and db.get(models.SurplusListing, lid).portions_remaining == 0, f"winners={len(won)}")


print("Nutrition: dish data, meal totals, warnings, intake log")
nd = client.get("/nutrition/dishes", headers=s1).json()
check("every seeded dish has nutrition data", nd and all(d["has_data"] for d in nd), str([d["dish_name"] for d in nd if not d["has_data"]]))
check("a student cannot edit dish nutrition", client.put("/nutrition/dishes/Poha", headers=s1, json={"kcal": 1}).status_code == 403)
r = client.put("/nutrition/dishes/Test Soup", headers=kitchen, json={"kcal": 150, "protein_g": 5, "allergens": ["dairy"]})
check("kitchen can add a new dish's nutrition", r.status_code == 200 and r.json()["kcal"] == 150, r.text)
check("unknown allergen is rejected", client.put("/nutrition/dishes/Test Soup", headers=kitchen, json={"kcal": 150, "allergens": ["glitter"]}).status_code == 422)

# a meal we control: tomorrow lunch = Rice & Dal + Curd Rice
tom = d0 + _td(days=1)
tm = db.query(models.Menu).filter(models.Menu.date == tom, models.Menu.meal_type == "lunch").first()
tm.dishes = ["Rice & Dal", "Curd Rice"]
db.commit()
meals = client.get(f"/nutrition/meals?from={tom}&to={tom}", headers=s1).json()
lunch = next(m for m in meals if m["meal_type"] == "lunch")
check("meal total = sum of its dishes (420 + 320 kcal)", lunch["totals"]["kcal"] == 740, str(lunch["totals"]))

# warnings come from the student's own profile
client.patch("/users/me", headers=s2, json={"allergies": ["dairy"], "diet_restrictions": []})
w = next(m for m in client.get(f"/nutrition/meals?from={tom}&to={tom}", headers=s2).json() if m["meal_type"] == "lunch")["warnings"]
check("dairy allergy flags Curd Rice", any("Curd Rice" in x and "dairy" in x for x in w), str(w))
client.patch("/users/me", headers=s3, json={"diet_restrictions": ["vegetarian"], "allergies": []})
egg_menu = db.query(models.Menu).filter(models.Menu.date == tom, models.Menu.meal_type == "dinner").first()
egg_menu.dishes = ["Egg Curry", "Khichdi"]
db.commit()
w = next(m for m in client.get(f"/nutrition/meals?from={tom}&to={tom}", headers=s3).json() if m["meal_type"] == "dinner")["warnings"]
check("vegetarian is warned about Egg Curry", any("Egg Curry" in x for x in w) and not any("Khichdi" in x for x in w), str(w))

# intake log (today's breakfast)
bm = db.query(models.Menu).filter(models.Menu.date == d0, models.Menu.meal_type == "breakfast").first()
bm.dishes = ["Poha", "Upma"]                          # 270 + 280 = 550
db.commit()
for e in db.query(models.IntakeEntry).filter(models.IntakeEntry.user_id == 3, models.IntakeEntry.date == d0).all():
    db.delete(e)
db.commit()
r = client.post("/nutrition/intake", headers=s1, json={"date": today, "meal_type": "breakfast", "source": "mess", "portion": "large"})
check("logging a large mess breakfast gives 1.5 x 550 = 825 kcal", r.status_code == 200 and r.json()["kcal"] == 825, r.text)
entry_id = r.json()["id"]
check("logging the same meal twice is refused", client.post("/nutrition/intake", headers=s1, json={"date": today, "meal_type": "breakfast", "source": "mess"}).status_code == 400)
check("future dates are refused", client.post("/nutrition/intake", headers=s1, json={"date": str(tom), "meal_type": "lunch", "source": "mess"}).status_code == 400)
check("other food needs calories", client.post("/nutrition/intake", headers=s1, json={"date": today, "meal_type": "snack", "source": "other", "description": "Samosa"}).status_code == 400)
r = client.post("/nutrition/intake", headers=s1, json={"date": today, "meal_type": "snack", "source": "other", "description": "Samosa", "kcal": 260, "fat_g": 15})
check("other food is logged", r.status_code == 200)
day = client.get(f"/nutrition/intake?date={today}", headers=s1).json()
check("day total adds mess + other (825 + 260)", day["totals"]["kcal"] == 1085, str(day["totals"]))
check("breakfast shows as already logged", next(m for m in day["mess_meals"] if m["meal_type"] == "breakfast")["already_logged"])

# history keeps its values if the dish data changes later
client.put("/nutrition/dishes/Poha", headers=kitchen, json={"kcal": 999})
day = client.get(f"/nutrition/intake?date={today}", headers=s1).json()
check("editing a dish later does not rewrite past entries", day["totals"]["kcal"] == 1085)

# one student cannot touch another student's log
check("another student cannot delete my entry", client.delete(f"/nutrition/intake/{entry_id}", headers=s2).status_code == 404)
check("I can delete my own entry", client.delete(f"/nutrition/intake/{entry_id}", headers=s1).status_code == 200)

# goal limits and the weekly summary
check("a target below 1200 kcal is refused", client.put("/nutrition/goal", headers=s1, json={"kcal_target": 600}).status_code == 422)
check("a normal target is saved", client.put("/nutrition/goal", headers=s1, json={"kcal_target": 2200}).json()["kcal_target"] == 2200)
sm = client.get("/nutrition/summary?days=7", headers=s1).json()
check("7-day summary has 7 days and today's 260 kcal", len(sm["days"]) == 7 and sm["days"][-1]["kcal"] == 260, str(sm["days"][-1]))

db.close()
os.remove("test_tmp.db")
print(f"\nALL {passed} CHECKS PASSED")

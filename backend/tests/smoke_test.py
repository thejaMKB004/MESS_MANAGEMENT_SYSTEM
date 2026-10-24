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

db.close()
os.remove("test_tmp.db")
print(f"\nALL {passed} CHECKS PASSED")

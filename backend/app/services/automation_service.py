"""Automation: background jobs that run without anyone clicking.

How it works
  * A small thread (started in main.py) calls run_all() every AUTOMATION_TICK_SECONDS.
  * Each job checks "is it time?" against the mess's local clock and then runs at most once per
    (job, run_key). The AutomationRun table has a unique constraint on that pair, so even if the
    server restarts or two workers run, a reminder can never be sent twice.
  * `now` and `force` are parameters so the logic can be tested with a fake clock and triggered
    on demand from the admin Automation page.
"""
import logging
import threading
from datetime import timedelta, date as date_cls
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..config import (
    AUTOMATION_TICK_SECONDS, REMINDER_MINUTES_BEFORE_DEADLINE, LOW_STOCK_CHECK_HOUR,
    WEEKLY_REPORT_HOUR, EMAIL_STUDENT_REMINDERS,
)
from ..database import SessionLocal
from ..timeutil import now_local, meal_deadline
from . import notification_service as notif
from . import kitchen_service, surplus_service
from .anomaly_service import detect_anomalies
from .report_service import build_weekly_report

log = logging.getLogger("automation")
MEALS = ["breakfast", "lunch", "dinner"]

JOBS_INFO = {
    "deadline_reminder": "Reminds students who haven't answered, shortly before the confirmation deadline.",
    "cooking_sheet": "When the deadline passes, sends the kitchen and admin how much to cook.",
    "anomaly_alert": "After the deadline, alerts the admin if the skip rate is unusually high or low.",
    "low_stock": "Each evening, checks tomorrow's menu against stock and warns about shortages.",
    "weekly_report": "Every Monday morning, builds last week's report and sends it to the admin.",
    "surplus_maintenance": "Every tick: expires unclaimed holds, offers leftovers to NGOs, expires unsafe food.",
}


def _day(d):
    return d.strftime("%d %b")


def _ran(db, job, key) -> bool:
    return db.query(models.AutomationRun).filter(
        models.AutomationRun.job == job, models.AutomationRun.run_key.in_([key, key + ":error"])
    ).first() is not None


def _record(db, job, key, status, details, now):
    db.add(models.AutomationRun(job=job, run_key=key, status=status, details=details, ran_at=now))
    db.commit()


def _run_once(db, job, key, work, now, force=False):
    """Run work() unless this (job, key) already ran. Everything work() changed commits together with the log row."""
    if force:
        key = f"{key}|manual|{now.isoformat()}"
    elif _ran(db, job, key):
        return None
    try:
        details = work()
        _record(db, job, key, "ok", details, now)
        return {"job": job, **details}
    except Exception as exc:
        db.rollback()
        log.exception("Job %s failed", job)
        _record(db, job, key if force else key + ":error", "error", {"error": str(exc)}, now)
        return {"job": job, "error": str(exc)}


def _jsonable(d: dict) -> dict:
    return {k: (str(v) if isinstance(v, date_cls) else v) for k, v in d.items()}


# ----------------------------------------------------------------- jobs

def job_deadline_reminders(db, now, force=False):
    results, today = [], now.date()
    for meal in MEALS:
        deadline = meal_deadline(today, meal)
        in_window = deadline - timedelta(minutes=REMINDER_MINUTES_BEFORE_DEADLINE) <= now < deadline
        if not (force or in_window):
            continue

        def work(meal=meal, deadline=deadline):
            answered = {uid for (uid,) in db.query(models.Attendance.user_id).filter(
                models.Attendance.date == today, models.Attendance.meal_type == meal)}
            targets = [s for s in db.query(models.User).filter(models.User.role == "student").all() if s.id not in answered]
            notif.notify_users(
                db, targets, "reminder", f"Confirm {meal} by {deadline.strftime('%I:%M %p').lstrip('0')}",
                "Tell the mess if you'll eat or skip so the kitchen cooks the right amount.", link="/",
                email=EMAIL_STUDENT_REMINDERS,
            )
            return {"meal": meal, "reminded": len(targets)}

        res = _run_once(db, "deadline_reminder", f"{today}:{meal}", work, now, force)
        if res:
            results.append(res)
    return results


def job_cooking_sheets(db, now, force=False):
    results, today = [], now.date()
    for meal in MEALS:
        deadline = meal_deadline(today, meal)
        if not (force or deadline <= now < deadline + timedelta(hours=6)):
            continue

        def work(meal=meal):
            sheet = kitchen_service.cooking_sheet(db, today, meal, now)
            diet = ", ".join(f"{n} {k}" for k, n in sheet["diet_counts"].items()) or "none recorded"
            allergy = ", ".join(f"{n} {k}" for k, n in sheet["allergy_counts"].items()) or "none recorded"
            body = (f"Cook about {sheet['recommended_portions']} portions.\n"
                    f"Confirmed: {sheet['confirmed_will_eat']} students ({sheet['confirmed_portion_units']} portion units), "
                    f"guests: {sheet['guests']}, expected walk-ins: {sheet['expected_walkins']} "
                    f"(from {sheet['not_responded']} who didn't answer), buffer {sheet['buffer_pct']:g}%.\n"
                    f"Diets: {diet}. Allergies: {allergy}.")
            notif.notify_roles(db, ["kitchen", "admin"], "cooking_sheet",
                               f"Cooking sheet: {meal} {_day(today)}", body, link="/kitchen",
                               payload=_jsonable({k: v for k, v in sheet.items() if k != "deadline"}))
            return {"meal": meal, "recommended": sheet["recommended_portions"]}

        res = _run_once(db, "cooking_sheet", f"{today}:{meal}", work, now, force)
        if res:
            results.append(res)
    return results


def job_anomaly_alerts(db, now, force=False):
    results, today = [], now.date()
    for meal in MEALS:
        deadline = meal_deadline(today, meal)
        if not (force or deadline <= now < deadline + timedelta(hours=6)):
            continue

        def work(meal=meal):
            found = [_jsonable(a) for a in detect_anomalies(db, today) if a["meal_type"] == meal]
            for a in found:
                rate, usual = round(a["today_skip_rate"] * 100), round(a["avg_skip_rate"] * 100)
                if a["alert"] == "high_skip_spike":
                    title = f"More skips than usual for {meal} on {_day(today)}"
                    advice = "Check the menu, or whether there's a campus event."
                else:
                    title = f"Fewer skips than usual for {meal} on {_day(today)}"
                    advice = "Expect more people than usual and consider cooking a little extra."
                notif.notify_roles(
                    db, ["admin"], "anomaly", title,
                    f"Skip rate is {rate}% against a usual {usual}%. {advice}", link="/", payload=a, email=True)
            return {"meal": meal, "anomalies": len(found)}

        res = _run_once(db, "anomaly_alert", f"{today}:{meal}", work, now, force)
        if res:
            results.append(res)
    return results


def _estimate_servings(db, meal, today) -> int:
    rows = db.query(models.Attendance.date, func.count(models.Attendance.id)).filter(
        models.Attendance.meal_type == meal, models.Attendance.status == models.AttendanceStatus.will_eat,
        models.Attendance.date >= today - timedelta(days=7), models.Attendance.date < today,
    ).group_by(models.Attendance.date).all()
    return round(sum(c for _, c in rows) / len(rows)) if rows else 0


def job_low_stock(db, now, force=False):
    if not force and now.hour < LOW_STOCK_CHECK_HOUR:
        return None
    tomorrow = now.date() + timedelta(days=1)

    def work():
        need = {}
        for meal in MEALS:
            menu = db.query(models.Menu).filter(models.Menu.date == tomorrow, models.Menu.meal_type == meal).first()
            servings = _estimate_servings(db, meal, now.date())
            if not menu or not servings:
                continue
            for dish in menu.dishes:
                for link in db.query(models.DishIngredient).filter(models.DishIngredient.dish_name == dish).all():
                    row = need.setdefault(link.item.name, {"unit": link.item.unit, "need": 0.0, "stock": link.item.stock_qty})
                    row["need"] += link.qty_per_serving * servings
        short = {n: r for n, r in need.items() if r["need"] > r["stock"]}
        if short:
            lines = [f"{n}: need {r['need']:.1f} {r['unit']}, have {r['stock']:.1f} (short {r['need'] - r['stock']:.1f})" for n, r in short.items()]
            notif.notify_roles(db, ["admin"], "low_stock", f"Stock shortfall for {_day(tomorrow)}",
                               "Order before tomorrow:\n" + "\n".join(lines), link="/inventory", email=True)
        return {"for_date": str(tomorrow), "items_short": len(short)}

    return _run_once(db, "low_stock", str(tomorrow), work, now, force)


def job_weekly_report(db, now, force=False):
    if not force and not (now.weekday() == 0 and now.hour >= WEEKLY_REPORT_HOUR):
        return None
    week_start = now.date() - timedelta(days=7)

    def work():
        summary = build_weekly_report(db, week_start)
        db.add(models.Report(week_start=week_start, summary=summary))
        k = summary["kitchen"]
        body = (f"Week of {_day(week_start)}\n"
                f"Cooked {k['cooked']}, served {k['served']}, leftover {k['leftover']}, rescued {k['rescued_total']}, wasted {k['wasted']} "
                f"(about Rs {k['waste_cost_inr']:.0f}).\n"
                f"Complaints: {summary['complaints_received']} received, {summary['complaints_resolved']} resolved.")
        notif.notify_roles(db, ["admin"], "weekly_report", f"Weekly report: {_day(week_start)}", body, link="/analytics", email=True)
        return {"week_start": str(week_start), "wasted": k["wasted"], "rescued": k["rescued_total"]}

    return _run_once(db, "weekly_report", str(week_start), work, now, force)


def job_surplus_maintenance(db, now, force=False):
    result = surplus_service.maintenance(db, now)
    actions = {k: v for k, v in result.items() if k != "escalation_skipped"}
    if any(actions.values()):
        _record(db, "surplus_maintenance", now.isoformat(), "ok", actions, now)
        return {"job": "surplus_maintenance", **actions}
    return None


JOB_FUNCS = {
    "surplus_maintenance": job_surplus_maintenance,
    "deadline_reminder": job_deadline_reminders,
    "cooking_sheet": job_cooking_sheets,
    "anomaly_alert": job_anomaly_alerts,
    "low_stock": job_low_stock,
    "weekly_report": job_weekly_report,
}


def run_job(db: Session, name: str, now=None, force=False):
    return JOB_FUNCS[name](db, now or now_local(), force)


def run_all(db: Session, now=None, force=False) -> dict:
    now = now or now_local()
    out = {}
    for name, fn in JOB_FUNCS.items():
        res = fn(db, now, force)
        if res:
            out[name] = res
    return out


# ----------------------------------------------------------------- background loop

_stop = threading.Event()
_thread = None


def _loop():
    while not _stop.is_set():
        db = SessionLocal()
        try:
            run_all(db)
        except Exception:
            log.exception("Automation tick failed")
        finally:
            db.close()
        _stop.wait(AUTOMATION_TICK_SECONDS)


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="automation", daemon=True)
    _thread.start()
    log.info("Automation started (tick every %ss)", AUTOMATION_TICK_SECONDS)


def stop():
    _stop.set()

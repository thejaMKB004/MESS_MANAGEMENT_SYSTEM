import math
from collections import Counter
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..config import (
    PORTION_MULTIPLIER, NON_RESPONDER_EAT_RATE, COOKING_BUFFER_PCT, DEFAULT_PORTION_COST_INR,
)
from ..timeutil import now_local, today_local, meal_deadline
from .surplus_service import listing_outcome


def _mt(value):
    return value.value if hasattr(value, "value") else value


def cooking_sheet(db: Session, target_date, meal_type: str, now=None) -> dict:
    """How much to cook. Confirmed students (weighted by portion size) + guests + an estimate for students who
    never answered, plus a safety buffer. A transparent formula, not ML, so the kitchen can see why."""
    now = now or now_local()
    rows = db.query(models.Attendance).filter(
        models.Attendance.date == target_date, models.Attendance.meal_type == meal_type
    ).all()
    will_eat = [r for r in rows if r.status == models.AttendanceStatus.will_eat]
    skipped = [r for r in rows if r.status == models.AttendanceStatus.skip]

    portion_counts = Counter((r.portion or "regular") for r in will_eat)
    confirmed_units = sum(PORTION_MULTIPLIER.get(r.portion or "regular", 1.0) for r in will_eat)
    guests = sum(g.count for g in db.query(models.GuestBooking).filter(
        models.GuestBooking.date == target_date, models.GuestBooking.meal_type == meal_type).all())

    total_students = db.query(func.count(models.User.id)).filter(models.User.role == "student").scalar() or 0
    non_responders = max(total_students - len(rows), 0)
    expected_walkins = round(non_responders * NON_RESPONDER_EAT_RATE)

    base = confirmed_units + guests + expected_walkins
    recommended = math.ceil(base * (1 + COOKING_BUFFER_PCT / 100))

    diet, allergies = Counter(), Counter()
    for r in will_eat:
        for d in (r.user.diet_restrictions or []):
            diet[d] += 1
        for a in (r.user.allergies or []):
            allergies[a] += 1

    menu = db.query(models.Menu).filter(models.Menu.date == target_date, models.Menu.meal_type == meal_type).first()
    deadline = meal_deadline(target_date, meal_type)
    return {
        "date": str(target_date),
        "meal_type": meal_type,
        "dishes": (menu.dishes if menu else []),
        "confirmed_will_eat": len(will_eat),
        "confirmed_portion_units": round(confirmed_units, 1),
        "portion_breakdown": dict(portion_counts),
        "skipped": len(skipped),
        "guests": guests,
        "total_students": total_students,
        "not_responded": non_responders,
        "expected_walkins": expected_walkins,
        "buffer_pct": COOKING_BUFFER_PCT,
        "recommended_portions": recommended,
        "diet_counts": dict(diet),
        "allergy_counts": dict(allergies),
        "deadline": deadline,
        "deadline_passed": now >= deadline,
    }


def _listed_portions(db: Session, target_date, meal_type) -> int:
    return db.query(func.coalesce(func.sum(models.SurplusListing.portions_total), 0)).filter(
        models.SurplusListing.date == target_date, models.SurplusListing.meal_type == meal_type
    ).scalar() or 0


def upsert_log(db: Session, user, payload) -> models.KitchenLog:
    if payload.date > today_local():
        raise HTTPException(status_code=400, detail="You can't log production for a future date.")
    if payload.served_portions > payload.cooked_portions:
        raise HTTPException(status_code=400, detail="Served portions can't be more than cooked portions. Check both numbers.")

    leftover = payload.cooked_portions - payload.served_portions
    listed = _listed_portions(db, payload.date, payload.meal_type)
    if leftover < listed:
        raise HTTPException(
            status_code=400,
            detail=f"{listed} portions from this meal are already listed for rescue, so leftover can't drop below {listed}.",
        )

    log = db.query(models.KitchenLog).filter(
        models.KitchenLog.date == payload.date, models.KitchenLog.meal_type == payload.meal_type
    ).first()
    if not log:
        log = models.KitchenLog(
            date=payload.date, meal_type=payload.meal_type, logged_by=user.id,
            recommended_portions=cooking_sheet(db, payload.date, payload.meal_type)["recommended_portions"],
        )
        db.add(log)
    log.cooked_portions = payload.cooked_portions
    log.served_portions = payload.served_portions
    log.leftover_portions = leftover
    log.waste_reason = payload.waste_reason
    log.notes = payload.notes
    db.commit()
    db.refresh(log)
    return log


def log_to_dict(db: Session, log: models.KitchenLog) -> dict:
    over_pct = None
    if log.recommended_portions:
        over_pct = round((log.cooked_portions - log.recommended_portions) / log.recommended_portions * 100, 1)
    return {
        "id": log.id,
        "date": str(log.date),
        "meal_type": _mt(log.meal_type),
        "cooked_portions": log.cooked_portions,
        "served_portions": log.served_portions,
        "leftover_portions": log.leftover_portions,
        "recommended_portions": log.recommended_portions,
        "over_production_pct": over_pct,
        "listed_portions": _listed_portions(db, log.date, log.meal_type),
        "waste_reason": log.waste_reason,
        "notes": log.notes,
    }


def real_waste_summary(db: Session, d_from, d_to) -> dict:
    """Real waste from the kitchen log: leftover - rescued. Replaces the old 'predicted - checked in' proxy."""
    logs = db.query(models.KitchenLog).filter(
        models.KitchenLog.date >= d_from, models.KitchenLog.date <= d_to
    ).order_by(models.KitchenLog.date).all()
    listings = db.query(models.SurplusListing).filter(
        models.SurplusListing.date >= d_from, models.SurplusListing.date <= d_to
    ).all()

    rescued_by_key, students_total, ngo_total = Counter(), 0, 0
    for l in listings:
        o = listing_outcome(l)
        rescued_by_key[(str(l.date), _mt(l.meal_type))] += o["rescued"]
        students_total += o["claimed_picked_up"]
        ngo_total += o["donated_picked_up"]

    cooked = sum(l.cooked_portions for l in logs)
    served = sum(l.served_portions for l in logs)
    leftover = sum(l.leftover_portions for l in logs)
    rescued = students_total + ngo_total
    wasted = max(leftover - rescued, 0)

    by_reason = Counter()
    over_production = 0
    daily = []
    for l in logs:
        if l.leftover_portions > 0:
            by_reason[l.waste_reason or "not_specified"] += l.leftover_portions
        if l.recommended_portions is not None:
            over_production += max(l.cooked_portions - l.recommended_portions, 0)
        r = rescued_by_key.get((str(l.date), _mt(l.meal_type)), 0)
        daily.append({
            "date": str(l.date), "meal_type": _mt(l.meal_type), "cooked": l.cooked_portions, "served": l.served_portions,
            "leftover": l.leftover_portions, "rescued": r, "wasted": max(l.leftover_portions - r, 0),
        })

    return {
        "from": str(d_from), "to": str(d_to), "meals_logged": len(logs),
        "cooked": cooked, "served": served, "leftover": leftover,
        "rescued_by_students": students_total, "rescued_by_ngos": ngo_total, "rescued_total": rescued,
        "wasted": wasted,
        "rescue_rate": round(rescued / leftover, 2) if leftover else None,
        "waste_rate": round(wasted / cooked, 3) if cooked else None,
        "over_production_portions": over_production,
        "waste_cost_inr": round(wasted * DEFAULT_PORTION_COST_INR, 2),
        "rescued_value_inr": round(rescued * DEFAULT_PORTION_COST_INR, 2),
        "leftover_by_reason": dict(by_reason),
        "daily": daily,
    }

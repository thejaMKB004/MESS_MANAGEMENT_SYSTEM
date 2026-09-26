from datetime import date as date_cls, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin, require_admin_or_kitchen
from ..services.attendance_service import enforce_deadline, VALID_SKIP_REASONS

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/confirm", response_model=schemas.AttendanceOut)
def confirm_attendance(
    payload: schemas.AttendanceConfirm,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.status not in ("will_eat", "skip"):
        raise HTTPException(status_code=400, detail="status must be will_eat or skip")
    if payload.status == "skip" and payload.reason not in VALID_SKIP_REASONS:
        raise HTTPException(status_code=400, detail=f"reason must be one of {sorted(VALID_SKIP_REASONS)}")

    enforce_deadline(payload.date, payload.meal_type)

    existing = db.query(models.Attendance).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == payload.date,
        models.Attendance.meal_type == payload.meal_type,
    ).first()

    if existing:
        existing.status = payload.status
        existing.portion = payload.portion
        existing.reason = payload.reason if payload.status == "skip" else None
        db.commit()
        db.refresh(existing)
        return existing

    record = models.Attendance(
        user_id=current_user.id,
        date=payload.date,
        meal_type=payload.meal_type,
        status=payload.status,
        portion=payload.portion,
        reason=payload.reason if payload.status == "skip" else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/mine", response_model=List[schemas.AttendanceOut])
def my_attendance(
    from_: Optional[date_cls] = Query(None, alias="from"),
    to: Optional[date_cls] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Attendance).filter(models.Attendance.user_id == current_user.id)
    if from_:
        q = q.filter(models.Attendance.date >= from_)
    if to:
        q = q.filter(models.Attendance.date <= to)
    return q.order_by(models.Attendance.date.desc()).all()


@router.get("/today")
def today_attendance(
    meal_type: str,
    for_date: Optional[date_cls] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin_or_kitchen),
):
    target = for_date or date_cls.today()
    rows = db.query(models.Attendance).filter(
        models.Attendance.date == target, models.Attendance.meal_type == meal_type
    ).all()
    will_eat = [r for r in rows if r.status == models.AttendanceStatus.will_eat]
    skip = [r for r in rows if r.status == models.AttendanceStatus.skip]
    reasons = {}
    for r in skip:
        reasons[r.reason] = reasons.get(r.reason, 0) + 1

    guest_count = db.query(models.GuestBooking).filter(
        models.GuestBooking.date == target, models.GuestBooking.meal_type == meal_type
    ).all()
    total_guests = sum(g.count for g in guest_count)

    return {
        "date": target,
        "meal_type": meal_type,
        "confirmed_will_eat": len(will_eat),
        "guest_bookings": total_guests,
        "predicted_total": len(will_eat) + total_guests,
        "skipped": len(skip),
        "skip_reasons": reasons,
        "checked_in": db.query(models.MealCheckin).join(models.Attendance).filter(
            models.Attendance.date == target, models.Attendance.meal_type == meal_type
        ).count(),
    }


@router.get("/stats")
def attendance_stats(
    from_: date_cls = Query(..., alias="from"),
    to: date_cls = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    rows = db.query(models.Attendance).filter(
        models.Attendance.date >= from_, models.Attendance.date <= to
    ).all()
    by_day = {}
    for r in rows:
        key = str(r.date)
        by_day.setdefault(key, {"will_eat": 0, "skip": 0})
        by_day[key]["will_eat" if r.status == models.AttendanceStatus.will_eat else "skip"] += 1
    return {"from": from_, "to": to, "by_day": by_day}


@router.post("/checkin")
def checkin(
    payload: schemas.CheckinRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_or_kitchen),
):
    attendance = db.query(models.Attendance).filter(models.Attendance.id == payload.attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if attendance.status != models.AttendanceStatus.will_eat:
        raise HTTPException(status_code=400, detail="Cannot check in a skipped meal")
    existing = db.query(models.MealCheckin).filter(models.MealCheckin.attendance_id == attendance.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already checked in")
    checkin_record = models.MealCheckin(attendance_id=attendance.id, method=payload.method)
    db.add(checkin_record)
    db.commit()
    return {"detail": "Checked in", "attendance_id": attendance.id, "time": datetime.utcnow()}

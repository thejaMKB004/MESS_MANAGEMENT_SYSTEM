from datetime import date as date_cls, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..timeutil import now_local, today_local
from .. import models
from ..database import get_db
from ..deps import require_admin
from ..services.waste_service import compute_waste_estimate
from ..services.feedback_service import top_bottom_dishes
from ..services.report_service import build_weekly_report
from ..services.anomaly_service import detect_anomalies

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/attendance")
def attendance_analytics(
    from_: date_cls = Query(..., alias="from"),
    to: date_cls = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    rows = db.query(models.Attendance).filter(
        models.Attendance.date >= from_, models.Attendance.date <= to
    ).all()

    by_meal = {}
    by_hostel = {}
    for r in rows:
        by_meal.setdefault(r.meal_type.value, {"will_eat": 0, "skip": 0})
        by_meal[r.meal_type.value]["will_eat" if r.status == models.AttendanceStatus.will_eat else "skip"] += 1

        hostel = r.user.hostel or "unknown"
        by_hostel.setdefault(hostel, {"will_eat": 0, "skip": 0})
        by_hostel[hostel]["will_eat" if r.status == models.AttendanceStatus.will_eat else "skip"] += 1

    return {"from": from_, "to": to, "by_meal": by_meal, "by_hostel": by_hostel}


@router.get("/dish-ratings")
def dish_ratings(limit: int = 5, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return top_bottom_dishes(db, limit=limit)


@router.get("/waste-estimate")
def waste_estimate(
    for_date: date_cls = Query(..., alias="date"),
    meal_type: str = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return compute_waste_estimate(db, for_date, meal_type)


@router.get("/weekly-report")
def weekly_report(
    week_start: date_cls = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    summary = build_weekly_report(db, week_start)
    record = models.Report(week_start=week_start, summary=summary)
    db.add(record)
    db.commit()
    return summary


@router.get("/anomalies")
def anomalies(
    for_date: date_cls = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    target = for_date or today_local()
    return {"date": target, "anomalies": detect_anomalies(db, target)}


@router.get("/real-waste")
def real_waste(
    from_: date_cls = Query(..., alias="from"), to: date_cls = Query(...),
    db: Session = Depends(get_db), admin=Depends(require_admin),
):
    """Real waste from the kitchen production log: leftover minus what was rescued."""
    from ..services.kitchen_service import real_waste_summary
    return real_waste_summary(db, from_, to)

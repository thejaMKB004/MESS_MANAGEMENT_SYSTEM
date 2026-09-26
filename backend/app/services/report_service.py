from datetime import date as date_cls, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models
from .waste_service import compute_waste_estimate
from .feedback_service import top_bottom_dishes


def build_weekly_report(db: Session, week_start: date_cls):
    week_end = week_start + timedelta(days=6)
    days = [week_start + timedelta(days=i) for i in range(7)]

    attendance_summary = []
    total_waste_meals = 0
    total_waste_cost = 0.0
    for d in days:
        for meal_type in ["breakfast", "lunch", "dinner"]:
            est = compute_waste_estimate(db, d, meal_type)
            if est["predicted_count"] == 0:
                continue
            attendance_summary.append(est)
            total_waste_meals += est["waste_meals"]
            total_waste_cost += est["waste_cost_inr"]

    complaints_count = db.query(func.count(models.Complaint.id)).filter(
        models.Complaint.created_at >= week_start,
        models.Complaint.created_at < week_end + timedelta(days=1),
    ).scalar() or 0

    resolved_count = db.query(func.count(models.Complaint.id)).filter(
        models.Complaint.status == models.ComplaintStatus.resolved,
        models.Complaint.created_at >= week_start,
        models.Complaint.created_at < week_end + timedelta(days=1),
    ).scalar() or 0

    dishes = top_bottom_dishes(db, limit=5)

    summary = {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "total_waste_meals": total_waste_meals,
        "total_waste_cost_inr": round(total_waste_cost, 2),
        "complaints_received": complaints_count,
        "complaints_resolved": resolved_count,
        "top_dishes": dishes["top"],
        "bottom_dishes": dishes["bottom"],
        "daily_breakdown": attendance_summary,
    }
    return summary

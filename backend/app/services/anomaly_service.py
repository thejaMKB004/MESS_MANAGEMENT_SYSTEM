"""Simple rule/stddev-based anomaly detection over recent attendance history.
Flags a meal as anomalous if today's skip rate deviates far from the trailing average -
good enough signal for a mini-project without a full ML forecasting pipeline."""
import statistics
from datetime import date as date_cls, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models


def skip_rate_for(db: Session, target_date: date_cls, meal_type: str):
    total = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.date == target_date, models.Attendance.meal_type == meal_type
    ).scalar() or 0
    skips = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.date == target_date,
        models.Attendance.meal_type == meal_type,
        models.Attendance.status == models.AttendanceStatus.skip,
    ).scalar() or 0
    return (skips / total) if total else None


def detect_anomalies(db: Session, target_date: date_cls, lookback_days: int = 14):
    results = []
    for meal_type in ["breakfast", "lunch", "dinner"]:
        history = []
        for i in range(1, lookback_days + 1):
            d = target_date - timedelta(days=i)
            rate = skip_rate_for(db, d, meal_type)
            if rate is not None:
                history.append(rate)

        today_rate = skip_rate_for(db, target_date, meal_type)
        if today_rate is None or len(history) < 3:
            continue

        mean = statistics.mean(history)
        stdev = statistics.pstdev(history) or 0.01
        z_score = (today_rate - mean) / stdev

        if abs(z_score) >= 1.5:
            results.append({
                "meal_type": meal_type,
                "date": target_date,
                "today_skip_rate": round(today_rate, 2),
                "avg_skip_rate": round(mean, 2),
                "z_score": round(z_score, 2),
                "alert": "high_skip_spike" if z_score > 0 else "unusually_low_skip",
            })
    return results

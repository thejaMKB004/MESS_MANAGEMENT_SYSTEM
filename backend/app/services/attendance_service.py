from datetime import datetime, date as date_cls, timedelta
from fastapi import HTTPException
from ..config import MEAL_START_TIMES, ATTENDANCE_DEADLINE_HOURS_BEFORE


def enforce_deadline(meal_date: date_cls, meal_type: str, now: datetime = None):
    """Raise if confirming/skipping this meal is past the allowed deadline.
    Deadline = meal start time minus ATTENDANCE_DEADLINE_HOURS_BEFORE, on the meal's own date.
    Confirmations for future dates are always allowed."""
    now = now or datetime.utcnow()
    if meal_date > now.date():
        return  # future day, fine
    if meal_date < now.date():
        raise HTTPException(status_code=400, detail="Cannot confirm attendance for a past date")

    start_hour = MEAL_START_TIMES.get(meal_type)
    if start_hour is None:
        return
    deadline = datetime.combine(meal_date, datetime.min.time()) + timedelta(hours=start_hour - ATTENDANCE_DEADLINE_HOURS_BEFORE)
    if now > deadline:
        raise HTTPException(
            status_code=400,
            detail=f"Deadline passed: {meal_type} confirmations close {ATTENDANCE_DEADLINE_HOURS_BEFORE}h before service.",
        )


VALID_SKIP_REASONS = {
    "dont_like_menu",
    "eating_out",
    "not_on_campus",
    "not_hungry_health",
    "other",
}

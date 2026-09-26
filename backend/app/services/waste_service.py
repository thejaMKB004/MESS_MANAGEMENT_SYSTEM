from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date as date_cls
from .. import models
from ..config import DEFAULT_PORTION_COST_INR


def compute_waste_estimate(db: Session, target_date: date_cls, meal_type: str):
    confirmed = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.date == target_date,
        models.Attendance.meal_type == meal_type,
        models.Attendance.status == models.AttendanceStatus.will_eat,
    ).scalar() or 0

    guest_count = db.query(func.coalesce(func.sum(models.GuestBooking.count), 0)).filter(
        models.GuestBooking.date == target_date,
        models.GuestBooking.meal_type == meal_type,
    ).scalar() or 0

    predicted_count = confirmed + guest_count

    # actual eaters = confirmed attendance rows that have a checkin record
    actual_eaters = db.query(func.count(models.Attendance.id)).join(
        models.MealCheckin, models.MealCheckin.attendance_id == models.Attendance.id
    ).filter(
        models.Attendance.date == target_date,
        models.Attendance.meal_type == meal_type,
    ).scalar() or 0

    # if nobody has checked in yet (e.g. meal not served yet), fall back to predicted == actual
    # so the estimate reads as "0 waste so far" rather than "100% waste"
    if actual_eaters == 0:
        checkins_exist = db.query(func.count(models.MealCheckin.id)).join(
            models.Attendance, models.Attendance.id == models.MealCheckin.attendance_id
        ).filter(
            models.Attendance.date == target_date,
            models.Attendance.meal_type == meal_type,
        ).scalar() or 0
        if checkins_exist == 0:
            actual_eaters = predicted_count

    waste_meals = max(predicted_count - actual_eaters, 0)
    waste_cost_inr = round(waste_meals * DEFAULT_PORTION_COST_INR, 2)

    return {
        "date": str(target_date),
        "meal_type": meal_type,
        "predicted_count": predicted_count,
        "actual_eaters": actual_eaters,
        "waste_meals": waste_meals,
        "waste_cost_inr": waste_cost_inr,
    }

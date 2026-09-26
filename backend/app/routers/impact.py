from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..config import DEFAULT_PORTION_COST_INR

# rough figures for the "impact" framing - not scientifically precise, just illustrative
CO2_KG_PER_MEAL_SAVED = 0.5
WATER_LITRES_PER_MEAL_SAVED = 40

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("/me")
def my_impact(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    records = db.query(models.Attendance).filter(models.Attendance.user_id == current_user.id).all()
    skipped = [r for r in records if r.status == models.AttendanceStatus.skip]
    total_confirmed = len(records)

    meals_saved = len(skipped)
    est_food_saved_cost = round(meals_saved * DEFAULT_PORTION_COST_INR, 2)
    co2_saved_kg = round(meals_saved * CO2_KG_PER_MEAL_SAVED, 2)
    water_saved_litres = round(meals_saved * WATER_LITRES_PER_MEAL_SAVED, 1)

    # simple current streak: consecutive most-recent days where every confirmed meal
    # accurately reflects a decision (any confirmation counts toward "active" streak)
    days = sorted({r.date for r in records}, reverse=True)
    streak = 0
    from datetime import timedelta
    expected = None
    for d in days:
        if expected is None or d == expected:
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break

    return {
        "total_confirmations": total_confirmed,
        "meals_skipped": meals_saved,
        "estimated_food_cost_saved_inr": est_food_saved_cost,
        "estimated_co2_saved_kg": co2_saved_kg,
        "estimated_water_saved_litres": water_saved_litres,
        "current_streak_days": streak,
    }

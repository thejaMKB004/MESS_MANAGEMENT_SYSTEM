from datetime import date as date_cls
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin_or_kitchen
from ..services import nutrition_service as svc
from ..timeutil import today_local

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/dishes")
def list_dishes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Every dish on any menu, with its nutrition data (or has_data=false if it still needs it)."""
    data = {d.dish_name: svc.dish_to_dict(d) for d in db.query(models.DishNutrition).all()}
    names = set(data)
    for (dishes,) in db.query(models.Menu.dishes).all():
        names.update(dishes or [])
    out = []
    for name in sorted(names):
        row = data.get(name)
        out.append({**row, "has_data": True} if row else {"dish_name": name, "has_data": False})
    return out


@router.put("/dishes/{dish_name}")
def upsert_dish(dish_name: str, payload: schemas.DishNutritionUpsert, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    dish_name = dish_name.strip()
    if not dish_name:
        raise HTTPException(status_code=400, detail="Dish name is required.")
    d = db.query(models.DishNutrition).filter(models.DishNutrition.dish_name == dish_name).first()
    if not d:
        d = models.DishNutrition(dish_name=dish_name)
        db.add(d)
    for field, value in payload.model_dump().items():
        setattr(d, field, value)
    d.updated_by = user.id
    db.commit()
    return svc.dish_to_dict(d)


@router.get("/meals")
def meals(from_: date_cls = Query(..., alias="from"), to: date_cls = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    if (to - from_).days > 31:
        raise HTTPException(status_code=400, detail="Choose a range of 31 days or less.")
    return svc.meals_in_range(db, user, from_, to)


@router.get("/intake")
def intake_day(date: Optional[date_cls] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    return svc.day_view(db, user, date or today_local())


@router.post("/intake")
def add_intake(payload: schemas.IntakeCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return svc.entry_to_dict(svc.add_intake(db, user, payload))


@router.delete("/intake/{entry_id}")
def delete_intake(entry_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc.delete_intake(db, user, entry_id)
    return {"detail": "Deleted"}


@router.get("/summary")
def summary(days: int = Query(7, ge=1, le=31), db: Session = Depends(get_db), user=Depends(get_current_user)):
    return svc.summary(db, user, days)


@router.put("/goal")
def set_goal(payload: schemas.GoalUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return svc.set_goal(db, user, payload)

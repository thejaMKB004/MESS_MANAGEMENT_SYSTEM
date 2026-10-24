from datetime import date as date_cls
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin_or_kitchen
from ..services import kitchen_service

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


@router.get("/cooking-sheet")
def cooking_sheet(
    date: date_cls = Query(...), meal_type: schemas.MealLiteral = Query(...),
    db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen),
):
    return kitchen_service.cooking_sheet(db, date, meal_type)


@router.put("/logs")
def save_log(payload: schemas.KitchenLogUpsert, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    return kitchen_service.log_to_dict(db, kitchen_service.upsert_log(db, user, payload))


@router.get("/logs")
def list_logs(
    from_: Optional[date_cls] = Query(None, alias="from"), to: Optional[date_cls] = Query(None),
    db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen),
):
    q = db.query(models.KitchenLog)
    if from_:
        q = q.filter(models.KitchenLog.date >= from_)
    if to:
        q = q.filter(models.KitchenLog.date <= to)
    return [kitchen_service.log_to_dict(db, l) for l in q.order_by(models.KitchenLog.date.desc()).limit(200).all()]

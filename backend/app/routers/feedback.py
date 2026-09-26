from datetime import date as date_cls
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..services.feedback_service import dish_rating_trend

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=schemas.FeedbackOut)
def create_feedback(
    payload: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = models.Feedback(
        user_id=current_user.id,
        date=payload.date,
        meal_type=payload.meal_type,
        dish_name=payload.dish_name,
        rating=payload.rating,
        tags=payload.tags,
        comment=payload.comment,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/dish/{dish_name}")
def dish_feedback(
    dish_name: str,
    from_: Optional[date_cls] = Query(None, alias="from"),
    to: Optional[date_cls] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return dish_rating_trend(db, dish_name, from_, to)

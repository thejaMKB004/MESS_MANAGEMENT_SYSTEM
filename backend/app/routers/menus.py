from datetime import date as date_cls
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("", response_model=List[schemas.MenuOut])
def list_menus(
    from_: Optional[date_cls] = Query(None, alias="from"),
    to: Optional[date_cls] = Query(None),
    db: Session = Depends(get_db),
    _current=Depends(get_current_user),
):
    q = db.query(models.Menu)
    if from_:
        q = q.filter(models.Menu.date >= from_)
    if to:
        q = q.filter(models.Menu.date <= to)
    return q.order_by(models.Menu.date).all()


@router.post("", response_model=schemas.MenuOut)
def create_menu(payload: schemas.MenuCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    existing = db.query(models.Menu).filter(
        models.Menu.date == payload.date, models.Menu.meal_type == payload.meal_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Menu already exists for this date/meal; use PATCH to edit")
    menu = models.Menu(date=payload.date, meal_type=payload.meal_type, dishes=payload.dishes, created_by=admin.id)
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


@router.patch("/{menu_id}", response_model=schemas.MenuOut)
def update_menu(menu_id: int, payload: schemas.MenuUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    if payload.dishes is not None:
        menu.dishes = payload.dishes
    db.commit()
    db.refresh(menu)
    return menu

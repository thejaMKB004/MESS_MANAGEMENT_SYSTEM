from datetime import date as date_cls
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/items", response_model=List[schemas.InventoryItemOut])
def list_items(db: Session = Depends(get_db), _current=Depends(get_current_user)):
    return db.query(models.InventoryItem).all()


@router.post("/items", response_model=schemas.InventoryItemOut)
def create_item(payload: schemas.InventoryItemCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    existing = db.query(models.InventoryItem).filter(models.InventoryItem.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item already exists")
    item = models.InventoryItem(**payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/dish-ingredients")
def link_dish_ingredient(payload: schemas.DishIngredientCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    link = models.DishIngredient(**payload.dict())
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "dish_name": link.dish_name, "item": item.name, "qty_per_serving": link.qty_per_serving}


@router.get("/requirements")
def requirements(
    for_date: date_cls = Query(..., alias="date"),
    meal_type: str = Query(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Given confirmed attendance for a meal, compute how much of each ingredient is needed."""
    menu = db.query(models.Menu).filter(models.Menu.date == for_date, models.Menu.meal_type == meal_type).first()
    if not menu:
        raise HTTPException(status_code=404, detail="No menu found for this date/meal")

    confirmed = db.query(models.Attendance).filter(
        models.Attendance.date == for_date,
        models.Attendance.meal_type == meal_type,
        models.Attendance.status == models.AttendanceStatus.will_eat,
    ).count()
    guests = db.query(models.GuestBooking).filter(
        models.GuestBooking.date == for_date, models.GuestBooking.meal_type == meal_type
    ).all()
    total_servings = confirmed + sum(g.count for g in guests)

    needs = {}
    total_cost = 0.0
    for dish in menu.dishes:
        links = db.query(models.DishIngredient).filter(models.DishIngredient.dish_name == dish).all()
        for link in links:
            item = link.item
            qty_needed = link.qty_per_serving * total_servings
            cost = qty_needed * (item.cost_per_unit or 0)
            total_cost += cost
            if item.name not in needs:
                needs[item.name] = {"unit": item.unit, "qty_needed": 0.0, "current_stock": item.stock_qty, "estimated_cost_inr": 0.0}
            needs[item.name]["qty_needed"] += qty_needed
            needs[item.name]["estimated_cost_inr"] += cost

    for v in needs.values():
        v["qty_needed"] = round(v["qty_needed"], 2)
        v["estimated_cost_inr"] = round(v["estimated_cost_inr"], 2)
        v["shortfall"] = round(max(v["qty_needed"] - v["current_stock"], 0), 2)

    return {
        "date": for_date,
        "meal_type": meal_type,
        "total_servings": total_servings,
        "ingredient_requirements": needs,
        "estimated_total_cost_inr": round(total_cost, 2),
    }

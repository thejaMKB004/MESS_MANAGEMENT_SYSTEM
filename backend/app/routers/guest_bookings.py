from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/guest-bookings", tags=["guest-bookings"])


@router.post("", response_model=schemas.GuestBookingOut)
def create_booking(
    payload: schemas.GuestBookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    booking = models.GuestBooking(booked_by=current_user.id, **payload.dict())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/mine", response_model=List[schemas.GuestBookingOut])
def my_bookings(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.GuestBooking).filter(models.GuestBooking.booked_by == current_user.id).all()

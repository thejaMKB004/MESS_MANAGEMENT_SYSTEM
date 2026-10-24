from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin_or_kitchen
from ..services import surplus_service as svc
from ..timeutil import now_local

router = APIRouter(prefix="/donations", tags=["donations"])
public_router = APIRouter(prefix="/public/donations", tags=["donations-public"])


@router.get("")
def list_donations(db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    rows = db.query(models.Donation).order_by(models.Donation.offered_at.desc()).limit(100).all()
    return [{"id": d.id, "ngo": d.ngo.name, "dish_description": d.listing.dish_description, "portions": d.portions,
             "status": d.status, "offered_at": d.offered_at, "safe_until": d.listing.safe_until,
             "safe_until_label": svc._fmt_time(d.listing.safe_until),
             "portions_picked": d.portions_picked} for d in rows]


@router.post("/{donation_id}/pickup")
def pickup(donation_id: int, payload: schemas.DonationPickup, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    d = svc.record_donation_pickup(db, donation_id, payload.portions_picked)
    return {"detail": "Pickup recorded", "ngo": d.ngo.name, "portions_picked": d.portions_picked}


# ---- no login: the secret token in the emailed link is the credential ----

@public_router.get("/{token}")
def view_offer(token: str, db: Session = Depends(get_db)):
    d = db.query(models.Donation).filter(models.Donation.token == token).first()
    if not d:
        raise HTTPException(status_code=404, detail="This offer link isn't valid.")
    l = d.listing
    return {"ngo": d.ngo.name, "dish_description": l.dish_description, "portions": d.portions,
            "meal_type": svc._mt(l.meal_type), "date": str(l.date), "safe_until": l.safe_until,
            "safe_until_label": svc._fmt_time(l.safe_until),
            "status": d.status, "expired": now_local() >= l.safe_until}


@public_router.post("/{token}/respond")
def respond(token: str, payload: schemas.DonationRespond, db: Session = Depends(get_db)):
    d = svc.ngo_respond(db, token, payload.action)
    return {"detail": "Thank you. The mess has been told you will collect." if d.status == "accepted" else "Noted. Thanks for letting us know.",
            "status": d.status}

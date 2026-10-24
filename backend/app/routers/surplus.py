from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_role, require_admin_or_kitchen
from ..services import surplus_service as svc
from ..timeutil import now_local

router = APIRouter(prefix="/surplus", tags=["surplus-rescue"])
require_student = require_role("student")


@router.post("/listings")
def create_listing(payload: schemas.SurplusCreate, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    return svc.listing_to_dict(svc.create_listing(db, user, payload), admin_view=True)


@router.get("/listings")
def list_listings(status: Optional[str] = None, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    q = db.query(models.SurplusListing)
    if status:
        q = q.filter(models.SurplusListing.status == status)
    return [svc.listing_to_dict(l, admin_view=True) for l in q.order_by(models.SurplusListing.created_at.desc()).limit(50).all()]


@router.get("/open")
def open_for_students(db: Session = Depends(get_db), user=Depends(get_current_user)):
    now = now_local()
    rows = db.query(models.SurplusListing).filter(
        models.SurplusListing.status == "open_students",
        models.SurplusListing.student_window_ends > now,
        models.SurplusListing.portions_remaining > 0,
    ).order_by(models.SurplusListing.created_at.desc()).all()
    return [svc.listing_to_dict(l) for l in rows]


@router.post("/listings/{listing_id}/claim")
def claim(listing_id: int, payload: schemas.ClaimRequest, db: Session = Depends(get_db), user=Depends(require_student)):
    c = svc.claim(db, user, listing_id, payload.portions)
    return {"id": c.id, "code": c.code, "portions": c.portions, "expires_at": c.expires_at, "status": c.status,
            "seconds_left": max(int((c.expires_at - now_local()).total_seconds()), 0),
            "dish_description": c.listing.dish_description}


@router.get("/claims/mine")
def my_claims(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.SurplusClaim).filter(models.SurplusClaim.user_id == user.id).order_by(models.SurplusClaim.created_at.desc()).limit(30).all()
    now = now_local()
    return [{"id": c.id, "code": c.code, "portions": c.portions, "status": c.status, "expires_at": c.expires_at,
             "seconds_left": max(int((c.expires_at - now).total_seconds()), 0),
             "dish_description": c.listing.dish_description, "created_at": c.created_at} for c in rows]


@router.post("/claims/pickup")
def pickup(payload: schemas.PickupRequest, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    c = svc.pickup_claim(db, payload.code)
    return {"detail": "Handed over", "student": c.user.name, "portions": c.portions, "dish_description": c.listing.dish_description}


@router.post("/listings/{listing_id}/offer-ngo")
def offer_ngo(listing_id: int, payload: schemas.OfferNgoRequest, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    listing = db.query(models.SurplusListing).filter(models.SurplusListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    donations = svc.offer_to_ngos(db, listing, ngo_ids=payload.ngo_ids)
    return {"detail": f"Offered to {len(donations)} partner(s)", "listing": svc.listing_to_dict(listing, admin_view=True)}


@router.post("/listings/{listing_id}/close")
def close(listing_id: int, db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    listing = db.query(models.SurplusListing).filter(models.SurplusListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if listing.status in svc.ACTIVE_LISTING:
        listing.status = "closed"
        for c in listing.claims:
            if c.status == "reserved":
                c.status = "expired"
        for d in listing.donations:
            if d.status in ("offered", "accepted"):
                d.status = "expired"
        db.commit()
    return svc.listing_to_dict(listing, admin_view=True)

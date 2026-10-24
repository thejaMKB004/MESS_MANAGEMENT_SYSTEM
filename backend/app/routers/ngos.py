from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin, require_admin_or_kitchen

router = APIRouter(prefix="/ngos", tags=["ngo-partners"])


def _out(n):
    return {"id": n.id, "name": n.name, "contact_person": n.contact_person, "email": n.email,
            "phone": n.phone, "area": n.area, "active": n.active}


@router.get("")
def list_ngos(db: Session = Depends(get_db), user=Depends(require_admin_or_kitchen)):
    return [_out(n) for n in db.query(models.NGOPartner).order_by(models.NGOPartner.name).all()]


@router.post("")
def create_ngo(payload: schemas.NGOCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    ngo = models.NGOPartner(**payload.model_dump())
    db.add(ngo)
    db.commit()
    db.refresh(ngo)
    return _out(ngo)


@router.patch("/{ngo_id}")
def update_ngo(ngo_id: int, payload: schemas.NGOUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    ngo = db.query(models.NGOPartner).filter(models.NGOPartner.id == ngo_id).first()
    if not ngo:
        raise HTTPException(status_code=404, detail="Partner not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ngo, field, value)
    db.commit()
    return _out(ngo)

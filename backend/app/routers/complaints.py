from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..timeutil import now_local, today_local
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..services.sentiment_service import score_sentiment

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=schemas.ComplaintOut)
def create_complaint(
    payload: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = models.Complaint(
        user_id=current_user.id,
        category=payload.category,
        severity=payload.severity,
        description=payload.description,
        sentiment_score=score_sentiment(payload.description),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=List[schemas.ComplaintOut])
def list_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    q = db.query(models.Complaint)
    if status_filter:
        q = q.filter(models.Complaint.status == status_filter)
    if category:
        q = q.filter(models.Complaint.category == category)
    return q.order_by(models.Complaint.created_at.desc()).all()


@router.patch("/{complaint_id}/status", response_model=schemas.ComplaintOut)
def update_status(
    complaint_id: int,
    payload: schemas.ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if payload.status not in ("open", "in_progress", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid status")
    complaint.status = payload.status
    if payload.status == "resolved":
        complaint.resolved_at = now_local()
    db.commit()
    db.refresh(complaint)
    return complaint

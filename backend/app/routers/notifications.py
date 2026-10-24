from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(n, with_recipient=False):
    d = {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link,
         "is_read": n.is_read, "created_at": n.created_at, "email_status": n.email_status}
    if with_recipient:
        d["recipient"] = n.user.name if n.user else n.recipient_email
        d["recipient_email"] = n.recipient_email
    return d


@router.get("/mine")
def mine(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(models.Notification).filter(models.Notification.user_id == user.id).order_by(models.Notification.created_at.desc()).limit(50).all()
    unread = db.query(models.Notification).filter(models.Notification.user_id == user.id, models.Notification.is_read == False).count()  # noqa: E712
    return {"unread": unread, "items": [_out(n) for n in rows]}


@router.post("/mine/read-all")
def read_all(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(models.Notification).filter(models.Notification.user_id == user.id, models.Notification.is_read == False).update({"is_read": True})  # noqa: E712
    db.commit()
    return {"detail": "ok"}


@router.post("/{notification_id}/read")
def read_one(notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    db.commit()
    return {"detail": "ok"}


@router.get("/outbox")
def outbox(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Every message the system has sent, including emails to NGOs (with their response links)."""
    rows = db.query(models.Notification).filter(
        models.Notification.kind != "last_call", models.Notification.kind != "reminder"
    ).order_by(models.Notification.created_at.desc()).limit(100).all()
    return [_out(n, with_recipient=True) for n in rows]

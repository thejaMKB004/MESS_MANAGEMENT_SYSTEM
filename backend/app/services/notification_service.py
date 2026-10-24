"""Creates notifications. Every message is stored (so the app has an in-app inbox and an admin outbox);
if SMTP_* settings exist it is also emailed. Without SMTP the email status is 'skipped', which keeps the demo
working on a laptop with no mail server."""
import logging
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from .. import models
from ..config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

log = logging.getLogger("notifications")


def _send_email(to: str, subject: str, body: str) -> str:
    if not SMTP_HOST:
        return "skipped"
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = SMTP_FROM, to, subject
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return "sent"
    except Exception as exc:  # never let a mail problem break the main workflow
        log.warning("Email to %s failed: %s", to, exc)
        return "failed"


def notify_users(db: Session, users, kind, title, body, link=None, payload=None, email=False):
    """In-app notification for each user (and an email too if email=True). The caller commits."""
    created = []
    for user in users:
        n = models.Notification(
            user_id=user.id, kind=kind, title=title, body=body, link=link, payload=payload,
            recipient_email=user.email if email else None,
        )
        if email:
            n.email_status = _send_email(user.email, title, body + (f"\n\n{link}" if link else ""))
        db.add(n)
        created.append(n)
    return created


def notify_roles(db: Session, roles, kind, title, body, link=None, payload=None, email=False):
    users = db.query(models.User).filter(models.User.role.in_(list(roles))).all()
    return notify_users(db, users, kind, title, body, link, payload, email)


def notify_external(db: Session, email_address, kind, title, body, link=None, payload=None):
    """Message for someone without an account (an NGO contact). Always emailed when SMTP is configured."""
    n = models.Notification(
        user_id=None, recipient_email=email_address, kind=kind, title=title, body=body, link=link, payload=payload,
    )
    n.email_status = _send_email(email_address, title, body + (f"\n\nRespond here: {link}" if link else ""))
    db.add(n)
    return n

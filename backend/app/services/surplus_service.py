"""Surplus rescue: leftover cooked food -> students (last call) -> NGO partners -> logged outcome.

Lifecycle of a listing:   open_students --(window ends)--> offered_ngo --(collected)--> closed
                                     \\______________(safe_until passes)______________> expired
Accounting rule: wasted = portions_total - (collected by students + collected by NGOs).
It is derived, never stored, so it can't drift out of sync.
"""
import secrets
import string
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..config import (
    SURPLUS_SAFE_HOURS, SURPLUS_STUDENT_WINDOW_MINUTES, CLAIM_HOLD_MINUTES,
    MAX_PORTIONS_PER_STUDENT, AUTO_ESCALATE_TO_NGO, FRONTEND_BASE_URL,
)
from ..timeutil import now_local
from . import notification_service as notif

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I so codes are easy to read out
ACTIVE_LISTING = ("open_students", "offered_ngo")


def _mt(value):
    return value.value if hasattr(value, "value") else value


def _fmt_time(dt) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def _new_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not db.query(models.SurplusClaim).filter(models.SurplusClaim.code == code).first():
            return code
    raise HTTPException(status_code=500, detail="Could not generate a claim code. Try again.")


def listing_outcome(listing: models.SurplusListing) -> dict:
    claimed = sum(c.portions for c in listing.claims if c.status == "picked_up")
    reserved = sum(c.portions for c in listing.claims if c.status == "reserved")
    donated = sum((d.portions_picked if d.portions_picked is not None else d.portions)
                  for d in listing.donations if d.status == "picked_up")
    rescued = claimed + donated
    final = listing.status in ("closed", "expired")
    return {
        "claimed_picked_up": claimed, "claims_reserved": reserved, "donated_picked_up": donated, "rescued": rescued,
        "wasted": max(listing.portions_total - rescued, 0) if final else None,
    }


def listing_to_dict(listing: models.SurplusListing, admin_view: bool = False) -> dict:
    now = now_local()
    data = {}
    data.update({
        "student_seconds_left": max(int((listing.student_window_ends - now).total_seconds()), 0),
        "safe_seconds_left": max(int((listing.safe_until - now).total_seconds()), 0),
        "student_window_ends_label": _fmt_time(listing.student_window_ends),
        "safe_until_label": _fmt_time(listing.safe_until),
    })
    data.update({
        "id": listing.id, "date": str(listing.date), "meal_type": _mt(listing.meal_type),
        "dish_description": listing.dish_description,
        "portions_total": listing.portions_total, "portions_remaining": listing.portions_remaining,
        "cooked_at": listing.cooked_at, "safe_until": listing.safe_until,
        "student_window_ends": listing.student_window_ends, "status": listing.status,
    })
    if admin_view:
        data.update({
            "ngo_offered_at": listing.ngo_offered_at,
            "outcome": listing_outcome(listing),
            "claims": [{"code": c.code, "student": c.user.name, "portions": c.portions, "status": c.status} for c in listing.claims],
            "donations": [{"id": d.id, "ngo": d.ngo.name, "portions": d.portions, "status": d.status} for d in listing.donations],
        })
    return data


def maybe_close(listing: models.SurplusListing) -> bool:
    """Close a listing once nothing is left to hand out and nothing is still pending."""
    if listing.status not in ACTIVE_LISTING:
        return False
    pending_claims = any(c.status == "reserved" for c in listing.claims)
    pending_donations = any(d.status in ("offered", "accepted") for d in listing.donations)
    if listing.portions_remaining <= 0 and not pending_claims and not pending_donations:
        listing.status = "closed"
        return True
    # an NGO collected everything that was offered and no student pickups are pending
    if listing.status == "offered_ngo" and not pending_claims and not pending_donations \
            and any(d.status == "picked_up" for d in listing.donations):
        listing.status = "closed"
        return True
    return False


# ---------------------------------------------------------------- create

def create_listing(db: Session, user, payload, now=None) -> models.SurplusListing:
    now = now or now_local()
    if not payload.held_safely:
        raise HTTPException(status_code=400, detail="Confirm the food was held at a safe temperature before listing it.")

    log = db.query(models.KitchenLog).filter(
        models.KitchenLog.date == payload.date, models.KitchenLog.meal_type == payload.meal_type
    ).first()
    if not log:
        raise HTTPException(status_code=400, detail="Log this meal's cooked and served portions first.")

    already = sum(l.portions_total for l in db.query(models.SurplusListing).filter(
        models.SurplusListing.date == payload.date, models.SurplusListing.meal_type == payload.meal_type).all())
    available = log.leftover_portions - already
    if payload.portions > available:
        raise HTTPException(status_code=400, detail=f"Only {max(available, 0)} leftover portions are available to list.")

    cooked_at = now - timedelta(minutes=payload.cooked_minutes_ago)
    safe_until = cooked_at + timedelta(hours=SURPLUS_SAFE_HOURS)
    if safe_until - now < timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="This food is past its safe window and can't be offered.")
    window_end = min(now + timedelta(minutes=SURPLUS_STUDENT_WINDOW_MINUTES), safe_until)

    listing = models.SurplusListing(
        date=payload.date, meal_type=payload.meal_type, dish_description=payload.dish_description.strip(),
        portions_total=payload.portions, portions_remaining=payload.portions,
        cooked_at=cooked_at, safe_until=safe_until, student_window_ends=window_end,
        held_safely=True, status="open_students", created_by=user.id,
    )
    db.add(listing)
    db.flush()

    students = db.query(models.User).filter(models.User.role == "student").all()
    notif.notify_users(
        db, students, "last_call",
        f"Last call: {payload.portions} portions of {listing.dish_description}",
        f"Free leftover food at the mess counter. Claim by {_fmt_time(window_end)}, one portion each.",
        link="/rescue",
    )
    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------- students

def claim(db: Session, user, listing_id: int, portions: int, now=None) -> models.SurplusClaim:
    now = now or now_local()
    listing = db.query(models.SurplusListing).filter(models.SurplusListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if listing.status != "open_students" or now >= listing.student_window_ends:
        raise HTTPException(status_code=400, detail="Claiming for this listing has closed.")
    if listing.portions_remaining < portions:
        raise HTTPException(status_code=400, detail="Not enough portions left. Someone just claimed them.")

    held = sum(c.portions for c in listing.claims if c.user_id == user.id and c.status in ("reserved", "picked_up"))
    if held + portions > MAX_PORTIONS_PER_STUDENT:
        raise HTTPException(status_code=400, detail=f"Limit is {MAX_PORTIONS_PER_STUDENT} portion(s) per student so more people get some.")

    listing.portions_remaining -= portions
    claim_row = models.SurplusClaim(
        listing_id=listing.id, user_id=user.id, portions=portions, code=_new_code(db),
        expires_at=min(now + timedelta(minutes=CLAIM_HOLD_MINUTES), listing.safe_until),
    )
    db.add(claim_row)
    db.commit()
    db.refresh(claim_row)
    return claim_row


def pickup_claim(db: Session, code: str, now=None) -> models.SurplusClaim:
    now = now or now_local()
    claim_row = db.query(models.SurplusClaim).filter(models.SurplusClaim.code == code.strip().upper()).first()
    if not claim_row:
        raise HTTPException(status_code=404, detail="No claim with that code.")
    if claim_row.status == "picked_up":
        raise HTTPException(status_code=400, detail="This code was already used.")
    if claim_row.status != "reserved" or now > claim_row.expires_at:
        raise HTTPException(status_code=400, detail="This claim has expired.")
    claim_row.status = "picked_up"
    claim_row.picked_up_at = now
    maybe_close(claim_row.listing)
    db.commit()
    return claim_row


# ---------------------------------------------------------------- NGOs

def offer_to_ngos(db: Session, listing: models.SurplusListing, now=None, ngo_ids=None):
    now = now or now_local()
    if listing.status not in ACTIVE_LISTING:
        raise HTTPException(status_code=400, detail="This listing is no longer active.")
    if now >= listing.safe_until:
        raise HTTPException(status_code=400, detail="The safe window for this food is over.")
    if listing.portions_remaining <= 0:
        raise HTTPException(status_code=400, detail="No portions are left to donate.")

    query = db.query(models.NGOPartner).filter(models.NGOPartner.active == True)  # noqa: E712
    if ngo_ids:
        query = query.filter(models.NGOPartner.id.in_(ngo_ids))
    ngos = query.all()
    if not ngos:
        raise HTTPException(status_code=400, detail="No active NGO partners. Add one on the Rescue page.")

    for old in listing.donations:           # a re-offer replaces earlier unanswered offers
        if old.status == "offered":
            old.status = "expired"

    created = []
    for ngo in ngos:
        donation = models.Donation(
            listing_id=listing.id, ngo_id=ngo.id, portions=listing.portions_remaining,
            token=secrets.token_urlsafe(16), offered_at=now,
        )
        db.add(donation)
        link = f"{FRONTEND_BASE_URL}/ngo/respond/{donation.token}"
        notif.notify_external(
            db, ngo.email, "donation_offer",
            f"Food available for pickup: {listing.portions_remaining} portions of {listing.dish_description}",
            (f"Hello {ngo.contact_person or ngo.name},\n\nThe college mess has {listing.portions_remaining} portions of "
             f"{listing.dish_description} ready for collection. It must be collected before {_fmt_time(listing.safe_until)}.\n"
             "The first partner to accept gets it."),
            link=link, payload={"listing_id": listing.id, "ngo_id": ngo.id},
        )
        created.append(donation)

    listing.status = "offered_ngo"
    listing.ngo_offered_at = now
    db.commit()
    return created


def ngo_respond(db: Session, token: str, action: str, now=None) -> models.Donation:
    now = now or now_local()
    donation = db.query(models.Donation).filter(models.Donation.token == token).first()
    if not donation:
        raise HTTPException(status_code=404, detail="This offer link isn't valid.")
    listing = donation.listing
    if donation.status != "offered":
        raise HTTPException(status_code=400, detail=f"This offer is already {donation.status.replace('_', ' ')}.")
    if now >= listing.safe_until or listing.status not in ACTIVE_LISTING:
        donation.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="This offer has expired.")

    donation.responded_at = now
    if action == "decline":
        donation.status = "declined"
    else:
        donation.status = "accepted"
        for other in listing.donations:
            if other.id != donation.id and other.status == "offered":
                other.status = "expired"        # first to accept wins
        notif.notify_roles(
            db, ["kitchen", "admin"], "donation_accepted",
            f"{donation.ngo.name} will collect {donation.portions} portions",
            f"{donation.ngo.name} accepted {listing.dish_description}. Hand over before {_fmt_time(listing.safe_until)}, "
            "then record the pickup.", link="/surplus",
        )
    db.commit()
    return donation


def record_donation_pickup(db: Session, donation_id: int, portions_picked=None, now=None) -> models.Donation:
    now = now or now_local()
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if donation.status != "accepted":
        raise HTTPException(status_code=400, detail="Only an accepted donation can be marked as collected.")
    picked = donation.portions if portions_picked is None else portions_picked
    if picked > donation.portions:
        raise HTTPException(status_code=400, detail=f"Offer was for {donation.portions} portions.")
    donation.status = "picked_up"
    donation.picked_up_at = now
    donation.portions_picked = picked
    maybe_close(donation.listing)
    db.commit()
    return donation


# ---------------------------------------------------------------- housekeeping (called by the automation tick)

def maintenance(db: Session, now=None) -> dict:
    """Idempotent clean-up: expire unclaimed holds, hand leftovers to NGOs, expire food past its safe time."""
    now = now or now_local()
    out = {"claims_expired": 0, "listings_escalated": 0, "listings_closed": 0, "listings_expired": 0, "escalation_skipped": 0}

    for c in db.query(models.SurplusClaim).filter(models.SurplusClaim.status == "reserved", models.SurplusClaim.expires_at < now).all():
        c.status = "expired"
        if c.listing.status in ACTIVE_LISTING:
            c.listing.portions_remaining += c.portions       # the portion goes back on the shelf
        out["claims_expired"] += 1
    db.flush()

    for l in db.query(models.SurplusListing).filter(
            models.SurplusListing.status == "open_students", models.SurplusListing.student_window_ends <= now).all():
        if now >= l.safe_until:
            continue                                         # handled by the expiry step below
        if l.portions_remaining <= 0:
            if maybe_close(l):
                out["listings_closed"] += 1
            continue
        if AUTO_ESCALATE_TO_NGO:
            try:
                offer_to_ngos(db, l, now)
                out["listings_escalated"] += 1
            except HTTPException:
                out["escalation_skipped"] += 1               # e.g. no active NGO yet

    for l in db.query(models.SurplusListing).filter(
            models.SurplusListing.status.in_(ACTIVE_LISTING), models.SurplusListing.safe_until <= now).all():
        l.status = "expired"
        for d in l.donations:
            if d.status in ("offered", "accepted"):
                d.status = "expired"
        for c in l.claims:
            if c.status == "reserved":
                c.status = "expired"
        out["listings_expired"] += 1

    db.commit()
    return out

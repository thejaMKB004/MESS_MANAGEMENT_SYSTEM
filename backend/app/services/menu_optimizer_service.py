from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models

LOW_RATING_THRESHOLD = 3.0
MIN_FEEDBACK_COUNT = 3
MIN_DISLIKE_SKIPS = 2


def get_suggestions(db: Session, date_from=None, date_to=None):
    """Advisory-only: reads feedback ratings + 'dont_like_menu' skip reasons and
    suggests dishes to rotate out. Admins decide what to actually change."""

    fb_q = db.query(
        models.Feedback.dish_name,
        func.avg(models.Feedback.rating).label("avg_rating"),
        func.count(models.Feedback.id).label("n"),
    ).group_by(models.Feedback.dish_name)
    if date_from:
        fb_q = fb_q.filter(models.Feedback.date >= date_from)
    if date_to:
        fb_q = fb_q.filter(models.Feedback.date <= date_to)
    fb_rows = fb_q.all()

    # count "don't like menu" skips per day/meal, then map to dishes served that day
    skip_q = db.query(models.Attendance).filter(
        models.Attendance.status == models.AttendanceStatus.skip,
        models.Attendance.reason == "dont_like_menu",
    )
    if date_from:
        skip_q = skip_q.filter(models.Attendance.date >= date_from)
    if date_to:
        skip_q = skip_q.filter(models.Attendance.date <= date_to)
    skips = skip_q.all()

    dislike_counter = Counter()
    for s in skips:
        menu = db.query(models.Menu).filter(
            models.Menu.date == s.date, models.Menu.meal_type == s.meal_type
        ).first()
        if menu:
            for dish in (menu.dishes or []):
                dislike_counter[dish] += 1

    suggestions = []
    keep = []
    for row in fb_rows:
        dislikes = dislike_counter.get(row.dish_name, 0)
        entry = {
            "dish_name": row.dish_name,
            "avg_rating": round(row.avg_rating, 2),
            "feedback_count": row.n,
            "dont_like_menu_skips": dislikes,
        }
        if row.n >= MIN_FEEDBACK_COUNT and row.avg_rating < LOW_RATING_THRESHOLD and dislikes >= MIN_DISLIKE_SKIPS:
            entry["recommendation"] = "rotate_out"
            entry["reason"] = f"Low avg rating ({round(row.avg_rating,2)}) and {dislikes} 'don't like menu' skips linked to it."
            suggestions.append(entry)
        else:
            entry["recommendation"] = "keep"
            keep.append(entry)

    return {"rotate_out_suggestions": suggestions, "other_dishes": keep}

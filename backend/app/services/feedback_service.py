from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models


def dish_rating_trend(db: Session, dish_name: str, date_from=None, date_to=None):
    q = db.query(models.Feedback).filter(models.Feedback.dish_name == dish_name)
    if date_from:
        q = q.filter(models.Feedback.date >= date_from)
    if date_to:
        q = q.filter(models.Feedback.date <= date_to)
    rows = q.order_by(models.Feedback.date).all()

    tag_counter = Counter()
    daily = {}
    for r in rows:
        daily.setdefault(str(r.date), []).append(r.rating)
        for t in (r.tags or []):
            tag_counter[t] += 1

    trend = [{"date": d, "avg_rating": round(sum(v) / len(v), 2), "count": len(v)} for d, v in sorted(daily.items())]
    avg_overall = round(sum(r.rating for r in rows) / len(rows), 2) if rows else None

    return {
        "dish_name": dish_name,
        "average_rating": avg_overall,
        "total_feedback": len(rows),
        "trend": trend,
        "top_tags": tag_counter.most_common(5),
    }


def top_bottom_dishes(db: Session, limit: int = 5):
    rows = (
        db.query(models.Feedback.dish_name, func.avg(models.Feedback.rating).label("avg_rating"), func.count(models.Feedback.id).label("n"))
        .group_by(models.Feedback.dish_name)
        .having(func.count(models.Feedback.id) > 0)
        .all()
    )
    ranked = sorted(rows, key=lambda r: r.avg_rating, reverse=True)
    top = [{"dish_name": r.dish_name, "avg_rating": round(r.avg_rating, 2), "count": r.n} for r in ranked[:limit]]
    bottom = [{"dish_name": r.dish_name, "avg_rating": round(r.avg_rating, 2), "count": r.n} for r in ranked[-limit:][::-1]]
    return {"top": top, "bottom": bottom}

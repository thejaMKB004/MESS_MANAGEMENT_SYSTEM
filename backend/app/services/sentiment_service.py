"""Lightweight keyword-based sentiment scorer for complaints/feedback comments.
Not ML, but gives admins a quick negative/neutral/positive signal and auto-flags
severity without needing an external NLP service (good enough for a mini-project;
swap for a real model/API later if needed)."""

NEGATIVE_WORDS = {
    "bad", "worst", "terrible", "awful", "cold", "stale", "rotten", "dirty",
    "unhygienic", "insect", "hair", "raw", "undercooked", "burnt", "salty",
    "bland", "disgusting", "late", "rude", "never", "worse", "poor", "spoiled",
    "sick", "unsafe", "overcooked", "unhappy", "angry", "disappointed",
}
POSITIVE_WORDS = {
    "good", "great", "excellent", "tasty", "delicious", "clean", "fresh",
    "amazing", "love", "best", "happy", "nice", "improved", "quick", "friendly",
}


def score_sentiment(text: str) -> float:
    """Returns a score from -1 (very negative) to 1 (very positive)."""
    if not text:
        return 0.0
    words = [w.strip(".,!?\"'").lower() for w in text.split()]
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    total = neg + pos
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


def suggested_severity(text: str) -> str:
    score = score_sentiment(text)
    if score <= -0.5:
        return "high"
    if score < 0:
        return "medium"
    return "low"

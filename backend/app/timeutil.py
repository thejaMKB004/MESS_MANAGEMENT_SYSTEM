"""One place that decides what 'now' means.

The server may run in UTC (cloud) while the mess runs on local time. Every deadline,
reminder and surplus window uses now_local() so the two can never disagree.
"""
from datetime import datetime, timedelta, timezone, time, date
from .config import LOCAL_TZ_OFFSET_MINUTES, MEAL_START_TIMES, ATTENDANCE_DEADLINE_HOURS_BEFORE


def now_local() -> datetime:
    """Naive datetime in the mess's local timezone (default: IST)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=LOCAL_TZ_OFFSET_MINUTES)


def today_local() -> date:
    return now_local().date()


def meal_deadline(meal_date: date, meal_type: str) -> datetime:
    """Moment attendance confirmations close for a meal (meal start minus the configured lead time)."""
    start_hour = MEAL_START_TIMES[meal_type]
    return datetime.combine(meal_date, time(0, 0)) + timedelta(hours=start_hour - ATTENDANCE_DEADLINE_HOURS_BEFORE)

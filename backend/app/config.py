import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mess.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours
ATTENDANCE_DEADLINE_HOURS_BEFORE = 2  # confirmation must happen 2h before meal start

# rough meal start times used for deadline enforcement (24h clock)
MEAL_START_TIMES = {
    "breakfast": 8,
    "lunch": 13,
    "dinner": 20,
}

# used by waste + inventory cost estimates
DEFAULT_PORTION_COST_INR = 25

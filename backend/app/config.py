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

# ======================================================================
# Settings added for: kitchen production log, surplus rescue, automation
# Everything can be overridden with an environment variable.
# ======================================================================

# The mess's local timezone as a UTC offset in minutes (330 = India Standard Time).
# All deadline / scheduling logic runs on this clock instead of raw UTC.
LOCAL_TZ_OFFSET_MINUTES = int(os.getenv("LOCAL_TZ_OFFSET_MINUTES", "330"))

# --- cooking sheet (how much the kitchen should cook) ---
NON_RESPONDER_EAT_RATE = float(os.getenv("NON_RESPONDER_EAT_RATE", "0.5"))  # share of students who never answered but still turn up
COOKING_BUFFER_PCT = float(os.getenv("COOKING_BUFFER_PCT", "5"))            # safety margin on top of the estimate
PORTION_MULTIPLIER = {"half": 0.5, "regular": 1.0, "large": 1.5}

# --- surplus rescue ---
SURPLUS_SAFE_HOURS = float(os.getenv("SURPLUS_SAFE_HOURS", "3"))            # how long cooked food may be offered after it was cooked
SURPLUS_STUDENT_WINDOW_MINUTES = int(os.getenv("SURPLUS_STUDENT_WINDOW_MINUTES", "30"))
CLAIM_HOLD_MINUTES = int(os.getenv("CLAIM_HOLD_MINUTES", "30"))             # a student must collect within this time
MAX_PORTIONS_PER_STUDENT = int(os.getenv("MAX_PORTIONS_PER_STUDENT", "1"))
AUTO_ESCALATE_TO_NGO = os.getenv("AUTO_ESCALATE_TO_NGO", "true").lower() == "true"

# --- automation (background jobs) ---
AUTOMATION_ENABLED = os.getenv("AUTOMATION_ENABLED", "true").lower() == "true"
AUTOMATION_TICK_SECONDS = int(os.getenv("AUTOMATION_TICK_SECONDS", "60"))
REMINDER_MINUTES_BEFORE_DEADLINE = int(os.getenv("REMINDER_MINUTES_BEFORE_DEADLINE", "60"))
LOW_STOCK_CHECK_HOUR = int(os.getenv("LOW_STOCK_CHECK_HOUR", "17"))         # local hour after which tomorrow's stock is checked
WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", "8"))
EMAIL_STUDENT_REMINDERS = os.getenv("EMAIL_STUDENT_REMINDERS", "false").lower() == "true"

# --- optional email (if SMTP_HOST is empty, messages are only stored in the in-app outbox) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "mess@example.org")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")  # used to build links inside emails

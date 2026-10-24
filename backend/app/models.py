import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, JSON, Enum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base
from .timeutil import now_local


class RoleEnum(str, enum.Enum):
    student = "student"
    admin = "admin"
    kitchen = "kitchen"


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"


class AttendanceStatus(str, enum.Enum):
    will_eat = "will_eat"
    skip = "skip"


class ComplaintStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    roll_no = Column(String, nullable=True)
    hostel = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
    diet_restrictions = Column(JSON, default=list)   # e.g. ["vegetarian", "no_egg"]
    allergies = Column(JSON, default=list)            # e.g. ["peanuts", "gluten"]
    created_at = Column(DateTime, default=now_local)

    attendance = relationship("Attendance", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    complaints = relationship("Complaint", back_populates="user")


class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False, index=True)
    dishes = Column(JSON, default=list)  # list of dish names
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_local)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False, index=True)
    status = Column(Enum(AttendanceStatus), nullable=False)
    portion = Column(String, nullable=True)   # half | regular | large
    reason = Column(String, nullable=True)    # skip reason
    created_at = Column(DateTime, default=now_local)

    user = relationship("User", back_populates="attendance")
    checkin = relationship("MealCheckin", back_populates="attendance", uselist=False)


class MealCheckin(Base):
    """Records that a confirmed meal was actually collected (QR scan at counter).
    This closes the gap between predicted/confirmed counts and real consumption."""
    __tablename__ = "meal_checkins"

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=False, unique=True)
    checkin_time = Column(DateTime, default=now_local)
    method = Column(String, default="qr")  # qr | manual

    attendance = relationship("Attendance", back_populates="checkin")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    dish_name = Column(String, nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    tags = Column(JSON, default=list)         # e.g. ["too salty", "cold"]
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    user = relationship("User", back_populates="feedback")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low | medium | high
    description = Column(Text, nullable=False)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.open)
    sentiment_score = Column(Float, nullable=True)  # -1..1, computed on create
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_local)

    user = relationship("User", back_populates="complaints")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    unit = Column(String, nullable=False)          # kg, litre, pcs...
    cost_per_unit = Column(Float, default=0.0)
    stock_qty = Column(Float, default=0.0)


class DishIngredient(Base):
    """Links a dish name (as it appears on menus) to inventory items & qty per serving."""
    __tablename__ = "dish_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    dish_name = Column(String, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    qty_per_serving = Column(Float, nullable=False)

    item = relationship("InventoryItem")


class GuestBooking(Base):
    __tablename__ = "guest_bookings"

    id = Column(Integer, primary_key=True, index=True)
    booked_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    count = Column(Integer, default=1)
    created_at = Column(DateTime, default=now_local)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now_local)


# ======================================================================
# Kitchen production log, surplus rescue, notifications, automation
# ======================================================================

class KitchenLog(Base):
    """What the kitchen actually cooked and served for one meal.
    This is the ground truth: real waste = cooked - served - rescued."""
    __tablename__ = "kitchen_logs"
    __table_args__ = (UniqueConstraint("date", "meal_type", name="uq_kitchen_log_meal"),)

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False)
    cooked_portions = Column(Integer, nullable=False)
    served_portions = Column(Integer, nullable=False)
    leftover_portions = Column(Integer, nullable=False)
    recommended_portions = Column(Integer, nullable=True)   # what the cooking sheet advised at the time
    waste_reason = Column(String, nullable=True)            # over_production | unpopular_dish | low_turnout | spoilage | other
    notes = Column(Text, nullable=True)
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_local)
    updated_at = Column(DateTime, default=now_local, onupdate=now_local)


class SurplusListing(Base):
    """Leftover cooked food offered for rescue: students first, then NGO partners."""
    __tablename__ = "surplus_listings"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False)
    dish_description = Column(String, nullable=False)
    portions_total = Column(Integer, nullable=False)
    portions_remaining = Column(Integer, nullable=False)
    cooked_at = Column(DateTime, nullable=False)
    safe_until = Column(DateTime, nullable=False)            # after this the food must not be given out
    student_window_ends = Column(DateTime, nullable=False)
    held_safely = Column(Boolean, default=False)             # kitchen confirmed hot/cold holding
    status = Column(String, default="open_students")         # open_students | offered_ngo | closed | expired
    ngo_offered_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_local)

    claims = relationship("SurplusClaim", back_populates="listing")
    donations = relationship("Donation", back_populates="listing")


class SurplusClaim(Base):
    __tablename__ = "surplus_claims"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("surplus_listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    portions = Column(Integer, default=1)
    code = Column(String, unique=True, nullable=False)       # shown to the student, checked at the counter
    status = Column(String, default="reserved")              # reserved | picked_up | expired
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=now_local)
    picked_up_at = Column(DateTime, nullable=True)

    listing = relationship("SurplusListing", back_populates="claims")
    user = relationship("User")


class NGOPartner(Base):
    __tablename__ = "ngo_partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    area = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_local)


class Donation(Base):
    """One offer of surplus food to one NGO. The first NGO to accept wins; the others are expired."""
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("surplus_listings.id"), nullable=False, index=True)
    ngo_id = Column(Integer, ForeignKey("ngo_partners.id"), nullable=False)
    portions = Column(Integer, nullable=False)
    status = Column(String, default="offered")               # offered | accepted | declined | picked_up | expired
    token = Column(String, unique=True, nullable=False)      # secret in the emailed link, lets the NGO respond without an account
    offered_at = Column(DateTime, default=now_local)
    responded_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    portions_picked = Column(Integer, nullable=True)

    listing = relationship("SurplusListing", back_populates="donations")
    ngo = relationship("NGOPartner")


class Notification(Base):
    """In-app notification for a user, or an outgoing email for an external contact (e.g. an NGO)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    recipient_email = Column(String, nullable=True)
    kind = Column(String, nullable=False)    # reminder | last_call | cooking_sheet | anomaly | low_stock | weekly_report | donation_offer | donation_accepted
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    link = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=False)
    email_status = Column(String, default="none")   # none | skipped (no SMTP set up) | sent | failed
    created_at = Column(DateTime, default=now_local)

    user = relationship("User")


class AutomationRun(Base):
    """Log of every automated job. (job, run_key) is unique, which is what stops a job running twice."""
    __tablename__ = "automation_runs"
    __table_args__ = (UniqueConstraint("job", "run_key", name="uq_automation_job_key"),)

    id = Column(Integer, primary_key=True, index=True)
    job = Column(String, nullable=False, index=True)
    run_key = Column(String, nullable=False)
    status = Column(String, default="ok")    # ok | error
    details = Column(JSON, nullable=True)
    ran_at = Column(DateTime, default=now_local)

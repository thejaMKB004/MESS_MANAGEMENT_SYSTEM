import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, JSON, Enum, Text
)
from sqlalchemy.orm import relationship
from .database import Base


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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False, index=True)
    status = Column(Enum(AttendanceStatus), nullable=False)
    portion = Column(String, nullable=True)   # half | regular | large
    reason = Column(String, nullable=True)    # skip reason
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attendance")
    checkin = relationship("MealCheckin", back_populates="attendance", uselist=False)


class MealCheckin(Base):
    """Records that a confirmed meal was actually collected (QR scan at counter).
    This closes the gap between predicted/confirmed counts and real consumption."""
    __tablename__ = "meal_checkins"

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=False, unique=True)
    checkin_time = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

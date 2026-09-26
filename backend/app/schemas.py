from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    roll_no: Optional[str] = None
    hostel: Optional[str] = None
    role: str = "student"  # student | admin | kitchen


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    roll_no: Optional[str] = None
    hostel: Optional[str] = None
    role: str
    diet_restrictions: List[str] = []
    allergies: List[str] = []

    class Config:
        from_attributes = True


class DietProfileUpdate(BaseModel):
    diet_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    name: Optional[str] = None
    hostel: Optional[str] = None


# ---------- Menus ----------

class MenuCreate(BaseModel):
    date: date
    meal_type: str
    dishes: List[str]


class MenuUpdate(BaseModel):
    dishes: Optional[List[str]] = None


class MenuOut(BaseModel):
    id: int
    date: date
    meal_type: str
    dishes: List[str]

    class Config:
        from_attributes = True


# ---------- Attendance ----------

class AttendanceConfirm(BaseModel):
    date: date
    meal_type: str
    status: str  # will_eat | skip
    portion: Optional[str] = None
    reason: Optional[str] = None


class AttendanceOut(BaseModel):
    id: int
    user_id: int
    date: date
    meal_type: str
    status: str
    portion: Optional[str]
    reason: Optional[str]

    class Config:
        from_attributes = True


class CheckinRequest(BaseModel):
    attendance_id: int
    method: str = "qr"


# ---------- Feedback ----------

class FeedbackCreate(BaseModel):
    date: date
    meal_type: str
    dish_name: str
    rating: int = Field(ge=1, le=5)
    tags: List[str] = []
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    dish_name: str
    rating: int
    tags: List[str]
    comment: Optional[str]
    date: date
    meal_type: str

    class Config:
        from_attributes = True


# ---------- Complaints ----------

class ComplaintCreate(BaseModel):
    category: str
    severity: str  # low | medium | high
    description: str


class ComplaintStatusUpdate(BaseModel):
    status: str  # open | in_progress | resolved


class ComplaintOut(BaseModel):
    id: int
    category: str
    severity: str
    description: str
    status: str
    sentiment_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Inventory ----------

class InventoryItemCreate(BaseModel):
    name: str
    unit: str
    cost_per_unit: float = 0.0
    stock_qty: float = 0.0


class InventoryItemOut(InventoryItemCreate):
    id: int

    class Config:
        from_attributes = True


class DishIngredientCreate(BaseModel):
    dish_name: str
    item_id: int
    qty_per_serving: float


# ---------- Guest bookings ----------

class GuestBookingCreate(BaseModel):
    date: date
    meal_type: str
    count: int = 1


class GuestBookingOut(GuestBookingCreate):
    id: int
    booked_by: int

    class Config:
        from_attributes = True


# ---------- Generic ----------

class Msg(BaseModel):
    detail: str

from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, Field


MealLiteral = Literal["breakfast", "lunch", "dinner"]


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
    meal_type: MealLiteral
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
    meal_type: MealLiteral
    status: Literal["will_eat", "skip"]
    portion: Optional[Literal["half", "regular", "large"]] = None
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
    meal_type: MealLiteral
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
    severity: Literal["low", "medium", "high"]
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
    meal_type: MealLiteral
    count: int = 1


class GuestBookingOut(GuestBookingCreate):
    id: int
    booked_by: int

    class Config:
        from_attributes = True


# ---------- Generic ----------

class Msg(BaseModel):
    detail: str


# ---------- Kitchen log / surplus rescue / NGOs ----------

class KitchenLogUpsert(BaseModel):
    date: date
    meal_type: MealLiteral
    cooked_portions: int = Field(ge=0, le=5000)
    served_portions: int = Field(ge=0, le=5000)
    waste_reason: Optional[Literal["over_production", "unpopular_dish", "low_turnout", "spoilage", "other"]] = None
    notes: Optional[str] = None


class SurplusCreate(BaseModel):
    date: date
    meal_type: MealLiteral
    dish_description: str = Field(min_length=2)
    portions: int = Field(ge=1, le=5000)
    held_safely: bool                                   # kitchen must confirm safe holding
    cooked_minutes_ago: int = Field(default=0, ge=0, le=600)


class ClaimRequest(BaseModel):
    portions: int = Field(default=1, ge=1, le=5)


class PickupRequest(BaseModel):
    code: str


class OfferNgoRequest(BaseModel):
    ngo_ids: Optional[List[int]] = None


class NGOCreate(BaseModel):
    name: str
    email: EmailStr
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    area: Optional[str] = None


class NGOUpdate(BaseModel):
    active: Optional[bool] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    area: Optional[str] = None


class DonationRespond(BaseModel):
    action: Literal["accept", "decline"]


class DonationPickup(BaseModel):
    portions_picked: Optional[int] = Field(default=None, ge=0)


# ---------- Nutrition ----------

AllergenLiteral = Literal["peanuts", "tree_nuts", "gluten", "dairy", "soy", "shellfish", "egg"]


class DishNutritionUpsert(BaseModel):
    kcal: float = Field(ge=0, le=3000)
    protein_g: float = Field(default=0, ge=0, le=300)
    carbs_g: float = Field(default=0, ge=0, le=500)
    fat_g: float = Field(default=0, ge=0, le=300)
    fibre_g: float = Field(default=0, ge=0, le=100)
    food_type: Literal["veg", "egg", "non_veg"] = "veg"
    allergens: List[AllergenLiteral] = []


class IntakeCreate(BaseModel):
    date: date
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    source: Literal["mess", "other"]
    # mess entries: the server works out the food and nutrition from the menu
    portion: Optional[Literal["half", "regular", "large"]] = None
    # other entries: the student describes the food and enters the numbers
    description: Optional[str] = Field(default=None, max_length=120)
    kcal: Optional[float] = Field(default=None, ge=0, le=5000)
    protein_g: Optional[float] = Field(default=None, ge=0, le=300)
    carbs_g: Optional[float] = Field(default=None, ge=0, le=800)
    fat_g: Optional[float] = Field(default=None, ge=0, le=300)


class GoalUpdate(BaseModel):
    kcal_target: Optional[float] = Field(default=None, ge=1200, le=5000)
    protein_target_g: Optional[float] = Field(default=None, ge=10, le=300)

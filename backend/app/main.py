from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import models  # noqa: ensures models are registered before create_all
from .routers import (
    auth, users, menus, attendance, feedback, complaints,
    analytics, menu_optimizer, inventory, guest_bookings, impact,
    kitchen, surplus, ngos, donations, notifications, automation, nutrition,
)
from .config import AUTOMATION_ENABLED
from .services import automation_service

Base.metadata.create_all(bind=engine)

# fill in starting nutrition estimates for known dishes (never overwrites edits)
from .database import SessionLocal  # noqa: E402
from .services.nutrition_service import ensure_defaults  # noqa: E402
with SessionLocal() as _db:
    ensure_defaults(_db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # background jobs (reminders, cooking sheets, surplus clean-up...) run in a small thread
    if AUTOMATION_ENABLED:
        automation_service.start()
    yield
    automation_service.stop()


app = FastAPI(title="Mess Management System", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(menus.router)
app.include_router(attendance.router)
app.include_router(feedback.router)
app.include_router(complaints.router)
app.include_router(analytics.router)
app.include_router(menu_optimizer.router)
app.include_router(inventory.router)
app.include_router(guest_bookings.router)
app.include_router(impact.router)
app.include_router(kitchen.router)
app.include_router(surplus.router)
app.include_router(ngos.router)
app.include_router(donations.router)
app.include_router(donations.public_router)
app.include_router(notifications.router)
app.include_router(automation.router)
app.include_router(nutrition.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "mess-management-api", "docs": "/docs"}

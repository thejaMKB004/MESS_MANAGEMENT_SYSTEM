from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import models  # noqa: ensures models are registered before create_all
from .routers import (
    auth, users, menus, attendance, feedback, complaints,
    analytics, menu_optimizer, inventory, guest_bookings, impact,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mess Management System", version="1.0.0")

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


@app.get("/")
def root():
    return {"status": "ok", "service": "mess-management-api", "docs": "/docs"}

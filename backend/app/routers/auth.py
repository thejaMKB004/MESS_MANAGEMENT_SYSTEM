from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin
from ..security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_user(db: Session, payload: schemas.UserRegister, role: str) -> models.User:
    """Shared by both sign-up routes. The role is chosen by the CALLER, never read from the request."""
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        roll_no=payload.roll_no,
        hostel=payload.hostel,
        role=role,
        diet_restrictions=[],
        allergies=[],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    """Public sign-up. Always creates a student, whatever role the request asks for."""
    return _create_user(db, payload, role="student")


@router.post("/staff", response_model=schemas.UserOut)
def create_staff(payload: schemas.UserRegister, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Only a logged-in admin can create admin or kitchen accounts."""
    if payload.role not in ("admin", "kitchen"):
        raise HTTPException(status_code=400, detail="Role must be admin or kitchen")
    return _create_user(db, payload, role=payload.role)


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}

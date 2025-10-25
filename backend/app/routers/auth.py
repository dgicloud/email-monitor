from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..schemas import AuthRequest, AuthResponse
from ..models import User
from ..db import get_db
from ..auth import create_access_token, verify_password, get_password_hash

router = APIRouter(prefix="/login", tags=["auth"])

@router.post("", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return AuthResponse(access_token=token)

@router.post("/seed-admin")
def seed_admin(db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == "admin@example.com").first():
        return {"detail": "exists"}
    user = User(name="Admin", email="admin@example.com", password_hash=get_password_hash("admin123"))
    db.add(user)
    db.commit()
    return {"detail": "created"}

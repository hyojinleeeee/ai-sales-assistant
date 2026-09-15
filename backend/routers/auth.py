from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, verify_password
from database import get_db
from models import User
from schemas import LoginRequest, _build_response

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_public(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "sls_code": user.sls_code,
        "team": user.team,
        "position": user.position,
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다.")
    token = create_access_token(user)
    return _build_response({"access_token": token, "token_type": "bearer", "user": _user_public(user)})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _build_response(_user_public(user))

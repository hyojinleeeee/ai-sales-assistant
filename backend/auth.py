import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from models import User

# 교육용 데모 앱이므로 고정 값을 사용한다. 실제 서비스라면 반드시 환경변수로 분리해야 한다.
SECRET_KEY = "ai-sales-assistant-training-demo-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12

_bearer = HTTPBearer()


def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return check_password_hash(hashed, raw)


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "sls_code": user.sls_code,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증 정보가 유효하지 않습니다.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "사용자를 찾을 수 없거나 비활성화되었습니다.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자만 접근할 수 있습니다.")
    return user

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import hash_password, require_admin
from database import get_db
from models import Account, RepPerformance, User
from schemas import (
    AssignAccountsRequest,
    UserCreateRequest,
    UserUpdateRequest,
    _build_response,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_out(u: User, db: Session) -> dict:
    account_count = db.query(Account).filter(Account.rep_sls_code == u.sls_code).count()
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "display_name": u.display_name,
        "team": u.team,
        "position": u.position,
        "sls_code": u.sls_code,
        "emp_code": u.emp_code,
        "is_active": u.is_active,
        "account_count": account_count,
    }


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).filter(User.role == "sales").order_by(User.display_name).all()
    return _build_response([_user_out(u, db) for u in users])


@router.post("")
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "이미 존재하는 아이디입니다.")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=payload.role,
        team=payload.team,
        position=payload.position,
        sls_code=payload.sls_code,
        emp_code=payload.emp_code,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_response(_user_out(user, db))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "조직원을 찾을 수 없습니다.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _build_response(_user_out(user, db))


@router.put("/{user_id}/deactivate")
def deactivate_user(
    user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "조직원을 찾을 수 없습니다.")
    user.is_active = False
    db.commit()
    return _build_response({"id": user.id, "is_active": False})


@router.put("/{user_id}/assignments")
def assign_accounts(
    user_id: int,
    payload: AssignAccountsRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "조직원을 찾을 수 없습니다.")
    accounts = db.query(Account).filter(Account.code.in_(payload.account_codes)).all()
    for account in accounts:
        account.rep_sls_code = user.sls_code
    db.commit()
    return _build_response({"reassigned": [a.code for a in accounts]})


@router.get("/{user_id}/performance")
def user_performance(
    user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "조직원을 찾을 수 없습니다.")
    perf = db.query(RepPerformance).filter(RepPerformance.sls_code == user.sls_code).first()
    if not perf:
        return _build_response(None)
    return _build_response(
        {
            "sls_code": perf.sls_code,
            "rep_name": perf.rep_name,
            "team": perf.team,
            "target_revenue": perf.target_revenue,
            "actual_revenue": perf.actual_revenue,
            "achievement_rate": perf.achievement_rate,
            "quote_count": perf.quote_count,
            "order_count": perf.order_count,
            "conversion_rate": perf.conversion_rate,
            "kpi_grade": perf.kpi_grade,
            "rank": perf.rank,
        }
    )

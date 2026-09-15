from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import Account, User


def scoped_account_query(db: Session, user: User):
    """role=sales면 자신의 거래처만, admin이면 전체를 반환하는 쿼리."""
    query = db.query(Account)
    if user.role != "admin":
        query = query.filter(Account.rep_sls_code == user.sls_code)
    return query


def get_account_or_403(db: Session, user: User, code: str) -> Account:
    account = db.query(Account).filter(Account.code == code).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "거래처를 찾을 수 없습니다.")
    if user.role != "admin" and account.rep_sls_code != user.sls_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "담당 거래처가 아닙니다.")
    return account

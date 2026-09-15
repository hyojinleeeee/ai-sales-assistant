import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import ai_rules
from auth import get_current_user
from database import get_db
from models import Account, AccountInquirySignal, RiskAssessment, User
from scoping import get_account_or_403, scoped_account_query
from schemas import _build_response

router = APIRouter(prefix="/api/risk", tags=["risk"])


def _out(r: RiskAssessment, account_name: str) -> dict:
    return {
        "account_code": r.account_code,
        "account_name": account_name,
        "risk_tier": r.risk_tier,
        "risk_score": r.risk_score,
        "ai_findings": json.loads(r.ai_findings) if r.ai_findings else [],
        "recommended_action": r.recommended_action,
        "computed_at": r.computed_at.isoformat() if r.computed_at else None,
    }


@router.get("")
def list_risk(
    tier: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    accounts = scoped_account_query(db, user).all()
    codes = [a.code for a in accounts]
    names = {a.code: a.name for a in accounts}
    query = db.query(RiskAssessment).filter(RiskAssessment.account_code.in_(codes))
    if tier:
        query = query.filter(RiskAssessment.risk_tier == tier)
    rows = query.order_by(RiskAssessment.risk_score.desc()).all()
    return _build_response([_out(r, names[r.account_code]) for r in rows])


@router.get("/{code}")
def get_risk(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = get_account_or_403(db, user, code)
    r = db.query(RiskAssessment).filter(RiskAssessment.account_code == code).first()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "위험도 정보가 없습니다.")
    return _build_response(_out(r, account.name))


@router.post("/{code}/recompute")
def recompute_risk(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = get_account_or_403(db, user, code)
    inquiries = (
        db.query(AccountInquirySignal)
        .filter(AccountInquirySignal.account_code == code)
        .all()
    )
    rows = [
        {"voc_tag": i.voc_tag, "repeat_inquiry": i.repeat_inquiry, "rating": i.rating}
        for i in inquiries
    ]
    result = ai_rules.compute_risk(rows, account.contract_end_date)

    r = db.query(RiskAssessment).filter(RiskAssessment.account_code == code).first()
    r.risk_tier = result["risk_tier"]
    r.risk_score = result["risk_score"]
    r.ai_findings = json.dumps(result["ai_findings"], ensure_ascii=False)
    r.recommended_action = result["recommended_action"]
    r.computed_at = datetime.utcnow()
    db.commit()
    return _build_response(_out(r, account.name))

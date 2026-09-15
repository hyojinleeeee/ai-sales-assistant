from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import ai_rules
from auth import get_current_user
from database import get_db
from models import (
    Account,
    AccountInquirySignal,
    AccountService,
    AccountTransaction,
    Opportunity,
    User,
)
from scoping import get_account_or_403, scoped_account_query
from schemas import OpportunityStatusRequest, _build_response

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _out(o: Opportunity, account_name: str) -> dict:
    return {
        "account_code": o.account_code,
        "account_name": account_name,
        "current_service_summary": o.current_service_summary,
        "recommended_service": o.recommended_service,
        "ai_rationale": o.ai_rationale,
        "opportunity_score": o.opportunity_score,
        "recommended_action": o.recommended_action,
        "status": o.status,
        "computed_at": o.computed_at.isoformat() if o.computed_at else None,
    }


@router.get("")
def list_opportunities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = scoped_account_query(db, user).all()
    codes = [a.code for a in accounts]
    names = {a.code: a.name for a in accounts}
    opps = (
        db.query(Opportunity)
        .filter(Opportunity.account_code.in_(codes))
        .order_by(Opportunity.opportunity_score.desc())
        .all()
    )
    return _build_response([_out(o, names[o.account_code]) for o in opps])


@router.get("/{code}")
def get_opportunity(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = get_account_or_403(db, user, code)
    opp = db.query(Opportunity).filter(Opportunity.account_code == code).first()
    if not opp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "영업기회 정보가 없습니다.")
    return _build_response(_out(opp, account.name))


def _recompute_one(db: Session, account: Account) -> Opportunity:
    services = db.query(AccountService).filter(AccountService.account_code == account.code).all()
    owned = {s.service_name for s in services}

    all_revenues = [a.annual_revenue for a in db.query(Account).all()]

    txns = db.query(AccountTransaction).filter(AccountTransaction.account_code == account.code).all()
    dates = [t.txn_date for t in txns if t.txn_date]
    if dates:
        latest = max(datetime.strptime(d, "%Y-%m-%d") for d in dates)
        days_since = (ai_rules.SIMULATED_TODAY - latest).days
    else:
        days_since = 999

    inquiries = (
        db.query(AccountInquirySignal)
        .filter(AccountInquirySignal.account_code == account.code)
        .all()
    )
    interest_tags = {"제안", "재구매의향", "단순문의"}
    interest_rate = (
        sum(1 for i in inquiries if i.voc_tag in interest_tags) / len(inquiries)
        if inquiries
        else 0
    )

    all_services_map = {}
    for a in db.query(Account).all():
        svc = db.query(AccountService).filter(AccountService.account_code == a.code).all()
        all_services_map[a.code] = {s.service_name for s in svc}
    co_occurrence = ai_rules.build_service_co_occurrence(all_services_map)

    result = ai_rules.compute_opportunity(
        account.code, owned, account.annual_revenue, all_revenues, interest_rate, days_since, co_occurrence
    )

    opp = db.query(Opportunity).filter(Opportunity.account_code == account.code).first()
    opp.current_service_summary = ", ".join(sorted(owned)) if owned else "없음"
    opp.recommended_service = result["recommended_service"]
    opp.ai_rationale = result["ai_rationale"]
    opp.opportunity_score = result["opportunity_score"]
    opp.recommended_action = result["recommended_action"]
    opp.computed_at = datetime.utcnow()
    db.commit()
    return opp


@router.post("/{code}/recompute")
def recompute_opportunity(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = get_account_or_403(db, user, code)
    opp = _recompute_one(db, account)
    return _build_response(_out(opp, account.name))


@router.put("/{code}/status")
def update_status(
    code: str,
    payload: OpportunityStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = get_account_or_403(db, user, code)
    opp = db.query(Opportunity).filter(Opportunity.account_code == code).first()
    if not opp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "영업기회 정보가 없습니다.")
    opp.status = payload.status
    db.commit()
    return _build_response(_out(opp, account.name))

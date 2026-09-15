from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import ai_rules
from auth import get_current_user
from database import get_db
from models import (
    Account,
    AccountInquirySignal,
    AccountTransaction,
    Opportunity,
    Proposal,
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

    result = ai_rules.compute_opportunity(
        {"industry": account.industry, "contract_size_tier": account.contract_size_tier},
        account.annual_revenue,
        all_revenues,
        interest_rate,
        days_since,
    )

    opp = db.query(Opportunity).filter(Opportunity.account_code == account.code).first()
    opp.current_service_summary = result["current_service_summary"]
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


@router.get("/{code}/market-fit")
def get_market_fit(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    이미 거래 중인 고객 대상 업셀(위 opportunity_score)과는 별개로, 이 거래처가
    이트너스의 실제 경영지원 사업(BPO) 신규 영업 대상으로서 얼마나 매력적인지를
    평가한다. 시장 전망 + 우리 회사와의 적합도를 계산해 반환한다 (참고용, 저장 안 함).
    """
    account = get_account_or_403(db, user, code)
    all_revenues = [a.annual_revenue for a in db.query(Account).all()]
    txns = db.query(AccountTransaction).filter(AccountTransaction.account_code == code).all()

    result = ai_rules.analyze_market_fit(
        {
            "name": account.name,
            "industry": account.industry,
            "region": account.region,
            "contract_size_tier": account.contract_size_tier,
            "annual_revenue": account.annual_revenue,
        },
        all_revenues,
        [{"txn_date": t.txn_date, "amount": t.amount} for t in txns],
    )
    return _build_response(result)


@router.post("/{code}/etners-proposal")
def create_etners_proposal(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    시장성·적합도 분석 결과를 바탕으로 이 거래처를 신규 영업 대상으로 "리스트업"하는
    이트너스 맞춤 제안서를 생성해 저장한다 (기존 제안서 목록/편집 화면에서 바로 보임).
    """
    account = get_account_or_403(db, user, code)
    all_revenues = [a.annual_revenue for a in db.query(Account).all()]
    txns = db.query(AccountTransaction).filter(AccountTransaction.account_code == code).all()

    market_fit = ai_rules.analyze_market_fit(
        {
            "name": account.name,
            "industry": account.industry,
            "region": account.region,
            "contract_size_tier": account.contract_size_tier,
            "annual_revenue": account.annual_revenue,
        },
        all_revenues,
        [{"txn_date": t.txn_date, "amount": t.amount} for t in txns],
    )
    draft = ai_rules.generate_etners_market_proposal(
        {"name": account.name, "industry": account.industry, "contract_size_tier": account.contract_size_tier},
        market_fit,
    )

    proposal = Proposal(
        account_code=account.code,
        rep_user_id=user.id,
        customer_situation=draft["customer_situation"],
        key_problems="\n".join(draft["key_problems"]),
        solution_direction=draft["solution_direction"],
        recommended_service=draft["recommended_service"],
        expected_effect=draft["expected_effect"],
        next_steps=draft["next_steps"],
        status="초안",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return _build_response({"id": proposal.id, "account_code": proposal.account_code})


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

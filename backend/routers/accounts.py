from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin
from database import get_db
from models import (
    Account,
    AccountInquirySignal,
    AccountPipelineState,
    AccountService,
    AccountTransaction,
    Opportunity,
    RiskAssessment,
    User,
)
from scoping import get_account_or_403, scoped_account_query
from schemas import AccountUpdateRequest, ReassignRequest, _build_response

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _account_summary(a: Account, db: Session) -> dict:
    opp = db.query(Opportunity).filter(Opportunity.account_code == a.code).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.account_code == a.code).first()
    stage = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code == a.code)
        .first()
    )
    return {
        "code": a.code,
        "name": a.name,
        "industry": a.industry,
        "region": a.region,
        "credit_grade": a.credit_grade,
        "contract_size_tier": a.contract_size_tier,
        "rep_sls_code": a.rep_sls_code,
        "contract_start_date": a.contract_start_date,
        "contract_end_date": a.contract_end_date,
        "annual_revenue": a.annual_revenue,
        "main_contact_name": a.main_contact_name,
        "main_contact_phone": a.main_contact_phone,
        "current_stage": stage.current_stage if stage else None,
        "opportunity_score": opp.opportunity_score if opp else None,
        "risk_tier": risk.risk_tier if risk else None,
    }


def _bulk_summaries(accounts: list[Account], db: Session) -> list[dict]:
    """
    _account_summary()를 계정 수만큼 반복 호출하면 계정당 3개씩 쿼리가 나가
    (원격 Postgres에서) 60개 거래처 기준 180번의 왕복이 발생한다. 대신 딱 3번의
    쿼리로 전체를 가져와 메모리에서 매칭한다.
    """
    codes = [a.code for a in accounts]
    if not codes:
        return []
    opp_by_code = {
        o.account_code: o
        for o in db.query(Opportunity).filter(Opportunity.account_code.in_(codes)).all()
    }
    risk_by_code = {
        r.account_code: r
        for r in db.query(RiskAssessment).filter(RiskAssessment.account_code.in_(codes)).all()
    }
    stage_by_code = {
        s.account_code: s
        for s in db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code.in_(codes))
        .all()
    }
    result = []
    for a in accounts:
        opp = opp_by_code.get(a.code)
        risk = risk_by_code.get(a.code)
        stage = stage_by_code.get(a.code)
        result.append(
            {
                "code": a.code,
                "name": a.name,
                "industry": a.industry,
                "region": a.region,
                "credit_grade": a.credit_grade,
                "contract_size_tier": a.contract_size_tier,
                "rep_sls_code": a.rep_sls_code,
                "contract_start_date": a.contract_start_date,
                "contract_end_date": a.contract_end_date,
                "annual_revenue": a.annual_revenue,
                "main_contact_name": a.main_contact_name,
                "main_contact_phone": a.main_contact_phone,
                "current_stage": stage.current_stage if stage else None,
                "opportunity_score": opp.opportunity_score if opp else None,
                "risk_tier": risk.risk_tier if risk else None,
            }
        )
    return result


@router.get("")
def list_accounts(
    industry: str | None = None,
    risk_tier: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scoped_account_query(db, user)
    if industry:
        query = query.filter(Account.industry == industry)
    accounts = query.order_by(Account.name).all()
    result = _bulk_summaries(accounts, db)
    if risk_tier:
        result = [r for r in result if r["risk_tier"] == risk_tier]
    return _build_response(result)


@router.get("/{code}")
def get_account(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = get_account_or_403(db, user, code)
    services = db.query(AccountService).filter(AccountService.account_code == code).all()
    transactions = (
        db.query(AccountTransaction)
        .filter(AccountTransaction.account_code == code)
        .order_by(AccountTransaction.txn_date.desc())
        .limit(20)
        .all()
    )
    inquiries = (
        db.query(AccountInquirySignal)
        .filter(AccountInquirySignal.account_code == code)
        .order_by(AccountInquirySignal.inquiry_date.desc())
        .all()
    )
    opp = db.query(Opportunity).filter(Opportunity.account_code == code).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.account_code == code).first()
    stage = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code == code)
        .first()
    )

    import json as _json

    return _build_response(
        {
            **_account_summary(account, db),
            "biz_reg_no": account.biz_reg_no,
            "services": [
                {
                    "service_name": s.service_name,
                    "category": s.category,
                    "first_txn_date": s.first_txn_date,
                    "last_txn_date": s.last_txn_date,
                    "txn_count": s.txn_count,
                }
                for s in services
            ],
            "recent_transactions": [
                {
                    "txn_date": t.txn_date,
                    "item_category": t.item_category,
                    "item_name": t.item_name,
                    "amount": t.amount,
                    "txn_type": t.txn_type,
                }
                for t in transactions
            ],
            "inquiries": [
                {
                    "inquiry_date": i.inquiry_date,
                    "type_major": i.type_major,
                    "type_minor": i.type_minor,
                    "voc_tag": i.voc_tag,
                    "rating": i.rating,
                    "repeat_inquiry": i.repeat_inquiry,
                    "channel": i.channel,
                }
                for i in inquiries
            ],
            "opportunity": {
                "recommended_service": opp.recommended_service,
                "ai_rationale": opp.ai_rationale,
                "opportunity_score": opp.opportunity_score,
                "recommended_action": opp.recommended_action,
                "status": opp.status,
            }
            if opp
            else None,
            "risk": {
                "risk_tier": risk.risk_tier,
                "risk_score": risk.risk_score,
                "ai_findings": _json.loads(risk.ai_findings) if risk.ai_findings else [],
                "recommended_action": risk.recommended_action,
            }
            if risk
            else None,
            "current_stage": stage.current_stage if stage else None,
        }
    )


@router.put("/{code}")
def update_account(
    code: str,
    payload: AccountUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    account = db.query(Account).filter(Account.code == code).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "거래처를 찾을 수 없습니다.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    return _build_response(_account_summary(account, db))


@router.put("/{code}/reassign")
def reassign_account(
    code: str,
    payload: ReassignRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    account = db.query(Account).filter(Account.code == code).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "거래처를 찾을 수 없습니다.")
    rep = db.query(User).filter(User.sls_code == payload.new_sls_code).first()
    if not rep:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "존재하지 않는 담당자 코드입니다.")
    account.rep_sls_code = payload.new_sls_code
    db.commit()
    return _build_response(_account_summary(account, db))

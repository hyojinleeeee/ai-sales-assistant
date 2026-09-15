from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin
from database import get_db
from models import (
    Account,
    AccountPipelineState,
    Meeting,
    Opportunity,
    Proposal,
    RiskAssessment,
    User,
)
from schemas import _build_response

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/admin")
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    total_accounts = db.query(Account).count()
    new_opportunities = db.query(Opportunity).filter(Opportunity.status == "신규").count()
    in_progress = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.current_stage.in_(["고객접촉", "미팅", "제안", "협의"]))
        .count()
    )
    upcoming_meetings = db.query(Meeting).filter(Meeting.status == "예정").count()
    proposals_in_progress = db.query(Proposal).filter(Proposal.status.in_(["초안", "편집됨"])).count()
    at_risk = (
        db.query(RiskAssessment).filter(RiskAssessment.risk_tier.in_(["주의", "위험"])).count()
    )

    # 담당자 수만큼 반복 쿼리하면(원격 Postgres 기준 담당자당 3번, 최대 120번 왕복) 매우
    # 느려지므로, 전체 거래처/위험도/기회 데이터를 한 번씩만 가져와 메모리에서 집계한다.
    reps = db.query(User).filter(User.role == "sales", User.is_active == True).all()  # noqa: E712
    all_accounts = db.query(Account.code, Account.rep_sls_code).all()
    codes_by_rep: dict[str, list[str]] = {}
    for code, rep_sls_code in all_accounts:
        codes_by_rep.setdefault(rep_sls_code, []).append(code)

    risky_codes = {
        r.account_code
        for r in db.query(RiskAssessment.account_code)
        .filter(RiskAssessment.risk_tier.in_(["주의", "위험"]))
        .all()
    }
    new_opp_codes = {
        o.account_code
        for o in db.query(Opportunity.account_code).filter(Opportunity.status == "신규").all()
    }

    rep_status = []
    for rep in reps:
        codes = codes_by_rep.get(rep.sls_code, [])
        rep_status.append(
            {
                "sls_code": rep.sls_code,
                "display_name": rep.display_name,
                "team": rep.team,
                "account_count": len(codes),
                "at_risk_count": sum(1 for c in codes if c in risky_codes),
                "new_opportunity_count": sum(1 for c in codes if c in new_opp_codes),
            }
        )

    return _build_response(
        {
            "total_accounts": total_accounts,
            "new_opportunities": new_opportunities,
            "in_progress_accounts": in_progress,
            "upcoming_meetings": upcoming_meetings,
            "proposals_in_progress": proposals_in_progress,
            "at_risk_accounts": at_risk,
            "rep_status": rep_status,
        }
    )


@router.get("/sales")
def sales_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.rep_sls_code == user.sls_code).all()
    codes = [a.code for a in accounts]
    names = {a.code: a.name for a in accounts}

    new_opps = (
        db.query(Opportunity)
        .filter(Opportunity.account_code.in_(codes), Opportunity.status == "신규")
        .order_by(Opportunity.opportunity_score.desc())
        .limit(5)
        .all()
    )
    today_meetings = (
        db.query(Meeting)
        .filter(Meeting.account_code.in_(codes), Meeting.status == "예정")
        .all()
    )
    proposal_needed = (
        db.query(Meeting)
        .filter(Meeting.account_code.in_(codes), Meeting.status == "완료")
        .all()
    )
    at_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.account_code.in_(codes), RiskAssessment.risk_tier.in_(["주의", "위험"]))
        .order_by(RiskAssessment.risk_score.desc())
        .all()
    )

    return _build_response(
        {
            "new_opportunities": [
                {
                    "account_code": o.account_code,
                    "account_name": names.get(o.account_code),
                    "recommended_service": o.recommended_service,
                    "opportunity_score": o.opportunity_score,
                }
                for o in new_opps
            ],
            "today_meetings": [
                {
                    "id": m.id,
                    "account_code": m.account_code,
                    "account_name": names.get(m.account_code),
                    "meeting_date": m.meeting_date,
                }
                for m in today_meetings
            ],
            "proposal_needed": [
                {
                    "meeting_id": m.id,
                    "account_code": m.account_code,
                    "account_name": names.get(m.account_code),
                }
                for m in proposal_needed
            ],
            "at_risk_accounts": [
                {
                    "account_code": r.account_code,
                    "account_name": names.get(r.account_code),
                    "risk_tier": r.risk_tier,
                }
                for r in at_risk
            ],
            "total_accounts": len(accounts),
        }
    )

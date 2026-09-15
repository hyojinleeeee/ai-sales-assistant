import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import ai_rules
from auth import get_current_user
from database import get_db
from models import (
    AccountPipelineState,
    Meeting,
    Opportunity,
    Proposal,
    RiskAssessment,
    User,
)
from scoping import get_account_or_403, scoped_account_query
from schemas import ProposalCreateRequest, ProposalUpdateRequest, _build_response

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


def _out(p: Proposal) -> dict:
    return {
        "id": p.id,
        "account_code": p.account_code,
        "rep_user_id": p.rep_user_id,
        "opportunity_id": p.opportunity_id,
        "meeting_id": p.meeting_id,
        "customer_situation": p.customer_situation,
        "key_problems": p.key_problems,
        "solution_direction": p.solution_direction,
        "recommended_service": p.recommended_service,
        "expected_effect": p.expected_effect,
        "next_steps": p.next_steps,
        "status": p.status,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_proposals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = scoped_account_query(db, user).all()
    codes = [a.code for a in accounts]
    proposals = (
        db.query(Proposal)
        .filter(Proposal.account_code.in_(codes))
        .order_by(Proposal.updated_at.desc())
        .all()
    )
    return _build_response([_out(p) for p in proposals])


@router.post("")
def create_proposal(
    payload: ProposalCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = get_account_or_403(db, user, payload.account_code)
    opp = db.query(Opportunity).filter(Opportunity.account_code == account.code).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.account_code == account.code).first()
    stage = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code == account.code)
        .first()
    )
    meeting = None
    if payload.meeting_id:
        meeting = db.query(Meeting).filter(Meeting.id == payload.meeting_id).first()

    meeting_dict = None
    if meeting and meeting.extracted_pain_points:
        meeting_dict = {"extracted_pain_points": json.loads(meeting.extracted_pain_points)}

    draft = ai_rules.generate_proposal_draft(
        {
            "name": account.name,
            "contract_size_tier": account.contract_size_tier,
            "annual_revenue": account.annual_revenue,
            "current_stage": stage.current_stage if stage else "영업기회 발견",
        },
        {"recommended_service": opp.recommended_service if opp else None},
        {"ai_findings": json.loads(risk.ai_findings) if risk and risk.ai_findings else []},
        meeting_dict,
    )

    proposal = Proposal(
        account_code=account.code,
        rep_user_id=user.id,
        opportunity_id=opp.id if opp else None,
        meeting_id=payload.meeting_id,
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
    return _build_response(_out(proposal))


@router.get("/{proposal_id}")
def get_proposal(proposal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "제안서를 찾을 수 없습니다.")
    get_account_or_403(db, user, proposal.account_code)
    return _build_response(_out(proposal))


@router.put("/{proposal_id}")
def update_proposal(
    proposal_id: int,
    payload: ProposalUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "제안서를 찾을 수 없습니다.")
    get_account_or_403(db, user, proposal.account_code)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proposal, field, value)
    proposal.status = "편집됨"
    db.commit()
    db.refresh(proposal)
    return _build_response(_out(proposal))

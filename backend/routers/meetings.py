import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import ai_rules
from auth import get_current_user
from database import get_db
from models import (
    Account,
    AccountInquirySignal,
    AccountService,
    Meeting,
    Opportunity,
    RiskAssessment,
    User,
)
from scoping import get_account_or_403, scoped_account_query
from schemas import MeetingCreateRequest, MeetingNotesRequest, _build_response

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _out(m: Meeting) -> dict:
    return {
        "id": m.id,
        "account_code": m.account_code,
        "rep_user_id": m.rep_user_id,
        "meeting_date": m.meeting_date,
        "status": m.status,
        "pre_brief": json.loads(m.pre_brief) if m.pre_brief else None,
        "notes_raw": m.notes_raw,
        "extracted_requirements": json.loads(m.extracted_requirements) if m.extracted_requirements else None,
        "extracted_pain_points": json.loads(m.extracted_pain_points) if m.extracted_pain_points else None,
        "extracted_interest_services": json.loads(m.extracted_interest_services) if m.extracted_interest_services else None,
        "extracted_customer_reaction": m.extracted_customer_reaction,
        "extracted_followup_items": json.loads(m.extracted_followup_items) if m.extracted_followup_items else None,
        "extracted_next_action": m.extracted_next_action,
        "extracted_next_schedule": m.extracted_next_schedule,
    }


@router.get("")
def list_meetings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = scoped_account_query(db, user).all()
    codes = [a.code for a in accounts]
    meetings = (
        db.query(Meeting)
        .filter(Meeting.account_code.in_(codes))
        .order_by(Meeting.meeting_date.desc())
        .all()
    )
    return _build_response([_out(m) for m in meetings])


@router.post("")
def create_meeting(
    payload: MeetingCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = get_account_or_403(db, user, payload.account_code)
    services = db.query(AccountService).filter(AccountService.account_code == account.code).all()
    inquiries = (
        db.query(AccountInquirySignal)
        .filter(AccountInquirySignal.account_code == account.code)
        .order_by(AccountInquirySignal.inquiry_date.desc())
        .all()
    )
    opp = db.query(Opportunity).filter(Opportunity.account_code == account.code).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.account_code == account.code).first()

    brief = ai_rules.generate_pre_meeting_brief(
        {
            "name": account.name,
            "industry": account.industry,
            "contract_size_tier": account.contract_size_tier,
        },
        [s.service_name for s in services],
        [
            {
                "inquiry_date": i.inquiry_date,
                "type_major": i.type_major,
                "voc_tag": i.voc_tag,
            }
            for i in inquiries
        ],
        {"risk_tier": risk.risk_tier if risk else "정상"},
        {
            "recommended_service": opp.recommended_service if opp else None,
            "opportunity_score": opp.opportunity_score if opp else 0,
        },
    )

    meeting = Meeting(
        account_code=account.code,
        rep_user_id=user.id,
        meeting_date=payload.meeting_date,
        status="예정",
        pre_brief=json.dumps(brief, ensure_ascii=False),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _build_response(_out(meeting))


@router.get("/{meeting_id}")
def get_meeting(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "미팅을 찾을 수 없습니다.")
    get_account_or_403(db, user, meeting.account_code)
    return _build_response(_out(meeting))


@router.put("/{meeting_id}/notes")
def submit_notes(
    meeting_id: int,
    payload: MeetingNotesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "미팅을 찾을 수 없습니다.")
    get_account_or_403(db, user, meeting.account_code)

    extracted = ai_rules.extract_meeting_fields(payload.notes_raw)

    meeting.notes_raw = payload.notes_raw
    meeting.status = "완료"
    meeting.extracted_requirements = json.dumps(extracted["extracted_requirements"], ensure_ascii=False)
    meeting.extracted_pain_points = json.dumps(extracted["extracted_pain_points"], ensure_ascii=False)
    meeting.extracted_interest_services = json.dumps(extracted["extracted_interest_services"], ensure_ascii=False)
    meeting.extracted_customer_reaction = extracted["extracted_customer_reaction"]
    meeting.extracted_followup_items = json.dumps(extracted["extracted_followup_items"], ensure_ascii=False)
    meeting.extracted_next_action = extracted["extracted_next_action"]
    meeting.extracted_next_schedule = extracted["extracted_next_schedule"]
    db.commit()
    db.refresh(meeting)
    return _build_response(_out(meeting))

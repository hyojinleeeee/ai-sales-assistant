from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_rules import PIPELINE_STAGES
from auth import get_current_user
from database import get_db
from models import AccountPipelineState, PipelineStageHistory, User
from scoping import get_account_or_403, scoped_account_query
from schemas import StageUpdateRequest, _build_response

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/summary")
def pipeline_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = scoped_account_query(db, user).all()
    codes = [a.code for a in accounts]
    states = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code.in_(codes))
        .all()
    )
    by_rep: dict[str, dict[str, int]] = {}
    counts = {stage: 0 for stage in PIPELINE_STAGES}
    code_to_rep = {a.code: a.rep_sls_code for a in accounts}
    for s in states:
        counts[s.current_stage] = counts.get(s.current_stage, 0) + 1
        rep = code_to_rep.get(s.account_code, "미배정")
        by_rep.setdefault(rep, {stage: 0 for stage in PIPELINE_STAGES})
        by_rep[rep][s.current_stage] += 1

    return _build_response(
        {
            "stages": PIPELINE_STAGES,
            "counts": counts,
            "by_rep": by_rep,
            "total": len(states),
        }
    )


@router.put("/{code}/stage")
def update_stage(
    code: str,
    payload: StageUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.stage not in PIPELINE_STAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "올바르지 않은 영업 단계입니다.")
    get_account_or_403(db, user, code)
    state = (
        db.query(AccountPipelineState)
        .filter(AccountPipelineState.account_code == code)
        .first()
    )
    if not state:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "파이프라인 상태가 없습니다.")

    prev_history = (
        db.query(PipelineStageHistory)
        .filter(
            PipelineStageHistory.account_code == code,
            PipelineStageHistory.exited_at.is_(None),
        )
        .order_by(PipelineStageHistory.entered_at.desc())
        .first()
    )
    if prev_history:
        prev_history.exited_at = datetime.utcnow()

    state.current_stage = payload.stage
    state.entered_at = datetime.utcnow()
    state.updated_by = user.id
    db.add(
        PipelineStageHistory(account_code=code, stage=payload.stage, note=payload.note)
    )
    db.commit()
    return _build_response({"account_code": code, "current_stage": payload.stage})

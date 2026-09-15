from typing import Optional

from pydantic import BaseModel


def _build_response(data=None, error_message: Optional[str] = None) -> dict:
    return {"success": error_message is None, "data": data, "error_message": error_message}


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    display_name: str
    role: str = "sales"
    team: Optional[str] = None
    position: Optional[str] = None
    sls_code: Optional[str] = None
    emp_code: Optional[str] = None


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    team: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None


class AssignAccountsRequest(BaseModel):
    account_codes: list[str]


class AccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    credit_grade: Optional[str] = None
    contract_size_tier: Optional[str] = None
    contract_end_date: Optional[str] = None
    main_contact_name: Optional[str] = None
    main_contact_phone: Optional[str] = None


class ReassignRequest(BaseModel):
    new_sls_code: str


class OpportunityStatusRequest(BaseModel):
    status: str


class StageUpdateRequest(BaseModel):
    stage: str
    note: Optional[str] = None


class MeetingCreateRequest(BaseModel):
    account_code: str
    meeting_date: str


class MeetingNotesRequest(BaseModel):
    notes_raw: str


class ProposalCreateRequest(BaseModel):
    account_code: str
    opportunity_id: Optional[int] = None
    meeting_id: Optional[int] = None


class ProposalUpdateRequest(BaseModel):
    customer_situation: Optional[str] = None
    key_problems: Optional[str] = None
    solution_direction: Optional[str] = None
    recommended_service: Optional[str] = None
    expected_effect: Optional[str] = None
    next_steps: Optional[str] = None

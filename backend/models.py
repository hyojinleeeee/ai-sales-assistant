import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


def now():
    return datetime.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin" | "sales"
    emp_code = Column(String, nullable=True)
    sls_code = Column(String, nullable=True, unique=True, index=True)
    display_name = Column(String, nullable=False)
    team = Column(String, nullable=True)
    position = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=now)


class Account(Base):
    __tablename__ = "accounts"

    code = Column(String, primary_key=True)  # 거래처코드, e.g. VND001
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    region = Column(String, nullable=True)
    credit_grade = Column(String, nullable=True)
    contract_size_tier = Column(String, nullable=True)  # A/B/C
    rep_sls_code = Column(String, ForeignKey("users.sls_code"), nullable=True, index=True)
    contract_start_date = Column(String, nullable=True)
    contract_end_date = Column(String, nullable=True)
    annual_revenue = Column(Float, nullable=True)  # 연간총매출액(원)
    annual_purchase = Column(Float, nullable=True)  # 연간총매입액(원)
    biz_reg_no = Column(String, nullable=True)
    main_contact_name = Column(String, nullable=True)
    main_contact_phone = Column(String, nullable=True)
    annual_txn_count = Column(Integer, nullable=True)
    avg_txn_amount = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=now, onupdate=now)

    services = relationship("AccountService", back_populates="account")
    transactions = relationship("AccountTransaction", back_populates="account")
    inquiries = relationship("AccountInquirySignal", back_populates="account")
    opportunity = relationship("Opportunity", back_populates="account", uselist=False)
    risk = relationship("RiskAssessment", back_populates="account", uselist=False)
    pipeline_state = relationship(
        "AccountPipelineState", back_populates="account", uselist=False
    )


class AccountService(Base):
    __tablename__ = "account_services"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    service_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    first_txn_date = Column(String, nullable=True)
    last_txn_date = Column(String, nullable=True)
    txn_count = Column(Integer, default=0)

    account = relationship("Account", back_populates="services")


class AccountTransaction(Base):
    __tablename__ = "account_transactions"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    txn_date = Column(String, nullable=True)
    item_category = Column(String, nullable=True)
    item_name = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    txn_type = Column(String, nullable=True)  # 매출 | 매입

    account = relationship("Account", back_populates="transactions")


class AccountInquirySignal(Base):
    __tablename__ = "account_inquiry_signals"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    inquiry_date = Column(String, nullable=True)
    type_major = Column(String, nullable=True)
    type_minor = Column(String, nullable=True)
    voc_tag = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    nps = Column(Float, nullable=True)
    repeat_inquiry = Column(Boolean, default=False)
    channel = Column(String, nullable=True)

    account = relationship("Account", back_populates="inquiries")


class RepPerformance(Base):
    __tablename__ = "rep_performance"

    id = Column(Integer, primary_key=True)
    sls_code = Column(String, index=True)
    rep_name = Column(String, nullable=True)
    team = Column(String, nullable=True)
    target_revenue = Column(Float, nullable=True)
    actual_revenue = Column(Float, nullable=True)
    achievement_rate = Column(Float, nullable=True)
    quote_count = Column(Integer, nullable=True)
    order_count = Column(Integer, nullable=True)
    conversion_rate = Column(Float, nullable=True)
    kpi_grade = Column(String, nullable=True)
    rank = Column(Integer, nullable=True)


class AccountPipelineState(Base):
    __tablename__ = "account_pipeline_state"

    account_code = Column(String, ForeignKey("accounts.code"), primary_key=True)
    current_stage = Column(String, nullable=False)
    entered_at = Column(DateTime, default=now)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    account = relationship("Account", back_populates="pipeline_state")


class PipelineStageHistory(Base):
    __tablename__ = "pipeline_stage_history"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    stage = Column(String, nullable=False)
    entered_at = Column(DateTime, default=now)
    exited_at = Column(DateTime, nullable=True)
    note = Column(String, nullable=True)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), unique=True, index=True)
    current_service_summary = Column(Text, nullable=True)
    recommended_service = Column(String, nullable=True)
    ai_rationale = Column(Text, nullable=True)
    opportunity_score = Column(Float, nullable=False, default=0)
    recommended_action = Column(String, nullable=True)
    status = Column(String, default="신규")  # 신규/진행중/전환완료/기각
    computed_at = Column(DateTime, default=now)

    account = relationship("Account", back_populates="opportunity")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), unique=True, index=True)
    risk_tier = Column(String, nullable=False)  # 정상/관심/주의/위험
    risk_score = Column(Float, nullable=False, default=0)
    ai_findings = Column(Text, nullable=True)  # JSON list of strings
    recommended_action = Column(String, nullable=True)
    computed_at = Column(DateTime, default=now)

    account = relationship("Account", back_populates="risk")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    rep_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    meeting_date = Column(String, nullable=True)
    status = Column(String, default="예정")  # 예정/완료
    pre_brief = Column(Text, nullable=True)  # JSON
    notes_raw = Column(Text, nullable=True)
    extracted_requirements = Column(Text, nullable=True)  # JSON list
    extracted_pain_points = Column(Text, nullable=True)  # JSON list
    extracted_interest_services = Column(Text, nullable=True)  # JSON list
    extracted_customer_reaction = Column(String, nullable=True)
    extracted_followup_items = Column(Text, nullable=True)  # JSON list
    extracted_next_action = Column(String, nullable=True)
    extracted_next_schedule = Column(String, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)
    account_code = Column(String, ForeignKey("accounts.code"), index=True)
    rep_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    customer_situation = Column(Text, nullable=True)
    key_problems = Column(Text, nullable=True)
    solution_direction = Column(Text, nullable=True)
    recommended_service = Column(String, nullable=True)
    expected_effect = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    status = Column(String, default="초안")  # 초안/편집됨
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

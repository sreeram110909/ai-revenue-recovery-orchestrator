"""SQLAlchemy Relational Database Models."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import declarative_base, relationship
from ..schemas.enums import CaseStatus, CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy

Base = declarative_base()


class RecoveryCaseModel(Base):
    __tablename__ = "recovery_cases"

    id = Column(String, primary_key=True, index=True)
    case_type = Column(Enum(CaseType), nullable=False)
    customer_id = Column(String, nullable=False, index=True)
    masked_customer_email = Column(String, nullable=False)
    masked_customer_phone = Column(String, nullable=False)
    customer_segment = Column(String, default="STANDARD")
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    gateway_reference_id = Column(String, nullable=False)
    failure_code = Column(String, nullable=False)
    failure_description = Column(String, nullable=False)
    failure_category = Column(Enum(FailureCategory), nullable=False)
    attempts_count = Column(Integer, default=0)
    max_attempts_allowed = Column(Integer, default=3)
    last_attempt_at = Column(DateTime, nullable=True)
    subscription_details = Column(JSON, nullable=True)
    current_status = Column(Enum(CaseStatus), default=CaseStatus.DETECTED, index=True)
    recommended_strategy = Column(Enum(RecoveryStrategy), nullable=True)
    strategy_confidence = Column(Float, nullable=True)
    strategy_rationale = Column(String, nullable=True)
    verified_recovered_amount = Column(Float, default=0.0)
    is_escalated = Column(Boolean, default=False)
    escalation_reason = Column(String, nullable=True)
    provenance = Column(String, default="SYNTHETIC_DATA_RESULT")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    policy_outcome = Column(Enum(PolicyOutcome), nullable=True)
    details = Column(JSON, default=dict)

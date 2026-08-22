"""SQLAlchemy ORM Models for Recovery Cases and Action Execution.

Maps the Pydantic RecoveryCase schema to relational storage.
Supports both PostgreSQL (production) and SQLite (local dev fallback).
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON, Enum as SAEnum,
)
from ..database import Base
from ..schemas.enums import CaseStatus, CaseType, FailureCategory, RecoveryStrategy, TruthProvenance


class RecoveryCaseModel(Base):
    """ORM model for the core RecoveryCase entity."""
    __tablename__ = "recovery_cases"

    id = Column(String(64), primary_key=True, index=True)
    case_type = Column(String(32), nullable=False)  # CaseType enum value
    customer_id = Column(String(64), nullable=False, index=True)
    masked_customer_email = Column(String(256), nullable=False)
    masked_customer_phone = Column(String(32), nullable=False)
    customer_segment = Column(String(32), default="STANDARD")
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    gateway_reference_id = Column(String(128), nullable=False)
    failure_code = Column(String(128), nullable=False)
    failure_description = Column(Text, nullable=False)
    failure_category = Column(String(48), nullable=False)  # FailureCategory enum value
    attempts_count = Column(Integer, default=0)
    max_attempts_allowed = Column(Integer, default=3)
    last_attempt_at = Column(DateTime, nullable=True)

    # Subscription details (stored as JSON for flexibility)
    subscription_details = Column(JSON, nullable=True)

    # Lifecycle
    current_status = Column(String(32), default=CaseStatus.DETECTED.value, nullable=False)
    recommended_strategy = Column(String(32), nullable=True)
    strategy_confidence = Column(Float, nullable=True)
    strategy_rationale = Column(Text, nullable=True)

    # Policy evaluation snapshot (stored as JSON)
    policy_evaluation = Column(JSON, nullable=True)

    # Execution record (stored as JSON)
    executed_action = Column(JSON, nullable=True)

    # Verification record (stored as JSON)
    verification_outcome = Column(JSON, nullable=True)
    verified_recovered_amount = Column(Float, default=0.0)

    # Escalation
    is_escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)

    # Provenance
    provenance = Column(String(32), default=TruthProvenance.SYNTHETIC_DATA_RESULT.value)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

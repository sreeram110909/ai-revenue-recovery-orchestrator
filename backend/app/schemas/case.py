"""Pydantic Schemas for Recovery Cases, Action Execution, and Verification."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from .enums import CaseStatus, CaseType, FailureCategory, RecoveryStrategy, TruthProvenance
from .policy import PolicyCheckResult


class SubscriptionMetadata(BaseModel):
    subscription_id: str
    plan_name: str
    billing_interval: str  # MONTHLY | YEARLY
    mandate_status: str  # ACTIVE | EXPIRED | REVOKED | INVALID
    mandate_expiry_date: Optional[str] = None
    requires_afa: bool = False


class ActionExecutionRecord(BaseModel):
    action_id: str
    action_type: RecoveryStrategy
    status: str  # PENDING | SUCCESS | FAILED
    executed_at: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    gateway_response: Optional[Dict[str, Any]] = None
    payment_link_url: Optional[str] = None
    notification_log: Optional[Dict[str, Any]] = None
    provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT


class VerificationRecord(BaseModel):
    verified: bool
    status: str  # PAID | FAILED | PENDING | EXPIRED
    verified_at: datetime
    recovered_amount: float
    verification_method: str  # GATEWAY_API_CHECK | WEBHOOK_EVENT | TEST_SIMULATION
    details: str
    provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT


class RecoveryCase(BaseModel):
    id: str
    case_type: CaseType
    customer_id: str
    masked_customer_email: str
    masked_customer_phone: str
    customer_segment: str = "STANDARD"
    amount: float
    currency: str = "INR"
    gateway_reference_id: str
    failure_code: str
    failure_description: str
    failure_category: FailureCategory
    attempts_count: int = 0
    max_attempts_allowed: int = 3
    last_attempt_at: Optional[datetime] = None
    subscription_details: Optional[SubscriptionMetadata] = None
    current_status: CaseStatus = CaseStatus.DETECTED
    recommended_strategy: Optional[RecoveryStrategy] = None
    strategy_confidence: Optional[float] = None
    strategy_rationale: Optional[str] = None
    policy_evaluation: Optional[PolicyCheckResult] = None
    executed_action: Optional[ActionExecutionRecord] = None
    verification_outcome: Optional[VerificationRecord] = None
    verified_recovered_amount: float = 0.0
    is_escalated: bool = False
    escalation_reason: Optional[str] = None
    provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

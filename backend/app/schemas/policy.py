"""Pydantic Schemas for Policy Configuration and Evaluation Results."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from .enums import FailureCategory, PolicyOutcome, RecoveryStrategy


class PolicyConfig(BaseModel):
    """Configurable Demonstration Policy Model.
    
    NOTE: Values such as ₹15,000 limit, max 3 retries, and 4h cooldown are demonstration
    safety policies for the buildathon. Production values must be verified against current
    payment methods, merchant risk thresholds, and applicable regulations.
    """
    max_retry_attempts: int = Field(default=3, description="Maximum automated retries per case")
    retry_cooldown_hours: float = Field(default=4.0, description="Minimum hours between retries")
    automated_recovery_amount_limit: float = Field(default=15000.0, description="Max amount for auto action without human sign-off")
    non_retryable_categories: List[FailureCategory] = Field(
        default=[FailureCategory.RISK_SECURITY_BLOCK, FailureCategory.EXPIRED_INSTRUMENT, FailureCategory.MANDATE_EXPIRED_INVALID],
        description="Failure categories where automated retries are strictly blocked"
    )
    allow_invalid_mandate_auto_retry: bool = Field(default=False)


class RuleEvaluationDetail(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    reason: str
    suggested_outcome: Optional[PolicyOutcome] = None


class PolicyCheckResult(BaseModel):
    outcome: PolicyOutcome
    passed: bool
    proposed_strategy: RecoveryStrategy
    approved_strategy: RecoveryStrategy
    evaluations: List[RuleEvaluationDetail]
    reasons: List[str]
    downgrade_reason: Optional[str] = None
    escalation_reason: Optional[str] = None
    evaluated_at: datetime
    config_snapshot: PolicyConfig

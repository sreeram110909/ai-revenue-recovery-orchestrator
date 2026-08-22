"""Pydantic Schemas for Audit Trail and Batch Metrics."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .enums import CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance


class AuditLogEntry(BaseModel):
    """Immutable audit trail entry recording a single event in case lifecycle.

    Every diagnosis, strategy selection, policy evaluation, action dispatch,
    and verification step produces an audit entry. Entries are append-only.
    """
    id: Optional[str] = None
    case_id: str
    event_type: str  # CASE_CREATED | DIAGNOSIS_COMPLETED | STRATEGY_SCORED | POLICY_EVALUATED | ACTION_DISPATCHED | VERIFICATION_COMPLETED | STATUS_CHANGED | ESCALATED | STOPPED
    event_timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = "SYSTEM"  # SYSTEM | POLICY_ENGINE | DIAGNOSIS_AGENT | EXECUTION_SERVICE | VERIFICATION_SERVICE
    previous_status: Optional[CaseStatus] = None
    new_status: Optional[CaseStatus] = None
    policy_outcome: Optional[PolicyOutcome] = None
    strategy: Optional[RecoveryStrategy] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT


class BatchMetricsResponse(BaseModel):
    """Aggregate metrics for a batch evaluation run.

    Revenue is counted strictly upon gateway status verification,
    not on action dispatch.
    """
    batch_id: str
    total_cases: int = 0
    total_amount_at_risk: float = 0.0
    verified_recovered_amount: float = 0.0
    recovery_rate_percent: float = 0.0
    cases_allowed: int = 0
    cases_blocked: int = 0
    cases_downgraded: int = 0
    cases_escalated: int = 0
    cases_stopped: int = 0
    policy_violations: int = 0  # Must always be 0 in a correct system
    provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

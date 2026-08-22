"""Pydantic Schemas for Milestone 5: Batch Evaluation, Metrics, and Benchmark Baselines.

Defines schemas for synthetic dataset generation, baseline definitions,
per-case evaluation records, aggregate metrics, and evaluation run summaries.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .enums import CaseStatus, CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, TruthProvenance


class BaselineStrategyType(str, Enum):
    """Evaluation strategy / baseline approaches."""
    NO_ACTION = "NO_ACTION"
    RETRY_ONLY = "RETRY_ONLY"
    AI_REVENUE_RECOVERY_ORCHESTRATOR = "AI_REVENUE_RECOVERY_ORCHESTRATOR"


class GroundTruthMetadata(BaseModel):
    """Ground truth characteristics for synthetic recovery cases.

    Independent of the orchestrator to ensure fair benchmark evaluation.
    """
    scenario_name: str
    expected_failure_category: FailureCategory
    is_retryable_failure: bool
    is_high_value: bool
    is_mandate_invalid: bool = False
    is_security_risk: bool = False
    expected_policy_outcome: Optional[PolicyOutcome] = None
    expected_ideal_strategy: Optional[RecoveryStrategy] = None
    simulated_payment_link_will_pay: bool = False
    simulated_retry_will_succeed: bool = False
    simulated_update_method_will_succeed: bool = False
    notes: Optional[str] = None


class EvaluationCaseResult(BaseModel):
    """Granular, traceable evaluation record for a single evaluated case."""
    case_id: str
    batch_id: str
    strategy_type: BaselineStrategyType
    workflow_type: CaseType
    failure_category: FailureCategory
    amount: float
    selected_strategy: Optional[RecoveryStrategy] = None
    policy_outcome: Optional[PolicyOutcome] = None
    execution_status: Optional[str] = None  # "SUCCESS", "FAILED", "BLOCKED", "SKIPPED", "NONE"
    verification_status: Optional[str] = None  # "PAID", "CAPTURED", "CREATED", "FAILED", "NONE"
    verified_recovered_amount: float = 0.0
    final_status: CaseStatus
    is_escalated: bool = False
    is_stopped: bool = False
    policy_violation: bool = False
    violation_details: Optional[str] = None
    truth_provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT
    audit_event_count: int = 0
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class BatchMetrics(BaseModel):
    """Aggregate performance metrics for a single baseline or orchestrator run."""
    strategy_type: BaselineStrategyType
    total_cases: int
    total_revenue_at_risk: float
    eligible_cases: int
    recovery_attempts: int
    successful_actions: int
    verified_recovered_revenue: float
    revenue_recovery_rate: float  # verified_recovered_revenue / total_revenue_at_risk
    case_recovery_rate: float  # cases with verified revenue / total_cases
    policy_blocks: int
    human_escalations: int
    stopped_cases: int
    failed_actions: int
    policy_violations: int = 0


class BatchRunMetadata(BaseModel):
    """Metadata recorded for batch reproducibility and auditing."""
    batch_id: str
    dataset_version: str = "v1.0"
    random_seed: int = 42
    policy_config_version: str = "1.0.0-demo"
    scoring_config_version: str = "1.0.0-demo"
    code_version: str = "1.0.0"
    batch_timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_cases: int = 0


class BatchRunSummary(BaseModel):
    """Comprehensive summary of a batch evaluation run across all 3 strategies."""
    metadata: BatchRunMetadata
    metrics: Dict[str, BatchMetrics]  # Keyed by BaselineStrategyType value
    case_results: List[EvaluationCaseResult] = Field(default_factory=list)
    comparison_summary: Dict[str, Any] = Field(default_factory=dict)
    generated_artifacts: Dict[str, str] = Field(default_factory=dict)

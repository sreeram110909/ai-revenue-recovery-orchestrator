"""LangGraph Typed State for the AI Revenue Recovery Orchestrator.

Defines the typed workflow state capturing the entire recovery lifecycle.
Compatible with LangGraph StateGraph dictionary merging and checkpointing.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from ..schemas.enums import CaseStatus, RecoveryStrategy, TruthProvenance
from ..schemas.case import ActionExecutionRecord, RecoveryCase, VerificationRecord
from ..schemas.diagnosis import DiagnosisResult, StrategyRankingResult
from ..schemas.policy import PolicyCheckResult


class RecoveryWorkflowState(TypedDict, total=False):
    """Explicit, serializable TypedDict state for LangGraph workflow."""

    case_id: str
    case: Optional[RecoveryCase]

    # Stage 1: Evidence
    evidence: Optional[Dict[str, Any]]

    # Stage 2: Diagnosis
    diagnosis: Optional[DiagnosisResult]
    candidate_strategies: Optional[List[RecoveryStrategy]]

    # Stage 3: Strategy Scoring
    strategy_ranking: Optional[StrategyRankingResult]
    recommended_strategy: Optional[RecoveryStrategy]

    # Stage 4: Policy Evaluation
    policy_result: Optional[PolicyCheckResult]

    # Stage 5: Execution
    execution_record: Optional[ActionExecutionRecord]

    # Stage 6: Verification
    verification_record: Optional[VerificationRecord]

    # Stage 7: State Resolution & Provenance
    final_state: Optional[CaseStatus]
    truth_provenance: TruthProvenance
    error: Optional[str]

    # Testing / Mocking injection hooks
    mock_gateway_response: Optional[Dict[str, Any]]
    mock_gateway_state: Optional[Dict[str, Any]]
    gateway_payment_id: Optional[str]

    # Audit tracking in memory
    audit_events: List[str]

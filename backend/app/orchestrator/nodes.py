"""Pure LangGraph Orchestration Nodes for Revenue Recovery.

Each node delegates directly to the already-approved components from Milestones 1–3
without duplicating any business logic inside the nodes.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ..schemas.enums import CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance
from ..schemas.case import RecoveryCase
from ..agents.evidence import extract_evidence, validate_no_pii_leakage
from ..agents.diagnosis import DiagnosisAgent
from ..agents.strategy_scorer import StrategyScorer
from ..policies.engine import PolicyEngine
from ..services.execution_service import ExecutionService
from ..services.verification_service import VerificationService
from ..services.audit_service import AuditService
from ..repositories.case_repository import CaseRepository

logger = logging.getLogger(__name__)


class WorkflowNodes:
    """Container for pure LangGraph node functions with injected services."""

    def __init__(
        self,
        diagnosis_agent: Optional[DiagnosisAgent] = None,
        strategy_scorer: Optional[StrategyScorer] = None,
        policy_engine: Optional[PolicyEngine] = None,
        execution_service: Optional[ExecutionService] = None,
        verification_service: Optional[VerificationService] = None,
        audit_service: Optional[AuditService] = None,
        session: Optional[Session] = None,
    ):
        self.diagnosis_agent = diagnosis_agent or DiagnosisAgent(api_key=None)
        self.strategy_scorer = strategy_scorer or StrategyScorer()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_service = audit_service or AuditService(session=session)
        self.execution_service = execution_service or ExecutionService(
            audit_service=self.audit_service, session=session
        )
        self.verification_service = verification_service or VerificationService(
            audit_service=self.audit_service, session=session
        )
        self.case_repository = CaseRepository(session) if session else None

    def detect_and_load(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 1: Ingest and load the recovery case."""
        case_id = state.get("case_id", "")
        case: Optional[RecoveryCase] = state.get("case")

        if not case and self.case_repository and case_id:
            db_case = self.case_repository.get_by_id(case_id)
            if db_case:
                # Reconstruct RecoveryCase if needed from DB
                pass

        if not case:
            logger.error("Node detect_and_load failed: Case not provided in state.")
            return {"error": "Case not found", "final_state": CaseStatus.CLOSED_UNRECOVERABLE}

        provenance = state.get("truth_provenance", case.provenance)

        # Audit CASE_INGESTED
        self.audit_service.log_event(
            case_id=case.id,
            event_type="CASE_INGESTED",
            actor="SYSTEM",
            previous_status=case.current_status,
            new_status=case.current_status,
            details={"case_type": case.case_type.value, "amount": case.amount},
            provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("CASE_INGESTED")

        return {
            "case_id": case.id,
            "case": case,
            "truth_provenance": provenance,
            "audit_events": audit_events,
        }

    def extract_evidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 2: Extract sanitized evidence with strict PII redaction."""
        case: RecoveryCase = state["case"]
        provenance = state.get("truth_provenance", case.provenance)

        # Check if case is already in a terminal/frozen state
        if case.current_status in [
            CaseStatus.VERIFIED_RECOVERED,
            CaseStatus.ESCALATED,
            CaseStatus.STOPPED,
            CaseStatus.CLOSED_UNRECOVERABLE,
        ]:
            logger.info("Case '%s' is in terminal state '%s'. Skipping further extraction.", case.id, case.current_status.value)
            return {"final_state": case.current_status}

        evidence = extract_evidence(case)
        validate_no_pii_leakage(evidence)

        self.audit_service.log_event(
            case_id=case.id,
            event_type="EVIDENCE_EXTRACTED",
            actor="SYSTEM",
            previous_status=case.current_status,
            new_status=case.current_status,
            details={"extracted_fields": list(evidence.keys())},
            provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("EVIDENCE_EXTRACTED")

        return {
            "evidence": evidence,
            "audit_events": audit_events,
        }

    def diagnose(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 3: Bounded AI diagnosis with deterministic fallback."""
        case: RecoveryCase = state["case"]
        provenance = state.get("truth_provenance", case.provenance)

        diagnosis = self.diagnosis_agent.diagnose(case)
        case.recommended_strategy = diagnosis.candidate_strategies[0] if diagnosis.candidate_strategies else None
        case.strategy_confidence = diagnosis.confidence
        case.strategy_rationale = diagnosis.rationale
        case.current_status = CaseStatus.DIAGNOSED

        self.audit_service.log_event(
            case_id=case.id,
            event_type="DIAGNOSIS_COMPLETED",
            actor="DIAGNOSIS_AGENT",
            previous_status=CaseStatus.DETECTED,
            new_status=CaseStatus.DIAGNOSED,
            details={
                "diagnosis": diagnosis.diagnosis,
                "failure_category": diagnosis.failure_category.value,
                "is_fallback": diagnosis.is_fallback,
                "confidence": diagnosis.confidence,
            },
            provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("DIAGNOSIS_COMPLETED")

        return {
            "diagnosis": diagnosis,
            "candidate_strategies": diagnosis.candidate_strategies,
            "case": case,
            "audit_events": audit_events,
        }

    def score_strategy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 4: Deterministic strategy scoring."""
        case: RecoveryCase = state["case"]
        diagnosis = state["diagnosis"]
        provenance = state.get("truth_provenance", case.provenance)

        ranking = self.strategy_scorer.score(case, diagnosis)
        recommended = ranking.recommended_strategy

        self.audit_service.log_event(
            case_id=case.id,
            event_type="STRATEGY_SCORED",
            actor="SYSTEM",
            previous_status=case.current_status,
            new_status=case.current_status,
            strategy=recommended,
            details={
                "recommended_strategy": recommended.value,
                "top_score": ranking.ranked_strategies[0].score if ranking.ranked_strategies else 0,
                "confidence": ranking.recommended_confidence,
            },
            provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("STRATEGY_SCORED")

        return {
            "strategy_ranking": ranking,
            "recommended_strategy": recommended,
            "audit_events": audit_events,
        }

    def evaluate_policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 5: Deterministic Policy Engine guardrail evaluation."""
        case: RecoveryCase = state["case"]
        recommended_strategy = state["recommended_strategy"]
        provenance = state.get("truth_provenance", case.provenance)

        policy_result = self.policy_engine.evaluate(case, recommended_strategy)
        case.policy_evaluation = policy_result

        self.audit_service.log_event(
            case_id=case.id,
            event_type="POLICY_EVALUATION",
            actor="POLICY_ENGINE",
            previous_status=case.current_status,
            new_status=case.current_status,
            policy_outcome=policy_result.outcome,
            strategy=policy_result.approved_strategy,
            details={
                "passed": policy_result.passed,
                "outcome": policy_result.outcome.value,
                "reasons": policy_result.reasons,
            },
            provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("POLICY_EVALUATION")

        return {
            "policy_result": policy_result,
            "case": case,
            "audit_events": audit_events,
        }

    def execute_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 6: Policy-approved action execution via ExecutionService."""
        case: RecoveryCase = state["case"]
        policy_result = state["policy_result"]
        mock_response = state.get("mock_gateway_response")
        provenance = state.get("truth_provenance", case.provenance)

        execution_record = self.execution_service.execute_policy_approved_action(
            case=case,
            policy_result=policy_result,
            mock_gateway_response=mock_response,
            truth_provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("ACTION_DISPATCHED")

        return {
            "execution_record": execution_record,
            "case": case,
            "audit_events": audit_events,
        }

    def verify_outcome(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 7: Post-action outcome verification via VerificationService."""
        case: RecoveryCase = state["case"]
        mock_state = state.get("mock_gateway_state")
        payment_id = state.get("gateway_payment_id")
        provenance = state.get("truth_provenance", case.provenance)

        verification_record = self.verification_service.verify_recovery_outcome(
            case=case,
            gateway_payment_id=payment_id,
            mock_gateway_state=mock_state,
            truth_provenance=provenance,
        )

        audit_events = list(state.get("audit_events", []))
        audit_events.append("VERIFICATION_RECEIVED")

        return {
            "verification_record": verification_record,
            "case": case,
            "audit_events": audit_events,
        }

    def resolve_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 8: Map final verified/action outcome to canonical case state."""
        case: Optional[RecoveryCase] = state.get("case")
        if not case:
            return {"final_state": CaseStatus.CLOSED_UNRECOVERABLE}

        provenance = state.get("truth_provenance", case.provenance)
        policy_result = state.get("policy_result")
        verification_record = state.get("verification_record")

        # Handle Policy-directed escalations/stops
        if policy_result:
            if policy_result.outcome == PolicyOutcome.STOP or policy_result.approved_strategy == RecoveryStrategy.STOP:
                case.current_status = CaseStatus.STOPPED
            elif policy_result.outcome == PolicyOutcome.ESCALATE or policy_result.approved_strategy == RecoveryStrategy.HUMAN_ESCALATION:
                case.is_escalated = True
                case.escalation_reason = policy_result.escalation_reason or "Policy mandated escalation."
                case.current_status = CaseStatus.ESCALATED

        # Audit final resolved state
        audit_events = list(state.get("audit_events", []))
        if case.current_status == CaseStatus.VERIFIED_RECOVERED:
            audit_events.append("CASE_RECOVERED")
        elif case.current_status == CaseStatus.ESCALATED:
            audit_events.append("CASE_ESCALATED")
        elif case.current_status == CaseStatus.STOPPED:
            audit_events.append("CASE_STOPPED")

        if self.case_repository:
            try:
                self.case_repository.save(case)
            except Exception as e:
                logger.error("Failed to save resolved case '%s': %s", case.id, e)

        return {
            "case": case,
            "final_state": case.current_status,
            "audit_events": audit_events,
        }

    def log_audit(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node 9: Final audit trail synchronization."""
        return state

"""Batch Evaluation Runner for AI Revenue Recovery Orchestrator.

Runs all 3 strategies (NO_ACTION, RETRY_ONLY, AI_REVENUE_RECOVERY_ORCHESTRATOR)
against the exact same deterministic dataset with 100% isolated case states.
Zero live Razorpay API calls are made during the benchmark.
"""

import copy
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

from ..schemas.enums import CaseStatus, CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, TruthProvenance
from ..schemas.case import RecoveryCase
from ..schemas.evaluation import (
    BaselineStrategyType,
    BatchMetrics,
    BatchRunMetadata,
    BatchRunSummary,
    EvaluationCaseResult,
    GroundTruthMetadata,
)
from ..schemas.policy import PolicyConfig
from ..policies.engine import PolicyEngine
from ..agents.diagnosis import DiagnosisAgent
from ..agents.strategy_scorer import StrategyScorer
from ..services.razorpay_service import RazorpayService
from ..services.audit_service import AuditService
from ..services.execution_service import ExecutionService
from ..services.verification_service import VerificationService
from ..orchestrator.nodes import WorkflowNodes
from ..orchestrator.workflow import run_recovery_workflow
from ..repositories.evaluation_repository import EvaluationRepository
from .synthetic_dataset import generate_synthetic_dataset
from .metrics import calculate_batch_metrics, detect_policy_violation

logger = logging.getLogger(__name__)


class BatchEvaluationRunner:
    """Executes deterministic benchmark comparisons across baselines and the orchestrator."""

    def __init__(
        self,
        policy_config: Optional[PolicyConfig] = None,
        evaluation_repository: Optional[EvaluationRepository] = None,
    ):
        self.policy_config = policy_config or PolicyConfig()
        self.evaluation_repository = evaluation_repository

    def _create_mocked_nodes(self) -> Tuple[WorkflowNodes, RazorpayService, AuditService]:
        """Construct isolated mocked nodes ensuring ZERO live gateway API calls."""
        mock_rzp = RazorpayService(key_id="mock_bench_key", key_secret="mock_bench_secret")
        mock_rzp._client = MagicMock()

        audit_svc = AuditService(session=None)
        exec_svc = ExecutionService(razorpay_service=mock_rzp, audit_service=audit_svc)
        verif_svc = VerificationService(razorpay_service=mock_rzp, audit_service=audit_svc)
        policy_eng = PolicyEngine(config=self.policy_config)
        diag_agent = DiagnosisAgent(api_key=None)  # Bounded deterministic diagnosis
        scorer = StrategyScorer()

        nodes = WorkflowNodes(
            diagnosis_agent=diag_agent,
            strategy_scorer=scorer,
            policy_engine=policy_eng,
            execution_service=exec_svc,
            verification_service=verif_svc,
            audit_service=audit_svc,
        )
        return nodes, mock_rzp, audit_svc

    def run_no_action_baseline(
        self,
        cases: List[RecoveryCase],
        batch_id: str,
    ) -> List[EvaluationCaseResult]:
        """Execute Baseline A: NO_ACTION.

        Never attempts recovery, initiates zero financial calls, recovers ₹0.
        """
        results: List[EvaluationCaseResult] = []
        for case in cases:
            case_copy = copy.deepcopy(case)
            cr = EvaluationCaseResult(
                case_id=case_copy.id,
                batch_id=batch_id,
                strategy_type=BaselineStrategyType.NO_ACTION,
                workflow_type=case_copy.case_type,
                failure_category=case_copy.failure_category,
                amount=case_copy.amount,
                selected_strategy=None,
                policy_outcome=None,
                execution_status="NONE",
                verification_status="NONE",
                verified_recovered_amount=0.0,
                final_status=case_copy.current_status,
                is_escalated=case_copy.is_escalated,
                is_stopped=(case_copy.current_status == CaseStatus.STOPPED),
                policy_violation=False,
                violation_details=None,
                truth_provenance=TruthProvenance.SYNTHETIC_DATA_RESULT,
                audit_event_count=0,
                executed_at=datetime.utcnow(),
            )
            results.append(cr)
        return results

    def run_retry_only_baseline(
        self,
        cases: List[RecoveryCase],
        ground_truth: Dict[str, GroundTruthMetadata],
        batch_id: str,
    ) -> List[EvaluationCaseResult]:
        """Execute Baseline B: RETRY_ONLY.

        Uses deterministic retry logic without LLM diagnosis or multi-strategy arbitration.
        Respects PolicyEngine rules (cooldown, retry limits, high value, non-retryable categories).
        """
        nodes, _, _ = self._create_mocked_nodes()
        results: List[EvaluationCaseResult] = []

        for case in cases:
            case_copy = copy.deepcopy(case)
            gt = ground_truth.get(case_copy.id)

            # Propose retry according to workflow
            proposed = (
                RecoveryStrategy.SUBSCRIPTION_RETRY
                if case_copy.case_type == CaseType.SUBSCRIPTION_RECURRING
                else RecoveryStrategy.SMART_RETRY
            )

            # Evaluate through Policy Engine
            policy_res = nodes.policy_engine.evaluate(case_copy, proposed)
            case_copy.policy_evaluation = policy_res

            execution_status = "NONE"
            verification_status = "NONE"
            recovered_amount = 0.0

            if policy_res.passed and policy_res.outcome in [PolicyOutcome.ALLOW, PolicyOutcome.DOWNGRADE]:
                # If retry is approved, execute and verify
                action_to_exec = policy_res.approved_strategy
                mock_exec_resp = {"id": f"mock_retry_{case_copy.id}", "status": "scheduled"}

                # Execute action
                exec_rec = nodes.execution_service.execute_policy_approved_action(
                    case=case_copy,
                    policy_result=policy_res,
                    mock_gateway_response=mock_exec_resp,
                    truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
                )
                execution_status = exec_rec.status

                if exec_rec.status == "SUCCESS":
                    # Simulate gateway verification from ground truth
                    if gt and gt.simulated_retry_will_succeed:
                        mock_state = {"status": "captured", "amount": int(case_copy.amount * 100)}
                    else:
                        mock_state = {"status": "failed"}

                    verif_rec = nodes.verification_service.verify_recovery_outcome(
                        case=case_copy,
                        mock_gateway_state=mock_state,
                        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
                    )
                    verification_status = verif_rec.status
                    if verif_rec.verified:
                        recovered_amount = verif_rec.recovered_amount
                        case_copy.current_status = CaseStatus.VERIFIED_RECOVERED
                        case_copy.verified_recovered_amount = recovered_amount
            else:
                # Handle policy block, escalation, or stop
                if policy_res.outcome == PolicyOutcome.ESCALATE:
                    case_copy.is_escalated = True
                    case_copy.current_status = CaseStatus.ESCALATED
                elif policy_res.outcome == PolicyOutcome.STOP:
                    case_copy.current_status = CaseStatus.STOPPED

            cr = EvaluationCaseResult(
                case_id=case_copy.id,
                batch_id=batch_id,
                strategy_type=BaselineStrategyType.RETRY_ONLY,
                workflow_type=case_copy.case_type,
                failure_category=case_copy.failure_category,
                amount=case_copy.amount,
                selected_strategy=policy_res.approved_strategy if policy_res else proposed,
                policy_outcome=policy_res.outcome if policy_res else None,
                execution_status=execution_status,
                verification_status=verification_status,
                verified_recovered_amount=recovered_amount,
                final_status=case_copy.current_status,
                is_escalated=case_copy.is_escalated,
                is_stopped=(case_copy.current_status == CaseStatus.STOPPED),
                truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
                audit_event_count=1 if execution_status != "NONE" else 0,
                executed_at=datetime.utcnow(),
            )

            is_viol, details = detect_policy_violation(cr, case_copy)
            cr.policy_violation = is_viol
            cr.violation_details = details
            results.append(cr)

        return results

    def run_orchestrator_benchmark(
        self,
        cases: List[RecoveryCase],
        ground_truth: Dict[str, GroundTruthMetadata],
        batch_id: str,
    ) -> List[EvaluationCaseResult]:
        """Execute Baseline C: AI_REVENUE_RECOVERY_ORCHESTRATOR.

        Runs the complete approved LangGraph state graph for each case.
        """
        nodes, _, _ = self._create_mocked_nodes()
        results: List[EvaluationCaseResult] = []

        for case in cases:
            case_copy = copy.deepcopy(case)
            gt = ground_truth.get(case_copy.id)

            # Determine simulation payloads based on ground truth
            # 1. Payment link responses
            mock_link_resp = {"id": f"plink_bench_{case_copy.id}", "short_url": f"https://rzp.io/i/{case_copy.id}", "status": "created"}

            # 2. Verification state simulation based on ground truth
            # Cases with expired instruments / auth failure recover via payment link
            if gt and gt.simulated_payment_link_will_pay:
                mock_state = {"status": "paid", "amount": int(case_copy.amount * 100)}
            elif gt and gt.simulated_retry_will_succeed:
                mock_state = {"status": "captured", "amount": int(case_copy.amount * 100)}
            else:
                mock_state = {"status": "created"}  # Link created but unpaid

            final_state = run_recovery_workflow(
                case=case_copy,
                nodes=nodes,
                mock_gateway_response=mock_link_resp,
                mock_gateway_state=mock_state,
                truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
            )

            resolved_case: RecoveryCase = final_state.get("case", case_copy)
            exec_rec = final_state.get("execution_record")
            verif_rec = final_state.get("verification_record")
            policy_res = final_state.get("policy_result")

            cr = EvaluationCaseResult(
                case_id=resolved_case.id,
                batch_id=batch_id,
                strategy_type=BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR,
                workflow_type=resolved_case.case_type,
                failure_category=resolved_case.failure_category,
                amount=resolved_case.amount,
                selected_strategy=final_state.get("recommended_strategy"),
                policy_outcome=policy_res.outcome if policy_res else None,
                execution_status=exec_rec.status if exec_rec else "NONE",
                verification_status=verif_rec.status if verif_rec else "NONE",
                verified_recovered_amount=resolved_case.verified_recovered_amount,
                final_status=resolved_case.current_status,
                is_escalated=resolved_case.is_escalated,
                is_stopped=(resolved_case.current_status == CaseStatus.STOPPED),
                truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
                audit_event_count=len(final_state.get("audit_events", [])),
                executed_at=datetime.utcnow(),
            )

            is_viol, details = detect_policy_violation(cr, resolved_case)
            cr.policy_violation = is_viol
            cr.violation_details = details
            results.append(cr)

        return results

    def run_benchmark(
        self,
        seed: int = 42,
        count: int = 60,
        dataset_version: str = "v1.0",
        batch_id: Optional[str] = None,
    ) -> BatchRunSummary:
        """Run the complete 3-way evaluation benchmark on a reproducible synthetic dataset.

        Args:
            seed: Random seed for 100% deterministic dataset generation.
            count: Number of cases (must be >= 50).
            dataset_version: Dataset version tag.
            batch_id: Optional custom batch identifier.

        Returns:
            BatchRunSummary with metadata, baseline metrics, case results, and comparison.
        """
        actual_batch_id = batch_id or f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        logger.info("Starting synthetic batch evaluation '%s' (seed=%d, count=%d)", actual_batch_id, seed, count)

        # 1. Generate deterministic dataset
        cases, ground_truth = generate_synthetic_dataset(seed=seed, count=count, version=dataset_version)
        total_revenue_at_risk = sum(c.amount for c in cases)

        # 2. Run Baseline A: NO_ACTION
        no_action_results = self.run_no_action_baseline(cases, actual_batch_id)
        no_action_metrics = calculate_batch_metrics(
            BaselineStrategyType.NO_ACTION, total_revenue_at_risk, no_action_results
        )

        # 3. Run Baseline B: RETRY_ONLY
        retry_only_results = self.run_retry_only_baseline(cases, ground_truth, actual_batch_id)
        retry_only_metrics = calculate_batch_metrics(
            BaselineStrategyType.RETRY_ONLY, total_revenue_at_risk, retry_only_results
        )

        # 4. Run Baseline C: AI_REVENUE_RECOVERY_ORCHESTRATOR
        orchestrator_results = self.run_orchestrator_benchmark(cases, ground_truth, actual_batch_id)
        orchestrator_metrics = calculate_batch_metrics(
            BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR, total_revenue_at_risk, orchestrator_results
        )

        # 5. Combine per-case evaluation results
        all_case_results = no_action_results + retry_only_results + orchestrator_results

        # 6. Build Metadata
        metadata = BatchRunMetadata(
            batch_id=actual_batch_id,
            dataset_version=dataset_version,
            random_seed=seed,
            policy_config_version="1.0.0-demo",
            scoring_config_version="1.0.0-demo",
            code_version="1.0.0",
            batch_timestamp=datetime.utcnow(),
            total_cases=count,
        )

        # 7. Calculate comparison insights
        orch_rev = orchestrator_metrics.verified_recovered_revenue
        retry_rev = retry_only_metrics.verified_recovered_revenue
        rev_lift = orch_rev - retry_rev
        pct_lift = ((orch_rev - retry_rev) / retry_rev * 100.0) if retry_rev > 0 else 0.0

        comparison = {
            "total_revenue_at_risk": round(total_revenue_at_risk, 2),
            "no_action_revenue": no_action_metrics.verified_recovered_revenue,
            "retry_only_revenue": retry_only_metrics.verified_recovered_revenue,
            "orchestrator_revenue": orchestrator_metrics.verified_recovered_revenue,
            "orchestrator_absolute_lift": round(rev_lift, 2),
            "orchestrator_percentage_lift": round(pct_lift, 2),
            "orchestrator_policy_violations": orchestrator_metrics.policy_violations,
            "retry_only_policy_violations": retry_only_metrics.policy_violations,
        }

        summary = BatchRunSummary(
            metadata=metadata,
            metrics={
                BaselineStrategyType.NO_ACTION.value: no_action_metrics,
                BaselineStrategyType.RETRY_ONLY.value: retry_only_metrics,
                BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR.value: orchestrator_metrics,
            },
            case_results=all_case_results,
            comparison_summary=comparison,
        )

        # 8. Persist run if repository configured
        if self.evaluation_repository:
            try:
                self.evaluation_repository.save_run(summary)
            except Exception as e:
                logger.error("Failed to persist evaluation run '%s': %s", actual_batch_id, e)

        return summary

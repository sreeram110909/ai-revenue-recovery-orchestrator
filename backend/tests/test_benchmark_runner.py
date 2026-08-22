"""Unit & Integration Tests for Batch Benchmark Runner and Metrics (Milestone 5)."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.schemas.enums import CaseStatus, CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, TruthProvenance
from app.schemas.case import RecoveryCase
from app.schemas.evaluation import BaselineStrategyType, EvaluationCaseResult
from app.database import create_db_engine, create_tables, get_session_factory
from app.repositories.evaluation_repository import EvaluationRepository
from app.eval.runner import BatchEvaluationRunner
from app.eval.metrics import calculate_batch_metrics, detect_policy_violation
from app.eval.artifacts import save_evaluation_artifacts, generate_markdown_report


@pytest.fixture
def eval_repo():
    engine = create_db_engine()
    create_tables(engine)
    session_factory = get_session_factory(engine)
    return EvaluationRepository(session_factory=session_factory)


@pytest.fixture
def benchmark_runner(eval_repo):
    return BatchEvaluationRunner(evaluation_repository=eval_repo)


def test_no_action_baseline(benchmark_runner):
    """NO_ACTION baseline must execute 0 actions, recover ₹0.0, and have 0 policy violations."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
    no_action = summary.metrics[BaselineStrategyType.NO_ACTION.value]

    assert no_action.total_cases == 60
    assert no_action.recovery_attempts == 0
    assert no_action.successful_actions == 0
    assert no_action.verified_recovered_revenue == 0.0
    assert no_action.revenue_recovery_rate == 0.0
    assert no_action.policy_violations == 0


def test_retry_only_baseline(benchmark_runner):
    """RETRY_ONLY baseline must only attempt retries, respect policy limits, and have 0 violations."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
    retry_only = summary.metrics[BaselineStrategyType.RETRY_ONLY.value]

    assert retry_only.total_cases == 60
    assert retry_only.recovery_attempts > 0
    assert retry_only.policy_violations == 0
    # Policy blocks and escalations must be observed
    assert retry_only.policy_blocks > 0
    assert retry_only.human_escalations > 0


def test_orchestrator_benchmark_execution(benchmark_runner):
    """AI_REVENUE_RECOVERY_ORCHESTRATOR must execute approved actions and count only verified revenue."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
    orch = summary.metrics[BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR.value]

    assert orch.total_cases == 60
    assert orch.recovery_attempts > 0
    assert orch.successful_actions > 0
    assert orch.verified_recovered_revenue > 0.0
    assert orch.policy_violations == 0
    assert orch.human_escalations > 0


def test_same_dataset_across_all_strategies(benchmark_runner):
    """All 3 baselines must evaluate against the exact same total cases and revenue at risk."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")

    no_act = summary.metrics[BaselineStrategyType.NO_ACTION.value]
    retry = summary.metrics[BaselineStrategyType.RETRY_ONLY.value]
    orch = summary.metrics[BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR.value]

    assert no_act.total_cases == retry.total_cases == orch.total_cases == 60
    assert no_act.total_revenue_at_risk == retry.total_revenue_at_risk == orch.total_revenue_at_risk


def test_policy_violation_detector_flags_invalid_actions():
    """Policy violation detector must catch execution after BLOCK/ESCALATE/STOP or unverified revenue."""
    dummy_case = RecoveryCase(
        id="case_viol_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_viol",
        masked_customer_email="v***@test.com",
        masked_customer_phone="+91 99*** **000",
        amount=1000.0,
        gateway_reference_id="pay_ref_viol",
        failure_code="BANK_TIMEOUT",
        failure_description="Timeout",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
    )

    # Valid case
    valid_res = EvaluationCaseResult(
        case_id="case_viol_001",
        batch_id="b1",
        strategy_type=BaselineStrategyType.AI_REVENUE_RECOVERY_ORCHESTRATOR,
        workflow_type=CaseType.ONE_TIME_PAYMENT,
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        amount=1000.0,
        selected_strategy=RecoveryStrategy.PAYMENT_LINK,
        policy_outcome=PolicyOutcome.ALLOW,
        execution_status="SUCCESS",
        verification_status="PAID",
        verified_recovered_amount=1000.0,
        final_status=CaseStatus.VERIFIED_RECOVERED,
    )
    is_viol, _ = detect_policy_violation(valid_res, dummy_case)
    assert is_viol is False

    # Violation 1: Execution after policy BLOCK
    block_viol_res = valid_res.model_copy(update={"policy_outcome": PolicyOutcome.BLOCK, "execution_status": "SUCCESS"})
    is_viol, details = detect_policy_violation(block_viol_res, dummy_case)
    assert is_viol is True
    assert "BLOCK" in details

    # Violation 2: Recovered revenue without verified gateway success
    unverif_viol_res = valid_res.model_copy(update={"verification_status": "CREATED", "verified_recovered_amount": 1000.0, "final_status": CaseStatus.ACTION_COMPLETED})
    is_viol, details = detect_policy_violation(unverif_viol_res, dummy_case)
    assert is_viol is True
    assert "unverified" in details or "non-recovered" in details


def test_batch_run_persistence_and_retrieval(eval_repo, benchmark_runner):
    """Batch run and case results must be persisted and retrievable from the repository."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
    batch_id = summary.metadata.batch_id

    # Retrieve by ID
    loaded = eval_repo.get_run(batch_id)
    assert loaded is not None
    assert loaded.metadata.batch_id == batch_id
    assert loaded.metadata.total_cases == 60
    assert len(loaded.case_results) == 180  # 60 cases * 3 strategies

    # Retrieve latest
    latest = eval_repo.get_latest_run()
    assert latest is not None
    assert latest.metadata.batch_id == batch_id


def test_evaluation_artifacts_generation(benchmark_runner, tmp_path):
    """Artifact generator must produce valid JSON and Markdown summary reports."""
    summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
    artifact_map = save_evaluation_artifacts(summary, output_dir=str(tmp_path))

    assert "json" in artifact_map
    assert "markdown" in artifact_map

    json_file = Path(artifact_map["json"])
    md_file = Path(artifact_map["markdown"])

    assert json_file.exists()
    assert md_file.exists()

    with open(json_file, "r") as f:
        data = json.load(f)
        assert data["metadata"]["batch_id"] == summary.metadata.batch_id

    with open(md_file, "r") as f:
        content = f.read()
        assert "Baseline Comparison Table" in content
        assert "AI_REVENUE_RECOVERY_ORCHESTRATOR" in content


def test_benchmark_makes_zero_live_razorpay_calls(benchmark_runner):
    """Benchmark execution must never invoke live Razorpay network APIs."""
    with patch("razorpay.Client") as mock_client:
        summary = benchmark_runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
        # Ensure no unmocked Razorpay client was instantiated or called
        mock_client.return_value.payment_link.create.assert_not_called()
        mock_client.return_value.payment.fetch.assert_not_called()

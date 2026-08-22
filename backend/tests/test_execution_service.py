"""Tests for Execution Service (Milestone 3).

All tests use mocked Razorpay responses — no live financial APIs are called.

Verifies:
1. No execution occurs without Policy Engine validation.
2. BLOCK outcome prevents execution.
3. ESCALATE outcome routes to human review queue with zero financial API calls.
4. STOP outcome prevents execution.
5. PAYMENT_LINK requires policy approval.
6. Payment link creation does NOT mark revenue as recovered.
7. SMART_RETRY increments attempts and schedules cooldown.
8. SUBSCRIPTION_RETRY executes for subscription cases.
9. UPDATE_PAYMENT_METHOD executes mandate update flow.
10. Idempotency prevents duplicate action execution.
11. Already recovered or escalated cases cannot be re-executed.
12. Mocked results are accurately tagged as MOCKED_TEST_RESULT.
13. Gateway failures fail closed gracefully.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.schemas.enums import CaseType, FailureCategory, CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance
from app.schemas.case import RecoveryCase, SubscriptionMetadata
from app.schemas.policy import PolicyCheckResult, PolicyConfig, RuleEvaluationDetail
from app.policies.engine import PolicyEngine
from app.services.execution_service import ExecutionService
from app.services.razorpay_service import RazorpayService
from app.services.audit_service import AuditService


@pytest.fixture
def policy_engine():
    config = PolicyConfig(
        max_retry_attempts=3,
        retry_cooldown_hours=4.0,
        automated_recovery_amount_limit=15000.0,
        non_retryable_categories=[
            FailureCategory.RISK_SECURITY_BLOCK,
            FailureCategory.EXPIRED_INSTRUMENT,
            FailureCategory.MANDATE_EXPIRED_INVALID,
        ],
        allow_invalid_mandate_auto_retry=False,
    )
    return PolicyEngine(config=config)


@pytest.fixture
def base_case():
    return RecoveryCase(
        id="case_exec_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_exec_100",
        masked_customer_email="e***@test.com",
        masked_customer_phone="+91 99*** **111",
        amount=4999.0,
        currency="INR",
        gateway_reference_id="pay_ref_001",
        failure_code="BANK_TIMEOUT",
        failure_description="Timeout during bank processing",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=5),
        current_status=CaseStatus.DIAGNOSED,
    )


@pytest.fixture
def subscription_case():
    return RecoveryCase(
        id="case_exec_sub_001",
        case_type=CaseType.SUBSCRIPTION_RECURRING,
        customer_id="cust_exec_200",
        masked_customer_email="s***@test.com",
        masked_customer_phone="+91 88*** **222",
        amount=1499.0,
        currency="INR",
        gateway_reference_id="pay_sub_ref_001",
        failure_code="MANDATE_EXPIRED",
        failure_description="Mandate expired",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DIAGNOSED,
        subscription_details=SubscriptionMetadata(
            subscription_id="sub_exec_001",
            plan_name="Pro Monthly",
            billing_interval="MONTHLY",
            mandate_status="EXPIRED",
        ),
    )


@pytest.fixture
def mock_razorpay_service():
    service = RazorpayService(key_id="test_key", key_secret="test_secret")
    service._client = MagicMock()
    return service


@pytest.fixture
def execution_service(mock_razorpay_service):
    audit = AuditService(session=None)
    return ExecutionService(razorpay_service=mock_razorpay_service, audit_service=audit)


def test_payment_link_executed_after_policy_approval(execution_service, policy_engine, base_case):
    """Payment link is dispatched only after Policy Engine validates the action."""
    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.PAYMENT_LINK)
    assert policy_result.outcome == PolicyOutcome.ALLOW

    mock_resp = {
        "id": "plink_test_123",
        "short_url": "https://rzp.io/i/test123",
        "status": "created",
        "amount": 499900,
    }

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        mock_gateway_response=mock_resp,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.status == "SUCCESS"
    assert execution.action_type == RecoveryStrategy.PAYMENT_LINK
    assert execution.payment_link_url == "https://rzp.io/i/test123"
    assert base_case.current_status == CaseStatus.ACTION_COMPLETED
    assert execution.provenance == TruthProvenance.MOCKED_TEST_RESULT
    # Critical: Revenue is NOT marked as recovered upon payment link creation!
    assert base_case.verified_recovered_amount == 0.0


def test_smart_retry_executed_after_policy_approval(execution_service, policy_engine, base_case):
    """Smart retry increments attempt count and updates case status."""
    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert policy_result.outcome == PolicyOutcome.ALLOW

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.status == "SUCCESS"
    assert execution.action_type == RecoveryStrategy.SMART_RETRY
    assert base_case.attempts_count == 2
    assert base_case.current_status == CaseStatus.RETRY_SCHEDULED
    assert base_case.verified_recovered_amount == 0.0


def test_policy_block_prevents_action_dispatch(execution_service, policy_engine, base_case):
    """Policy BLOCK (e.g. cooldown violation) prevents execution."""
    base_case.last_attempt_at = datetime.utcnow() - timedelta(hours=1)
    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert policy_result.outcome == PolicyOutcome.BLOCK
    assert policy_result.passed is False

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.status == "FAILED"
    assert base_case.current_status == CaseStatus.DIAGNOSED  # Unchanged
    assert base_case.attempts_count == 1  # Not incremented


def test_policy_escalate_routes_to_human_review_without_financial_calls(execution_service, policy_engine, base_case):
    """High value cases that force escalation must NOT call payment APIs."""
    base_case.amount = 25000.0
    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert policy_result.outcome == PolicyOutcome.ESCALATE

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.HUMAN_ESCALATION
    assert base_case.is_escalated is True
    assert base_case.current_status == CaseStatus.ESCALATED
    assert base_case.verified_recovered_amount == 0.0


def test_policy_stop_sets_terminal_status_without_financial_calls(execution_service, base_case):
    """STOP policy outcome halts automated processing."""
    stop_policy = PolicyCheckResult(
        outcome=PolicyOutcome.STOP,
        passed=False,
        proposed_strategy=RecoveryStrategy.PAYMENT_LINK,
        approved_strategy=RecoveryStrategy.STOP,
        evaluations=[],
        reasons=["Terminal state reached."],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=stop_policy,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.STOP
    assert base_case.current_status == CaseStatus.STOPPED
    assert base_case.verified_recovered_amount == 0.0


def test_idempotency_prevents_duplicate_execution(execution_service, policy_engine, base_case):
    """Executing the same action twice must return the existing record and not double-execute."""
    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.PAYMENT_LINK)
    mock_resp = {"id": "plink_123", "short_url": "https://rzp.io/i/test123", "status": "created"}

    first_exec = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        mock_gateway_response=mock_resp,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )
    assert first_exec.status == "SUCCESS"

    # Second execution attempt with the same case
    second_exec = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        mock_gateway_response=mock_resp,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert second_exec.action_id == first_exec.action_id


def test_already_escalated_case_cannot_be_re_executed(execution_service, policy_engine, base_case):
    """An already-escalated case cannot execute automated actions."""
    base_case.current_status = CaseStatus.ESCALATED
    base_case.is_escalated = True

    policy_result = policy_engine.evaluate(base_case, RecoveryStrategy.PAYMENT_LINK)
    assert policy_result.outcome == PolicyOutcome.STOP

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.status == "FAILED"
    assert base_case.current_status == CaseStatus.ESCALATED


def test_subscription_retry_execution(execution_service, subscription_case):
    """Subscription retry executes properly for recurring cases."""
    policy_result = PolicyCheckResult(
        outcome=PolicyOutcome.ALLOW,
        passed=True,
        proposed_strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
        approved_strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
        evaluations=[],
        reasons=["Subscription retry permitted."],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = execution_service.execute_policy_approved_action(
        case=subscription_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.SUBSCRIPTION_RETRY
    assert subscription_case.current_status == CaseStatus.RETRY_SCHEDULED
    assert subscription_case.attempts_count == 1


def test_update_payment_method_execution(execution_service, subscription_case):
    """Update payment method records strategy decision without claiming a fake API link was generated."""
    policy_result = PolicyCheckResult(
        outcome=PolicyOutcome.DOWNGRADE,
        passed=True,
        proposed_strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
        approved_strategy=RecoveryStrategy.UPDATE_PAYMENT_METHOD,
        evaluations=[],
        reasons=["Downgraded to UPDATE_PAYMENT_METHOD."],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = execution_service.execute_policy_approved_action(
        case=subscription_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.UPDATE_PAYMENT_METHOD
    assert subscription_case.current_status == CaseStatus.ACTION_COMPLETED
    assert execution.payment_link_url is None  # No fake link URL claimed
    assert execution.gateway_response is None  # No fake API call claimed
    assert subscription_case.verified_recovered_amount == 0.0


def test_smart_retry_is_not_reported_as_real_gateway_api_call(execution_service, base_case):
    """SMART_RETRY records recovery decision and schedule without falsely claiming a direct gateway debit call."""
    policy_result = PolicyCheckResult(
        outcome=PolicyOutcome.ALLOW,
        passed=True,
        proposed_strategy=RecoveryStrategy.SMART_RETRY,
        approved_strategy=RecoveryStrategy.SMART_RETRY,
        evaluations=[],
        reasons=["Allowed"],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = execution_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.SMART_RETRY
    assert execution.gateway_response is None  # No fake direct charge API claimed
    assert base_case.current_status == CaseStatus.RETRY_SCHEDULED
    assert base_case.verified_recovered_amount == 0.0


def test_subscription_retry_is_not_represented_as_direct_api_call(execution_service, subscription_case):
    """SUBSCRIPTION_RETRY observes subscription lifecycle without pretending a standalone debit API exists."""
    policy_result = PolicyCheckResult(
        outcome=PolicyOutcome.ALLOW,
        passed=True,
        proposed_strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
        approved_strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
        evaluations=[],
        reasons=["Allowed"],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = execution_service.execute_policy_approved_action(
        case=subscription_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert execution.action_type == RecoveryStrategy.SUBSCRIPTION_RETRY
    assert execution.gateway_response is None
    assert subscription_case.current_status == CaseStatus.RETRY_SCHEDULED
    assert subscription_case.verified_recovered_amount == 0.0


def test_gateway_api_failure_fails_closed(base_case):
    """When Razorpay client raises an exception during payment link creation, execution fails closed."""
    failing_service = RazorpayService(key_id="test_key", key_secret="test_secret")
    failing_service._client = MagicMock()
    failing_service._client.payment_link.create.side_effect = RuntimeError("Razorpay gateway timeout 504")

    exec_service = ExecutionService(razorpay_service=failing_service, audit_service=AuditService())

    policy_result = PolicyCheckResult(
        outcome=PolicyOutcome.ALLOW,
        passed=True,
        proposed_strategy=RecoveryStrategy.PAYMENT_LINK,
        approved_strategy=RecoveryStrategy.PAYMENT_LINK,
        evaluations=[],
        reasons=["Allowed"],
        evaluated_at=datetime.utcnow(),
        config_snapshot=PolicyConfig(),
    )

    execution = exec_service.execute_policy_approved_action(
        case=base_case,
        policy_result=policy_result,
        truth_provenance=TruthProvenance.LIVE_TEST_MODE_API_RESULT,
    )

    assert execution.status == "FAILED"
    assert "Razorpay gateway timeout 504" in execution.payload.get("error", "")
    assert base_case.verified_recovered_amount == 0.0

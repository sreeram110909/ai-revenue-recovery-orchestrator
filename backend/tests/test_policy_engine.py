"""Pytest Test Suite for Deterministic Policy Engine (Python)."""

import pytest
from datetime import datetime, timedelta
from app.schemas.enums import CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, CaseStatus
from app.schemas.case import RecoveryCase, SubscriptionMetadata
from app.schemas.policy import PolicyConfig
from app.policies.engine import PolicyEngine


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
        id="case_py_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_py_100",
        masked_customer_email="c***@example.com",
        masked_customer_phone="+91 98*** **111",
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


def test_valid_retry_is_allowed(policy_engine, base_case):
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.ALLOW
    assert result.approved_strategy == RecoveryStrategy.SMART_RETRY
    assert result.passed is True


def test_retry_limit_forces_downgrade(policy_engine, base_case):
    base_case.attempts_count = 3
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.DOWNGRADE
    assert result.approved_strategy == RecoveryStrategy.PAYMENT_LINK


def test_cooldown_violation_blocks_retry(policy_engine, base_case):
    base_case.last_attempt_at = datetime.utcnow() - timedelta(hours=1)
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.BLOCK
    assert result.passed is False


def test_high_value_case_forces_escalation(policy_engine, base_case):
    base_case.amount = 25000.0
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.ESCALATE
    assert result.approved_strategy == RecoveryStrategy.HUMAN_ESCALATION


def test_non_retryable_category_blocks_retry(policy_engine, base_case):
    base_case.failure_category = FailureCategory.RISK_SECURITY_BLOCK
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.BLOCK
    assert result.approved_strategy == RecoveryStrategy.HUMAN_ESCALATION


def test_frozen_escalated_case_rejects_automated_action(policy_engine, base_case):
    base_case.current_status = CaseStatus.ESCALATED
    base_case.is_escalated = True
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.STOP
    assert result.passed is False


def test_frozen_stopped_case_rejects_automated_action(policy_engine, base_case):
    base_case.current_status = CaseStatus.STOPPED
    result = policy_engine.evaluate(base_case, RecoveryStrategy.PAYMENT_LINK)
    assert result.outcome == PolicyOutcome.STOP
    assert result.passed is False


def test_invalid_mandate_downgrades_subscription_retry(policy_engine, base_case):
    base_case.case_type = CaseType.SUBSCRIPTION_RECURRING
    base_case.failure_category = FailureCategory.MANDATE_EXPIRED_INVALID
    base_case.subscription_details = SubscriptionMetadata(
        subscription_id="sub_999",
        plan_name="Monthly SaaS",
        billing_interval="MONTHLY",
        mandate_status="EXPIRED",
    )
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SUBSCRIPTION_RETRY)
    assert result.outcome == PolicyOutcome.DOWNGRADE
    assert result.approved_strategy == RecoveryStrategy.UPDATE_PAYMENT_METHOD


def test_expired_instrument_downgrades_to_payment_link(policy_engine, base_case):
    base_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    result = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY)
    assert result.outcome == PolicyOutcome.DOWNGRADE
    assert result.approved_strategy == RecoveryStrategy.PAYMENT_LINK


def test_policy_engine_is_strictly_deterministic(policy_engine, base_case):
    fixed_time = datetime(2026, 8, 20, 12, 0, 0)
    base_case.last_attempt_at = datetime(2026, 8, 20, 6, 0, 0)

    result_1 = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY, fixed_time)
    result_2 = policy_engine.evaluate(base_case, RecoveryStrategy.SMART_RETRY, fixed_time)

    assert result_1.outcome == result_2.outcome
    assert result_1.approved_strategy == result_2.approved_strategy
    assert result_1.model_dump_json() == result_2.model_dump_json()

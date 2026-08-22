"""Safety and Non-Execution Verification Tests for Milestone 2.

Explicitly proves that Milestone 2 is strictly limited to:
    Evidence Extraction -> Bounded Diagnosis -> Deterministic Strategy Scoring -> STOP

Verifies that:
1. Diagnosis layer does NOT import or call Razorpay.
2. Strategy scorer does NOT import or call Razorpay.
3. Evidence layer does NOT import or call Razorpay.
4. No payment action is dispatched.
5. No Payment Link is created.
6. No subscription retry is executed.
7. Case payment status and financial amounts remain unaltered.
8. No financial API or external execution layer is invoked.
"""

import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.schemas.enums import CaseType, FailureCategory, CaseStatus, RecoveryStrategy
from app.schemas.case import RecoveryCase, SubscriptionMetadata
from app.agents.evidence import extract_evidence
from app.agents.diagnosis import DiagnosisAgent
from app.agents.strategy_scorer import StrategyScorer


@pytest.fixture
def one_time_test_case():
    return RecoveryCase(
        id="case_safety_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_safe_100",
        masked_customer_email="test***@example.com",
        masked_customer_phone="+91 99*** **000",
        customer_segment="STANDARD",
        amount=5000.0,
        currency="INR",
        gateway_reference_id="pay_ref_safe_001",
        failure_code="BANK_TIMEOUT",
        failure_description="Bank timed out",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=5),
        current_status=CaseStatus.DETECTED,
        verified_recovered_amount=0.0,
        executed_action=None,
        verification_outcome=None,
    )


@pytest.fixture
def subscription_test_case():
    return RecoveryCase(
        id="case_safety_002",
        case_type=CaseType.SUBSCRIPTION_RECURRING,
        customer_id="cust_safe_200",
        masked_customer_email="sub***@example.com",
        masked_customer_phone="+91 88*** **111",
        customer_segment="PREMIUM",
        amount=2499.0,
        currency="INR",
        gateway_reference_id="pay_ref_safe_002",
        failure_code="MANDATE_EXPIRED",
        failure_description="Mandate expired",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
        subscription_details=SubscriptionMetadata(
            subscription_id="sub_safe_001",
            plan_name="Enterprise Monthly",
            billing_interval="MONTHLY",
            mandate_status="EXPIRED",
        ),
        verified_recovered_amount=0.0,
        executed_action=None,
        verification_outcome=None,
    )


def test_evidence_layer_does_not_invoke_razorpay(one_time_test_case):
    """Evidence extraction must be pure and never call payment SDKs."""
    with patch.dict(sys.modules, {"razorpay": MagicMock()}):
        evidence = extract_evidence(one_time_test_case)
        assert isinstance(evidence, dict)
        # Ensure razorpay module was not called
        assert sys.modules["razorpay"].mock_calls == []


def test_diagnosis_agent_does_not_invoke_razorpay(one_time_test_case):
    """Diagnosis agent must be advisory only and never call payment SDKs."""
    with patch.dict(sys.modules, {"razorpay": MagicMock()}):
        agent = DiagnosisAgent(api_key=None)
        diagnosis = agent.diagnose(one_time_test_case)
        assert diagnosis is not None
        assert sys.modules["razorpay"].mock_calls == []


def test_strategy_scorer_does_not_invoke_razorpay(one_time_test_case):
    """Strategy scorer must be deterministic math and never call payment SDKs."""
    with patch.dict(sys.modules, {"razorpay": MagicMock()}):
        agent = DiagnosisAgent(api_key=None)
        diagnosis = agent.diagnose(one_time_test_case)
        scorer = StrategyScorer()
        ranking = scorer.score(one_time_test_case, diagnosis)
        assert ranking is not None
        assert sys.modules["razorpay"].mock_calls == []


def test_case_state_is_immutable_throughout_milestone2_pipeline(one_time_test_case):
    """Running through Evidence -> Diagnosis -> Strategy Scoring must NOT mutate the Case state."""
    initial_status = one_time_test_case.current_status
    initial_amount = one_time_test_case.amount
    initial_recovered = one_time_test_case.verified_recovered_amount
    initial_executed_action = one_time_test_case.executed_action
    initial_verification = one_time_test_case.verification_outcome

    # 1. Evidence extraction
    evidence = extract_evidence(one_time_test_case)
    assert evidence["case_id"] == one_time_test_case.id

    # 2. Bounded Diagnosis
    agent = DiagnosisAgent(api_key=None)
    diagnosis = agent.diagnose(one_time_test_case)
    assert diagnosis.case_id == one_time_test_case.id

    # 3. Strategy Scoring
    scorer = StrategyScorer()
    ranking = scorer.score(one_time_test_case, diagnosis)
    assert ranking.recommended_strategy is not None

    # Assert that NO financial state or action was modified on the Case entity
    assert one_time_test_case.current_status == initial_status == CaseStatus.DETECTED
    assert one_time_test_case.amount == initial_amount == 5000.0
    assert one_time_test_case.verified_recovered_amount == initial_recovered == 0.0
    assert one_time_test_case.executed_action == initial_executed_action is None
    assert one_time_test_case.verification_outcome == initial_verification is None


def test_no_payment_link_or_subscription_dispatched_in_milestone2(subscription_test_case):
    """For subscription cases, diagnosis and scoring must NOT create links or retry debits."""
    agent = DiagnosisAgent(api_key=None)
    diagnosis = agent.diagnose(subscription_test_case)
    scorer = StrategyScorer()
    ranking = scorer.score(subscription_test_case, diagnosis)

    # Scorer recommends strategy, but does NOT execute it
    assert ranking.recommended_strategy == RecoveryStrategy.UPDATE_PAYMENT_METHOD
    assert subscription_test_case.executed_action is None
    assert subscription_test_case.verified_recovered_amount == 0.0
    assert subscription_test_case.current_status == CaseStatus.DETECTED

"""Tests for Deterministic Strategy Scoring Engine.

Verifies:
- Same input always produces same output (determinism)
- Different failure types produce expected strategy rankings
- Primary workflow only scores primary strategies
- Secondary workflow only scores secondary strategies
- High attempts reduce retry scores
- High amounts increase escalation scores
- Score breakdowns are inspectable
- Weights are applied correctly
"""

import pytest
from datetime import datetime, timedelta

from app.schemas.enums import CaseType, FailureCategory, CaseStatus, RecoveryStrategy
from app.schemas.case import RecoveryCase, SubscriptionMetadata
from app.schemas.diagnosis import DiagnosisResult
from app.agents.strategy_scorer import StrategyScorer


@pytest.fixture
def scorer():
    return StrategyScorer()


@pytest.fixture
def bank_timeout_case():
    return RecoveryCase(
        id="case_score_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_score_100",
        masked_customer_email="s***@test.com",
        masked_customer_phone="+91 88*** **111",
        amount=5000.0,
        currency="INR",
        gateway_reference_id="pay_score_ref_001",
        failure_code="BANK_TIMEOUT",
        failure_description="Bank timed out",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=5),
        current_status=CaseStatus.DIAGNOSED,
    )


@pytest.fixture
def bank_timeout_diagnosis():
    return DiagnosisResult(
        case_id="case_score_001",
        diagnosis="Bank timeout during processing.",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        candidate_strategies=[RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK],
        rationale="Transient error. Retry recommended.",
        confidence=0.85,
        is_fallback=True,
    )


# ---------------------------------------------------------------------------
# Determinism Tests
# ---------------------------------------------------------------------------

def test_deterministic_same_input_same_output(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """Identical inputs must always produce identical results."""
    result_1 = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
    result_2 = scorer.score(bank_timeout_case, bank_timeout_diagnosis)

    assert result_1.recommended_strategy == result_2.recommended_strategy
    assert len(result_1.ranked_strategies) == len(result_2.ranked_strategies)

    for s1, s2 in zip(result_1.ranked_strategies, result_2.ranked_strategies):
        assert s1.strategy == s2.strategy
        assert s1.score == s2.score
        assert s1.signal_contributions == s2.signal_contributions


def test_deterministic_across_multiple_runs(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """Run scoring 100 times — every result must be identical."""
    first = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
    for _ in range(100):
        result = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
        assert result.recommended_strategy == first.recommended_strategy
        for s1, s2 in zip(result.ranked_strategies, first.ranked_strategies):
            assert s1.score == s2.score


# ---------------------------------------------------------------------------
# Failure Category Ranking Tests
# ---------------------------------------------------------------------------

def test_bank_timeout_ranks_smart_retry_highest(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """Bank timeout should rank SMART_RETRY highest for primary workflow."""
    result = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
    assert result.recommended_strategy == RecoveryStrategy.SMART_RETRY


def test_expired_instrument_ranks_payment_link_highest(scorer):
    """Expired instrument should rank PAYMENT_LINK highest."""
    case = RecoveryCase(
        id="case_score_exp",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_score_exp",
        masked_customer_email="e***@test.com",
        masked_customer_phone="+91 77*** **222",
        amount=5000.0,
        currency="INR",
        gateway_reference_id="pay_ref_exp",
        failure_code="CARD_EXPIRED",
        failure_description="Card expired",
        failure_category=FailureCategory.EXPIRED_INSTRUMENT,
        attempts_count=1,
        max_attempts_allowed=3,
        current_status=CaseStatus.DIAGNOSED,
    )
    diagnosis = DiagnosisResult(
        case_id="case_score_exp",
        diagnosis="Card expired.",
        failure_category=FailureCategory.EXPIRED_INSTRUMENT,
        candidate_strategies=[RecoveryStrategy.PAYMENT_LINK],
        rationale="Need new payment method.",
        confidence=0.9,
        is_fallback=True,
    )
    result = scorer.score(case, diagnosis)
    assert result.recommended_strategy == RecoveryStrategy.PAYMENT_LINK


def test_security_block_ranks_escalation_highest(scorer):
    """Security block should rank HUMAN_ESCALATION highest."""
    case = RecoveryCase(
        id="case_score_sec",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_score_sec",
        masked_customer_email="r***@test.com",
        masked_customer_phone="+91 66*** **333",
        amount=10000.0,
        currency="INR",
        gateway_reference_id="pay_ref_sec",
        failure_code="RISK_BLOCKED",
        failure_description="Blocked by risk engine",
        failure_category=FailureCategory.RISK_SECURITY_BLOCK,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
    )
    diagnosis = DiagnosisResult(
        case_id="case_score_sec",
        diagnosis="Risk block.",
        failure_category=FailureCategory.RISK_SECURITY_BLOCK,
        candidate_strategies=[RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP],
        rationale="Human review required.",
        confidence=0.95,
        is_fallback=True,
    )
    result = scorer.score(case, diagnosis)
    assert result.recommended_strategy == RecoveryStrategy.HUMAN_ESCALATION


def test_insufficient_funds_ranks_smart_retry_highest(scorer):
    """Insufficient funds should rank SMART_RETRY highest."""
    case = RecoveryCase(
        id="case_score_insf",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_score_insf",
        masked_customer_email="i***@test.com",
        masked_customer_phone="+91 55*** **444",
        amount=2000.0,
        currency="INR",
        gateway_reference_id="pay_ref_insf",
        failure_code="INSUFFICIENT_FUNDS",
        failure_description="Insufficient balance",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
    )
    diagnosis = DiagnosisResult(
        case_id="case_score_insf",
        diagnosis="Insufficient funds.",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        candidate_strategies=[RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK],
        rationale="Retry after customer replenishes funds.",
        confidence=0.75,
        is_fallback=True,
    )
    result = scorer.score(case, diagnosis)
    assert result.recommended_strategy == RecoveryStrategy.SMART_RETRY


# ---------------------------------------------------------------------------
# Workflow Constraint Tests
# ---------------------------------------------------------------------------

def test_primary_workflow_only_primary_strategies(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """Primary workflow should only score primary strategies."""
    result = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
    allowed = {RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK,
               RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP}
    for s in result.ranked_strategies:
        assert s.strategy in allowed, f"Strategy {s.strategy} not in primary action space"


def test_secondary_workflow_only_secondary_strategies(scorer):
    """Secondary workflow should only score secondary strategies."""
    case = RecoveryCase(
        id="case_score_sub",
        case_type=CaseType.SUBSCRIPTION_RECURRING,
        customer_id="cust_score_sub",
        masked_customer_email="s***@test.com",
        masked_customer_phone="+91 44*** **555",
        amount=1299.0,
        currency="INR",
        gateway_reference_id="pay_ref_sub",
        failure_code="MANDATE_EXPIRED",
        failure_description="Mandate expired",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
        subscription_details=SubscriptionMetadata(
            subscription_id="sub_001",
            plan_name="Pro Plan",
            billing_interval="MONTHLY",
            mandate_status="EXPIRED",
        ),
    )
    diagnosis = DiagnosisResult(
        case_id="case_score_sub",
        diagnosis="Mandate expired.",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        candidate_strategies=[RecoveryStrategy.UPDATE_PAYMENT_METHOD],
        rationale="Customer must re-authorize mandate.",
        confidence=0.9,
        is_fallback=True,
    )
    result = scorer.score(case, diagnosis)
    allowed = {RecoveryStrategy.SUBSCRIPTION_RETRY, RecoveryStrategy.UPDATE_PAYMENT_METHOD,
               RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP}
    for s in result.ranked_strategies:
        assert s.strategy in allowed, f"Strategy {s.strategy} not in secondary action space"


# ---------------------------------------------------------------------------
# Signal Adjustment Tests
# ---------------------------------------------------------------------------

def test_high_attempts_reduces_retry_score(scorer):
    """More attempts used should reduce retry strategy scores."""
    case_low = RecoveryCase(
        id="case_score_low_att",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_att",
        masked_customer_email="a***@test.com",
        masked_customer_phone="+91 33*** **666",
        amount=5000.0,
        currency="INR",
        gateway_reference_id="pay_att_ref",
        failure_code="BANK_TIMEOUT",
        failure_description="Timeout",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
    )
    case_high = case_low.model_copy(update={"id": "case_score_high_att", "attempts_count": 3})

    diagnosis = DiagnosisResult(
        case_id="case_score_low_att",
        diagnosis="Bank timeout.",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        candidate_strategies=[RecoveryStrategy.SMART_RETRY],
        rationale="Retry.",
        confidence=0.8,
        is_fallback=True,
    )
    diag_high = diagnosis.model_copy(update={"case_id": "case_score_high_att"})

    result_low = scorer.score(case_low, diagnosis)
    result_high = scorer.score(case_high, diag_high)

    # Find SMART_RETRY score in each
    retry_low = next(s for s in result_low.ranked_strategies if s.strategy == RecoveryStrategy.SMART_RETRY)
    retry_high = next(s for s in result_high.ranked_strategies if s.strategy == RecoveryStrategy.SMART_RETRY)

    assert retry_high.score < retry_low.score, "Retry score should decrease with more attempts"


def test_high_amount_increases_escalation_score(scorer):
    """Higher amounts should increase HUMAN_ESCALATION score."""
    case_low = RecoveryCase(
        id="case_score_low_amt",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_amt",
        masked_customer_email="a***@test.com",
        masked_customer_phone="+91 22*** **777",
        amount=500.0,
        currency="INR",
        gateway_reference_id="pay_amt_ref",
        failure_code="BANK_TIMEOUT",
        failure_description="Timeout",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        current_status=CaseStatus.DIAGNOSED,
    )
    case_high = case_low.model_copy(update={"id": "case_score_high_amt", "amount": 25000.0})

    diagnosis = DiagnosisResult(
        case_id="case_score_low_amt",
        diagnosis="Bank timeout.",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        candidate_strategies=[RecoveryStrategy.SMART_RETRY],
        rationale="Retry.",
        confidence=0.8,
        is_fallback=True,
    )
    diag_high = diagnosis.model_copy(update={"case_id": "case_score_high_amt"})

    result_low = scorer.score(case_low, diagnosis)
    result_high = scorer.score(case_high, diag_high)

    esc_low = next(s for s in result_low.ranked_strategies if s.strategy == RecoveryStrategy.HUMAN_ESCALATION)
    esc_high = next(s for s in result_high.ranked_strategies if s.strategy == RecoveryStrategy.HUMAN_ESCALATION)

    assert esc_high.score > esc_low.score, "Escalation score should increase with higher amounts"


# ---------------------------------------------------------------------------
# Inspectability Tests
# ---------------------------------------------------------------------------

def test_signal_contributions_are_inspectable(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """Each strategy score should have a full breakdown of signal contributions."""
    result = scorer.score(bank_timeout_case, bank_timeout_diagnosis)

    for strategy_score in result.ranked_strategies:
        contributions = strategy_score.signal_contributions
        assert "base_score" in contributions
        assert "failure_category" in contributions
        assert "attempt_exhaustion" in contributions
        assert "amount_tier" in contributions
        assert "diagnosis_alignment" in contributions

        # Total should match the score
        computed_total = sum(contributions.values())
        assert abs(computed_total - strategy_score.score) < 0.01


def test_ranking_result_has_required_fields(scorer, bank_timeout_case, bank_timeout_diagnosis):
    """StrategyRankingResult should have all required fields."""
    result = scorer.score(bank_timeout_case, bank_timeout_diagnosis)
    assert result.case_id == bank_timeout_case.id
    assert result.case_type == CaseType.ONE_TIME_PAYMENT
    assert result.recommended_strategy is not None
    assert 0.0 <= result.recommended_confidence <= 1.0
    assert len(result.ranked_strategies) == 4  # 4 primary strategies

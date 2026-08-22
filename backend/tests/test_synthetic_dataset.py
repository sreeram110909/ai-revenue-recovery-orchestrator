"""Unit Tests for Deterministic Synthetic Dataset Generator (Milestone 5)."""

import pytest
from app.schemas.enums import CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, TruthProvenance
from app.eval.synthetic_dataset import (
    generate_synthetic_dataset,
    check_dataset_reproducibility,
)


def test_generate_minimum_50_cases():
    """Dataset generator must produce at least 50 cases (default 60)."""
    cases, gt_map = generate_synthetic_dataset(seed=42, count=60)
    assert len(cases) >= 50
    assert len(cases) == 60
    assert len(gt_map) == 60


def test_both_workflows_represented():
    """Dataset must contain both Primary (ONE_TIME_PAYMENT) and Secondary (SUBSCRIPTION_RECURRING) cases."""
    cases, _ = generate_synthetic_dataset(seed=42, count=60)
    one_time_cases = [c for c in cases if c.case_type == CaseType.ONE_TIME_PAYMENT]
    subscription_cases = [c for c in cases if c.case_type == CaseType.SUBSCRIPTION_RECURRING]

    assert len(one_time_cases) > 0, "Primary workflow (One-Time) must be present"
    assert len(subscription_cases) > 0, "Secondary workflow (Subscription) must be present"
    assert len(one_time_cases) + len(subscription_cases) == 60


def test_heterogeneous_failure_categories():
    """Dataset must cover all required failure categories."""
    cases, _ = generate_synthetic_dataset(seed=42, count=60)
    categories = {c.failure_category for c in cases}

    assert FailureCategory.BANK_TIMEOUT_NETWORK in categories
    assert FailureCategory.INSUFFICIENT_FUNDS in categories
    assert FailureCategory.EXPIRED_INSTRUMENT in categories
    assert FailureCategory.AUTHENTICATION_OTP_FAILURE in categories
    assert FailureCategory.RISK_SECURITY_BLOCK in categories
    assert FailureCategory.MANDATE_EXPIRED_INVALID in categories
    assert FailureCategory.GENERAL_TECHNICAL_ERROR in categories


def test_dataset_reproducibility():
    """Identical seeds must produce 100% bitwise equivalent datasets."""
    assert check_dataset_reproducibility(seed=42, count=60) is True
    assert check_dataset_reproducibility(seed=123, count=55) is True


def test_different_seeds_produce_different_amounts():
    """Different random seeds must produce different distributions."""
    cases_42, _ = generate_synthetic_dataset(seed=42, count=60)
    cases_99, _ = generate_synthetic_dataset(seed=99, count=60)

    amounts_42 = [c.amount for c in cases_42]
    amounts_99 = [c.amount for c in cases_99]
    assert amounts_42 != amounts_99


def test_ground_truth_metadata_is_complete():
    """Every generated case must have corresponding ground truth metadata."""
    cases, gt_map = generate_synthetic_dataset(seed=42, count=60)
    for case in cases:
        assert case.id in gt_map
        gt = gt_map[case.id]
        assert gt.expected_failure_category == case.failure_category
        assert isinstance(gt.is_high_value, bool)
        assert isinstance(gt.is_retryable_failure, bool)


def test_synthetic_data_provenance():
    """Generated cases must carry SYNTHETIC_DATA_RESULT truth provenance."""
    cases, _ = generate_synthetic_dataset(seed=42, count=60)
    for case in cases:
        assert case.provenance == TruthProvenance.SYNTHETIC_DATA_RESULT

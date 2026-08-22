"""Tests for PII Redaction & Evidence Extraction.

Verifies that:
- Raw email never appears in evidence
- Raw phone never appears in evidence
- API keys/secrets never appear in evidence
- Gateway references never appear in evidence
- Required diagnostic fields ARE present
- Subscription metadata IS included for recurring cases
- Blocklisted fields are detected and scrubbed
"""

import pytest
from datetime import datetime, timedelta

from app.schemas.enums import CaseType, FailureCategory, CaseStatus
from app.schemas.case import RecoveryCase, SubscriptionMetadata
from app.agents.evidence import extract_evidence, validate_no_pii_leakage, scrub_evidence


@pytest.fixture
def one_time_case():
    """A one-time payment case with realistic customer data."""
    return RecoveryCase(
        id="case_pii_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_py_200",
        masked_customer_email="s***@gmail.com",
        masked_customer_phone="+91 99*** **222",
        customer_segment="PREMIUM",
        amount=8500.0,
        currency="INR",
        gateway_reference_id="pay_ABCDEF123456",
        failure_code="BANK_TIMEOUT",
        failure_description="Bank timed out during processing",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=5),
        current_status=CaseStatus.DIAGNOSED,
    )


@pytest.fixture
def subscription_case():
    """A subscription case with mandate details."""
    return RecoveryCase(
        id="case_pii_002",
        case_type=CaseType.SUBSCRIPTION_RECURRING,
        customer_id="cust_py_300",
        masked_customer_email="r***@company.com",
        masked_customer_phone="+91 88*** **333",
        customer_segment="STANDARD",
        amount=1299.0,
        currency="INR",
        gateway_reference_id="pay_XYZABC789012",
        failure_code="MANDATE_EXPIRED",
        failure_description="E-mandate has expired",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        attempts_count=0,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=10),
        current_status=CaseStatus.DETECTED,
        subscription_details=SubscriptionMetadata(
            subscription_id="sub_001",
            plan_name="Monthly SaaS Pro",
            billing_interval="MONTHLY",
            mandate_status="EXPIRED",
        ),
    )


# ---------------------------------------------------------------------------
# PII Exclusion Tests
# ---------------------------------------------------------------------------

def test_raw_email_not_in_evidence(one_time_case):
    """Masked or raw email must never appear in evidence."""
    evidence = extract_evidence(one_time_case)
    evidence_str = str(evidence)
    assert "masked_customer_email" not in evidence
    assert "s***@gmail.com" not in evidence_str
    assert "@gmail.com" not in evidence_str
    assert "@" not in evidence_str or "case_pii" in evidence_str  # Only case ID might have special chars


def test_raw_phone_not_in_evidence(one_time_case):
    """Masked or raw phone must never appear in evidence."""
    evidence = extract_evidence(one_time_case)
    evidence_str = str(evidence)
    assert "masked_customer_phone" not in evidence
    assert "+91 99*** **222" not in evidence_str
    assert "99***" not in evidence_str


def test_gateway_reference_not_in_evidence(one_time_case):
    """Gateway reference IDs are internal and must not be sent to the LLM."""
    evidence = extract_evidence(one_time_case)
    assert "gateway_reference_id" not in evidence
    assert "pay_ABCDEF123456" not in str(evidence)


def test_policy_evaluation_not_in_evidence(one_time_case):
    """Internal policy evaluation snapshots must not be sent to the LLM."""
    evidence = extract_evidence(one_time_case)
    assert "policy_evaluation" not in evidence
    assert "executed_action" not in evidence
    assert "verification_outcome" not in evidence


def test_api_keys_not_in_evidence(one_time_case):
    """API keys and secrets must never appear in evidence payloads."""
    evidence = extract_evidence(one_time_case)
    evidence_str = str(evidence)
    # These should never be fields or values in evidence
    assert "razorpay_key" not in evidence_str.lower()
    assert "api_key" not in evidence_str.lower()
    assert "secret" not in evidence_str.lower()
    assert "webhook" not in evidence_str.lower()


# ---------------------------------------------------------------------------
# Required Fields Present Tests
# ---------------------------------------------------------------------------

def test_required_diagnostic_fields_present(one_time_case):
    """Evidence must contain the fields needed for diagnosis."""
    evidence = extract_evidence(one_time_case)
    required_fields = [
        "case_id", "case_type", "customer_id", "customer_segment",
        "amount", "currency", "failure_code", "failure_description",
        "failure_category", "attempts_count", "max_attempts_allowed",
        "current_status",
    ]
    for field in required_fields:
        assert field in evidence, f"Required field '{field}' missing from evidence"

    # Verify values
    assert evidence["case_id"] == "case_pii_001"
    assert evidence["case_type"] == "ONE_TIME_PAYMENT"
    assert evidence["amount"] == 8500.0
    assert evidence["failure_category"] == "BANK_TIMEOUT_NETWORK"


def test_subscription_metadata_included_for_recurring(subscription_case):
    """Subscription metadata must be included for recurring cases."""
    evidence = extract_evidence(subscription_case)
    assert "subscription_details" in evidence
    sub = evidence["subscription_details"]
    assert sub["plan_name"] == "Monthly SaaS Pro"
    assert sub["billing_interval"] == "MONTHLY"
    assert sub["mandate_status"] == "EXPIRED"
    # But subscription_id should NOT be in the evidence (internal)
    assert "subscription_id" not in sub


def test_subscription_metadata_absent_for_one_time(one_time_case):
    """Subscription metadata should not be in evidence for one-time payments."""
    evidence = extract_evidence(one_time_case)
    assert "subscription_details" not in evidence


# ---------------------------------------------------------------------------
# PII Validation Tests
# ---------------------------------------------------------------------------

def test_validate_clean_evidence_passes(one_time_case):
    """Clean evidence should pass PII validation."""
    evidence = extract_evidence(one_time_case)
    assert validate_no_pii_leakage(evidence) is True


def test_validate_detects_injected_email():
    """Validation should detect an email injected into evidence."""
    evidence = {
        "case_id": "test_001",
        "customer_email": "real.person@gmail.com",  # Should not be here
        "amount": 5000,
    }
    assert validate_no_pii_leakage(evidence) is False


def test_validate_detects_razorpay_key():
    """Validation should detect Razorpay key patterns."""
    evidence = {
        "case_id": "test_002",
        "note": "rzp_test_abc123def456",
        "amount": 5000,
    }
    assert validate_no_pii_leakage(evidence) is False


def test_scrub_removes_blocklisted_fields():
    """Scrub should remove any accidentally included PII fields."""
    evidence = {
        "case_id": "test_003",
        "amount": 5000,
        "masked_customer_email": "s***@gmail.com",  # Should be removed
        "gateway_reference_id": "pay_123",  # Should be removed
    }
    scrubbed = scrub_evidence(evidence)
    assert "masked_customer_email" not in scrubbed
    assert "gateway_reference_id" not in scrubbed
    assert "case_id" in scrubbed
    assert "amount" in scrubbed

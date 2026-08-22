"""PII Redaction & Evidence Extraction for Bounded LLM Diagnosis.

Extracts the minimum information needed for diagnosis from a RecoveryCase,
ensuring no raw PII, payment credentials, API keys, or unnecessary
personal information is sent to the LLM.

The evidence payload is the ONLY data the diagnosis agent receives.
"""

import re
import logging
from typing import Any, Dict, Optional
from ..schemas.case import RecoveryCase

logger = logging.getLogger(__name__)

# Fields that are NEVER included in LLM evidence
_PII_FIELD_BLOCKLIST = frozenset({
    "masked_customer_email",
    "masked_customer_phone",
    "gateway_reference_id",
    "policy_evaluation",
    "executed_action",
    "verification_outcome",
    "verified_recovered_amount",
    "created_at",
    "updated_at",
})

# Patterns that must never appear in evidence payloads
_SENSITIVE_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE),  # Email
    re.compile(r"(?<!\w)(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\w)"),  # Phone
    re.compile(r"rzp_(?:test|live)_\w+", re.IGNORECASE),  # Razorpay key IDs
    re.compile(r"sk_(?:test|live)_\w+", re.IGNORECASE),  # Stripe-style keys
    re.compile(r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*\S+", re.IGNORECASE),  # Generic secrets
]


def extract_evidence(case: RecoveryCase) -> Dict[str, Any]:
    """Extract sanitized evidence from a RecoveryCase for LLM diagnosis.

    Includes ONLY the fields needed for failure analysis:
    - Case identification (id, type)
    - Customer context (segment only — no email, phone, or raw PII)
    - Payment context (amount, currency)
    - Failure details (code, description, category)
    - Attempt history (count, max allowed, time since last attempt)
    - Subscription metadata (for recurring cases only)

    Returns:
        Dict with sanitized evidence fields. Safe to pass to the LLM.
    """
    evidence: Dict[str, Any] = {
        "case_id": case.id,
        "case_type": case.case_type.value,
        "customer_id": case.customer_id,
        "customer_segment": case.customer_segment,
        "amount": case.amount,
        "currency": case.currency,
        "failure_code": case.failure_code,
        "failure_description": case.failure_description,
        "failure_category": case.failure_category.value,
        "attempts_count": case.attempts_count,
        "max_attempts_allowed": case.max_attempts_allowed,
        "current_status": case.current_status.value,
    }

    # Include time since last attempt (duration, not timestamp)
    if case.last_attempt_at:
        evidence["last_attempt_at"] = case.last_attempt_at.isoformat()

    # Include subscription metadata for recurring cases (no PII)
    if case.subscription_details:
        evidence["subscription_details"] = {
            "plan_name": case.subscription_details.plan_name,
            "billing_interval": case.subscription_details.billing_interval,
            "mandate_status": case.subscription_details.mandate_status,
            "requires_afa": case.subscription_details.requires_afa,
        }

    return evidence


def validate_no_pii_leakage(evidence: Dict[str, Any]) -> bool:
    """Scan an evidence payload for accidental PII or secret leakage.

    Returns True if the evidence is clean, False if sensitive data is found.
    Logs a warning for each detected leak.
    """
    evidence_str = str(evidence)
    is_clean = True

    for pattern in _SENSITIVE_PATTERNS:
        matches = pattern.findall(evidence_str)
        if matches:
            logger.warning(
                "PII/secret pattern detected in evidence payload: %s",
                pattern.pattern,
            )
            is_clean = False

    # Check for blocklisted field names
    for field in _PII_FIELD_BLOCKLIST:
        if field in evidence:
            logger.warning("Blocklisted field '%s' found in evidence payload.", field)
            is_clean = False

    return is_clean


def scrub_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any accidentally included PII fields from evidence.

    This is a safety net — extract_evidence should never include these,
    but scrub_evidence provides defense-in-depth.
    """
    scrubbed = {k: v for k, v in evidence.items() if k not in _PII_FIELD_BLOCKLIST}
    return scrubbed

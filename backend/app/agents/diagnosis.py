"""Bounded Gemini Diagnosis Agent with Deterministic Fallback.

The LLM is strictly bounded to:
- Interpreting failure context
- Classifying root cause
- Summarizing evidence
- Proposing candidate recovery strategies
- Providing rationale

The LLM may NOT:
- Execute financial actions
- Authorize actions
- Modify policy rules or retry limits
- Override escalation or stopping rules
- Declare revenue recovered

If Gemini is unavailable, returns invalid output, or cannot be validated,
the system uses a deterministic rule-based fallback. It never fails open.
"""

import json
import logging
from typing import Any, Dict, Optional

from ..schemas.enums import CaseType, FailureCategory, RecoveryStrategy
from ..schemas.diagnosis import DiagnosisResult, get_allowed_strategies
from ..schemas.case import RecoveryCase
from .evidence import extract_evidence, validate_no_pii_leakage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deterministic Fallback Diagnosis Rules
# ---------------------------------------------------------------------------
# Maps each failure category to a default diagnosis, candidate strategies,
# and rationale. Used when Gemini is unavailable or returns invalid output.

_FALLBACK_RULES: Dict[FailureCategory, Dict[str, Any]] = {
    FailureCategory.INSUFFICIENT_FUNDS: {
        "diagnosis": "Payment failed due to insufficient funds in the customer's account.",
        "primary_candidates": [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK],
        "secondary_candidates": [RecoveryStrategy.SUBSCRIPTION_RETRY, RecoveryStrategy.UPDATE_PAYMENT_METHOD],
        "rationale": "Insufficient funds is typically transient. A delayed retry allows the customer time to replenish funds. A payment link provides an alternative collection path.",
        "confidence": 0.75,
    },
    FailureCategory.BANK_TIMEOUT_NETWORK: {
        "diagnosis": "Payment failed due to bank timeout or network connectivity issues during processing.",
        "primary_candidates": [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK],
        "secondary_candidates": [RecoveryStrategy.SUBSCRIPTION_RETRY, RecoveryStrategy.UPDATE_PAYMENT_METHOD],
        "rationale": "Bank timeouts and network errors are typically transient infrastructure issues. A retry after the cooldown period has high recovery probability.",
        "confidence": 0.85,
    },
    FailureCategory.AUTHENTICATION_OTP_FAILURE: {
        "diagnosis": "Payment failed because customer authentication (OTP/2FA) was not completed or timed out.",
        "primary_candidates": [RecoveryStrategy.PAYMENT_LINK, RecoveryStrategy.SMART_RETRY],
        "secondary_candidates": [RecoveryStrategy.UPDATE_PAYMENT_METHOD, RecoveryStrategy.SUBSCRIPTION_RETRY],
        "rationale": "OTP failures often indicate customer-side friction. A payment link gives the customer a fresh opportunity to complete authentication at their convenience.",
        "confidence": 0.70,
    },
    FailureCategory.EXPIRED_INSTRUMENT: {
        "diagnosis": "Payment failed because the payment instrument (card/bank account) has expired.",
        "primary_candidates": [RecoveryStrategy.PAYMENT_LINK, RecoveryStrategy.HUMAN_ESCALATION],
        "secondary_candidates": [RecoveryStrategy.UPDATE_PAYMENT_METHOD, RecoveryStrategy.HUMAN_ESCALATION],
        "rationale": "Expired instruments cannot be retried. The customer must provide an updated payment method. A payment link or mandate update flow is required.",
        "confidence": 0.90,
    },
    FailureCategory.RISK_SECURITY_BLOCK: {
        "diagnosis": "Payment was blocked by the bank's or gateway's risk/fraud detection system.",
        "primary_candidates": [RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP],
        "secondary_candidates": [RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP],
        "rationale": "Risk/security blocks require human review. Automated retries are prohibited as they may trigger further security alerts.",
        "confidence": 0.95,
    },
    FailureCategory.MANDATE_EXPIRED_INVALID: {
        "diagnosis": "Recurring payment failed because the mandate (e-mandate/autopay authorization) is expired or invalid.",
        "primary_candidates": [RecoveryStrategy.PAYMENT_LINK, RecoveryStrategy.HUMAN_ESCALATION],
        "secondary_candidates": [RecoveryStrategy.UPDATE_PAYMENT_METHOD, RecoveryStrategy.HUMAN_ESCALATION],
        "rationale": "Invalid mandates cannot be retried. The customer must re-authorize a new mandate or update their payment method.",
        "confidence": 0.90,
    },
    FailureCategory.GENERAL_TECHNICAL_ERROR: {
        "diagnosis": "Payment failed due to a general technical error in the payment processing pipeline.",
        "primary_candidates": [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK],
        "secondary_candidates": [RecoveryStrategy.SUBSCRIPTION_RETRY, RecoveryStrategy.UPDATE_PAYMENT_METHOD],
        "rationale": "General technical errors are often transient. A retry after the cooldown period is the standard first approach.",
        "confidence": 0.65,
    },
}


# ---------------------------------------------------------------------------
# Gemini Prompt Construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a payment failure diagnosis assistant for the AI Revenue Recovery Orchestrator.

Your role is STRICTLY LIMITED to analyzing payment failure evidence and providing a structured diagnosis.

You must NOT:
- Execute any financial actions
- Authorize payments or retries
- Modify policy rules or retry limits
- Override escalation or stopping decisions
- Declare revenue as recovered
- Access or request any API keys, secrets, or credentials
- Request personal customer information beyond what is provided

Analyze the provided payment failure evidence and respond with ONLY a JSON object."""


def _build_diagnosis_prompt(evidence: Dict[str, Any], case_type: CaseType) -> str:
    """Build the bounded diagnosis prompt with sanitized evidence."""
    allowed = get_allowed_strategies(case_type)
    strategy_names = [s.value for s in allowed]

    failure_categories = [fc.value for fc in FailureCategory]

    return f"""{_SYSTEM_PROMPT}

Payment failure evidence:
{json.dumps(evidence, indent=2, default=str)}

Respond with a JSON object containing exactly these fields:
- "diagnosis": A clear 1-2 sentence summary of the failure root cause.
- "failure_category": One of {failure_categories}
- "candidate_strategies": An ordered array of recommended strategies from {strategy_names} (most recommended first).
- "rationale": Brief explanation of why these strategies are recommended.
- "confidence": A float between 0.0 and 1.0 indicating your confidence in this diagnosis.

Respond with ONLY the JSON object. No additional text."""


# ---------------------------------------------------------------------------
# Diagnosis Agent
# ---------------------------------------------------------------------------

class DiagnosisAgent:
    """Bounded diagnosis agent using Gemini with deterministic fallback.

    Architecture:
        1. Extract sanitized evidence (PII redacted)
        2. Attempt Gemini diagnosis with structured output validation
        3. If Gemini fails → use deterministic fallback rules
        4. Validate and return DiagnosisResult

    The diagnosis NEVER executes actions or modifies policy.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model = model
        self._client = None

        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
                logger.info("Gemini diagnosis agent initialized (model=%s)", model)
            except Exception as e:
                logger.warning("Failed to initialize Gemini client: %s. Using fallback.", e)
                self._client = None
        else:
            logger.info("No Gemini API key configured. Using deterministic fallback diagnosis.")

    def diagnose(self, case: RecoveryCase) -> DiagnosisResult:
        """Diagnose a recovery case. Returns validated DiagnosisResult.

        Flow:
            1. Extract evidence (PII redacted)
            2. Try Gemini → validate → return
            3. On any failure → deterministic fallback → return

        Never fails open. Always returns a valid DiagnosisResult.
        """
        # Step 1: Extract sanitized evidence
        evidence = extract_evidence(case)

        # Safety check: verify no PII leaked into evidence
        if not validate_no_pii_leakage(evidence):
            logger.error("PII detected in evidence payload. Using fallback diagnosis.")
            return self._fallback_diagnosis(case)

        # Step 2: Try Gemini diagnosis
        if self._client:
            try:
                result = self._gemini_diagnosis(evidence, case)
                if result:
                    return result
            except Exception as e:
                logger.warning("Gemini diagnosis failed: %s. Using fallback.", e)

        # Step 3: Deterministic fallback
        return self._fallback_diagnosis(case)

    def _gemini_diagnosis(
        self, evidence: Dict[str, Any], case: RecoveryCase
    ) -> Optional[DiagnosisResult]:
        """Attempt bounded Gemini diagnosis with structured output validation."""
        from google.genai import types

        prompt = _build_diagnosis_prompt(evidence, case.case_type)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,  # Low temperature for consistent diagnosis
                    max_output_tokens=1024,
                ),
            )

            if not response or not response.text:
                logger.warning("Empty Gemini response. Falling back.")
                return None

            return self._validate_gemini_response(response.text, case)

        except Exception as e:
            logger.warning("Gemini API call failed: %s", e)
            return None

    def _validate_gemini_response(
        self, response_text: str, case: RecoveryCase
    ) -> Optional[DiagnosisResult]:
        """Parse and validate the Gemini JSON response.

        Rejects:
        - Malformed JSON
        - Missing required fields
        - Invalid failure categories
        - Strategies outside the locked action space
        - Confidence outside [0.0, 1.0]
        """
        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Gemini returned malformed JSON. Rejecting.")
            return None

        if not isinstance(raw, dict):
            logger.warning("Gemini response is not a JSON object. Rejecting.")
            return None

        # Validate failure_category
        try:
            failure_cat = FailureCategory(raw.get("failure_category", ""))
        except ValueError:
            logger.warning(
                "Gemini returned invalid failure_category: %s. Rejecting.",
                raw.get("failure_category"),
            )
            return None

        # Validate candidate strategies strictly against the locked action space for this case_type
        allowed = get_allowed_strategies(case.case_type)
        allowed_values = {s.value for s in allowed}
        raw_strategies = raw.get("candidate_strategies", [])

        if not isinstance(raw_strategies, list) or len(raw_strategies) == 0:
            logger.warning("candidate_strategies is missing, empty, or not a list. Rejecting Gemini output.")
            return None

        valid_strategies = []
        for s in raw_strategies:
            if not isinstance(s, str) or s not in allowed_values:
                logger.warning(
                    "Gemini proposed strategy '%s' which is invalid or outside locked action space for %s. Rejecting entire response.",
                    s,
                    case.case_type.value,
                )
                return None
            valid_strategies.append(RecoveryStrategy(s))

        # Validate confidence
        confidence = raw.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        # Build validated DiagnosisResult
        try:
            result = DiagnosisResult(
                case_id=case.id,
                diagnosis=str(raw.get("diagnosis", "Diagnosis provided by Gemini.")),
                failure_category=failure_cat,
                candidate_strategies=valid_strategies,
                rationale=str(raw.get("rationale", "Strategy recommended by AI diagnosis.")),
                confidence=confidence,
                is_fallback=False,
            )
            return result
        except Exception as e:
            logger.warning("Failed to construct DiagnosisResult from Gemini output: %s", e)
            return None

    def _fallback_diagnosis(self, case: RecoveryCase) -> DiagnosisResult:
        """Deterministic rule-based fallback diagnosis.

        Maps failure_category to predefined diagnosis, candidates, and rationale.
        Always produces a valid DiagnosisResult. Never fails open.
        """
        rules = _FALLBACK_RULES.get(case.failure_category)

        if not rules:
            # Ultimate safety net: unknown category → escalate
            logger.warning(
                "No fallback rule for category '%s'. Escalating.", case.failure_category.value
            )
            return DiagnosisResult(
                case_id=case.id,
                diagnosis=f"Unknown failure category: {case.failure_category.value}. Requires human review.",
                failure_category=case.failure_category,
                candidate_strategies=[RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP],
                rationale="Failure category has no predefined recovery path. Human escalation required.",
                confidence=0.3,
                is_fallback=True,
            )

        # Select candidates based on case type
        if case.case_type == CaseType.SUBSCRIPTION_RECURRING:
            candidates = rules["secondary_candidates"]
        else:
            candidates = rules["primary_candidates"]

        return DiagnosisResult(
            case_id=case.id,
            diagnosis=rules["diagnosis"],
            failure_category=case.failure_category,
            candidate_strategies=candidates,
            rationale=rules["rationale"],
            confidence=rules["confidence"],
            is_fallback=True,
        )

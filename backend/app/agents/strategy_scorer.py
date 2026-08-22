"""Deterministic Strategy Scoring Engine.

Produces an inspectable, reproducible ranking of candidate recovery strategies.
Given identical inputs and configuration, the scorer ALWAYS produces identical results.

The scorer does NOT call Gemini or any external service.
The scorer does NOT execute financial actions.
The Policy Engine remains the final authority over whether the recommended action is permitted.

Architecture:
    Evidence → Diagnosis → Candidate Strategies → **Strategy Scoring** → Policy Engine → Execution

Scoring Formula:
    Score(strategy) = base_score + Σ(signal_weight × signal_value)

All weights are explicit and inspectable in the SCORING_WEIGHTS configuration.
"""

import logging
from typing import Dict, List, Optional

from ..schemas.enums import CaseType, FailureCategory, RecoveryStrategy
from ..schemas.diagnosis import (
    DiagnosisResult,
    StrategyRankingResult,
    StrategyScore,
    get_allowed_strategies,
)
from ..schemas.case import RecoveryCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scoring Configuration — All weights are explicit and inspectable
# ---------------------------------------------------------------------------

# Base scores for each strategy (before signal adjustments)
BASE_SCORES: Dict[RecoveryStrategy, float] = {
    RecoveryStrategy.SMART_RETRY: 70.0,
    RecoveryStrategy.PAYMENT_LINK: 40.0,
    RecoveryStrategy.SUBSCRIPTION_RETRY: 70.0,
    RecoveryStrategy.UPDATE_PAYMENT_METHOD: 40.0,
    RecoveryStrategy.HUMAN_ESCALATION: 20.0,
    RecoveryStrategy.STOP: 10.0,
}

# Signal 1: Failure category weights per strategy
# Each failure category adjusts the base score of each strategy
FAILURE_CATEGORY_WEIGHTS: Dict[FailureCategory, Dict[RecoveryStrategy, float]] = {
    FailureCategory.INSUFFICIENT_FUNDS: {
        RecoveryStrategy.SMART_RETRY: +15.0,
        RecoveryStrategy.PAYMENT_LINK: +5.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: +15.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: +5.0,
        RecoveryStrategy.HUMAN_ESCALATION: -5.0,
        RecoveryStrategy.STOP: -10.0,
    },
    FailureCategory.BANK_TIMEOUT_NETWORK: {
        RecoveryStrategy.SMART_RETRY: +20.0,
        RecoveryStrategy.PAYMENT_LINK: 0.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: +20.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: 0.0,
        RecoveryStrategy.HUMAN_ESCALATION: -10.0,
        RecoveryStrategy.STOP: -15.0,
    },
    FailureCategory.AUTHENTICATION_OTP_FAILURE: {
        RecoveryStrategy.SMART_RETRY: +5.0,
        RecoveryStrategy.PAYMENT_LINK: +15.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: +5.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: +10.0,
        RecoveryStrategy.HUMAN_ESCALATION: 0.0,
        RecoveryStrategy.STOP: -5.0,
    },
    FailureCategory.EXPIRED_INSTRUMENT: {
        RecoveryStrategy.SMART_RETRY: -40.0,
        RecoveryStrategy.PAYMENT_LINK: +25.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: -40.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: +30.0,
        RecoveryStrategy.HUMAN_ESCALATION: +5.0,
        RecoveryStrategy.STOP: 0.0,
    },
    FailureCategory.RISK_SECURITY_BLOCK: {
        RecoveryStrategy.SMART_RETRY: -40.0,
        RecoveryStrategy.PAYMENT_LINK: -20.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: -40.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: -20.0,
        RecoveryStrategy.HUMAN_ESCALATION: +35.0,
        RecoveryStrategy.STOP: +10.0,
    },
    FailureCategory.MANDATE_EXPIRED_INVALID: {
        RecoveryStrategy.SMART_RETRY: -40.0,
        RecoveryStrategy.PAYMENT_LINK: +10.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: -30.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: +30.0,
        RecoveryStrategy.HUMAN_ESCALATION: +5.0,
        RecoveryStrategy.STOP: 0.0,
    },
    FailureCategory.GENERAL_TECHNICAL_ERROR: {
        RecoveryStrategy.SMART_RETRY: +10.0,
        RecoveryStrategy.PAYMENT_LINK: +5.0,
        RecoveryStrategy.SUBSCRIPTION_RETRY: +10.0,
        RecoveryStrategy.UPDATE_PAYMENT_METHOD: +5.0,
        RecoveryStrategy.HUMAN_ESCALATION: 0.0,
        RecoveryStrategy.STOP: -5.0,
    },
}

# Signal 2: Attempt exhaustion thresholds and adjustments
# Applied when attempts_count / max_attempts_allowed reaches a threshold
ATTEMPT_EXHAUSTION_THRESHOLDS = [
    {
        "ratio": 0.67,  # 2/3 of max attempts used
        "adjustments": {
            RecoveryStrategy.SMART_RETRY: -15.0,
            RecoveryStrategy.PAYMENT_LINK: +10.0,
            RecoveryStrategy.SUBSCRIPTION_RETRY: -15.0,
            RecoveryStrategy.UPDATE_PAYMENT_METHOD: +10.0,
            RecoveryStrategy.HUMAN_ESCALATION: +5.0,
            RecoveryStrategy.STOP: +5.0,
        },
    },
    {
        "ratio": 1.0,  # Max attempts reached or exceeded
        "adjustments": {
            RecoveryStrategy.SMART_RETRY: -30.0,
            RecoveryStrategy.PAYMENT_LINK: +15.0,
            RecoveryStrategy.SUBSCRIPTION_RETRY: -30.0,
            RecoveryStrategy.UPDATE_PAYMENT_METHOD: +15.0,
            RecoveryStrategy.HUMAN_ESCALATION: +10.0,
            RecoveryStrategy.STOP: +10.0,
        },
    },
]

# Signal 3: Amount tier thresholds and adjustments
AMOUNT_TIERS = [
    {
        "name": "LOW",
        "max_amount": 1000.0,
        "adjustments": {
            RecoveryStrategy.SMART_RETRY: +5.0,
            RecoveryStrategy.SUBSCRIPTION_RETRY: +5.0,
            RecoveryStrategy.STOP: +5.0,
        },
    },
    {
        "name": "STANDARD",
        "max_amount": 15000.0,
        "adjustments": {},  # No adjustment for standard range
    },
    {
        "name": "HIGH",
        "max_amount": float("inf"),
        "adjustments": {
            RecoveryStrategy.SMART_RETRY: -10.0,
            RecoveryStrategy.SUBSCRIPTION_RETRY: -10.0,
            RecoveryStrategy.HUMAN_ESCALATION: +20.0,
        },
    },
]


# ---------------------------------------------------------------------------
# Strategy Scorer
# ---------------------------------------------------------------------------

class StrategyScorer:
    """Deterministic strategy scoring engine.

    Computes an inspectable score for each allowed strategy based on
    explicit, configurable signal weights. Identical inputs always
    produce identical outputs.

    This scorer does NOT call any LLM or external API.
    """

    def __init__(
        self,
        base_scores: Optional[Dict[RecoveryStrategy, float]] = None,
        failure_weights: Optional[Dict[FailureCategory, Dict[RecoveryStrategy, float]]] = None,
        attempt_thresholds: Optional[list] = None,
        amount_tiers: Optional[list] = None,
    ):
        self.base_scores = base_scores or BASE_SCORES
        self.failure_weights = failure_weights or FAILURE_CATEGORY_WEIGHTS
        self.attempt_thresholds = attempt_thresholds or ATTEMPT_EXHAUSTION_THRESHOLDS
        self.amount_tiers = amount_tiers or AMOUNT_TIERS

    def score(
        self,
        case: RecoveryCase,
        diagnosis: DiagnosisResult,
    ) -> StrategyRankingResult:
        """Score and rank all allowed strategies for a recovery case.

        Args:
            case: The recovery case to score strategies for.
            diagnosis: The validated diagnosis result (from Gemini or fallback).

        Returns:
            StrategyRankingResult with ranked strategies and signal breakdowns.
        """
        allowed = get_allowed_strategies(case.case_type)
        scored: List[StrategyScore] = []

        for strategy in allowed:
            contributions: Dict[str, float] = {}

            # Base score
            base = self.base_scores.get(strategy, 0.0)
            contributions["base_score"] = base

            # Signal 1: Failure category
            fc_weight = self._get_failure_category_weight(diagnosis.failure_category, strategy)
            contributions["failure_category"] = fc_weight

            # Signal 2: Attempt exhaustion
            attempt_adj = self._get_attempt_exhaustion_adjustment(case, strategy)
            contributions["attempt_exhaustion"] = attempt_adj

            # Signal 3: Amount tier
            amount_adj = self._get_amount_tier_adjustment(case.amount, strategy)
            contributions["amount_tier"] = amount_adj

            # Signal 4: Diagnosis confidence boost
            # If the diagnosis specifically recommends this strategy, boost it
            confidence_boost = self._get_diagnosis_confidence_boost(
                strategy, diagnosis
            )
            contributions["diagnosis_alignment"] = confidence_boost

            # Total score
            total = sum(contributions.values())
            scored.append(
                StrategyScore(
                    strategy=strategy,
                    score=round(total, 2),
                    signal_contributions=contributions,
                )
            )

        # Sort by score descending (stable sort preserves order for ties)
        scored.sort(key=lambda s: s.score, reverse=True)

        # Top strategy
        recommended = scored[0].strategy
        max_score = scored[0].score
        min_score = scored[-1].score if scored else 0
        score_range = max_score - min_score if max_score != min_score else 1.0

        # Normalize confidence: how much the top strategy dominates
        normalized_confidence = min(1.0, max(0.0, (max_score - min_score) / score_range * 0.5 + 0.5))

        return StrategyRankingResult(
            case_id=case.id,
            case_type=case.case_type,
            ranked_strategies=scored,
            recommended_strategy=recommended,
            recommended_confidence=round(normalized_confidence, 3),
        )

    def _get_failure_category_weight(
        self, category: FailureCategory, strategy: RecoveryStrategy
    ) -> float:
        """Get the failure category weight for a strategy."""
        category_weights = self.failure_weights.get(category, {})
        return category_weights.get(strategy, 0.0)

    def _get_attempt_exhaustion_adjustment(
        self, case: RecoveryCase, strategy: RecoveryStrategy
    ) -> float:
        """Get adjustment based on how many attempts have been used."""
        if case.max_attempts_allowed <= 0:
            return 0.0

        ratio = case.attempts_count / case.max_attempts_allowed
        adjustment = 0.0

        # Apply the highest matching threshold
        for threshold in self.attempt_thresholds:
            if ratio >= threshold["ratio"]:
                adjustment = threshold["adjustments"].get(strategy, 0.0)

        return adjustment

    def _get_amount_tier_adjustment(
        self, amount: float, strategy: RecoveryStrategy
    ) -> float:
        """Get adjustment based on amount tier."""
        for tier in self.amount_tiers:
            if amount <= tier["max_amount"]:
                return tier["adjustments"].get(strategy, 0.0)
        return 0.0

    def _get_diagnosis_confidence_boost(
        self,
        strategy: RecoveryStrategy,
        diagnosis: DiagnosisResult,
    ) -> float:
        """Boost score if the diagnosis specifically recommends this strategy.

        The boost is proportional to the diagnosis confidence and the
        strategy's position in the candidate list (first = highest boost).
        """
        if strategy not in diagnosis.candidate_strategies:
            return 0.0

        position = diagnosis.candidate_strategies.index(strategy)
        # First candidate gets full boost, subsequent get diminishing boost
        position_factor = max(0.0, 1.0 - (position * 0.3))
        boost = diagnosis.confidence * 10.0 * position_factor

        return round(boost, 2)

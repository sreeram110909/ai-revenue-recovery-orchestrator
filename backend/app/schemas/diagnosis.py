"""Pydantic Schemas for Diagnosis Output and Strategy Scoring.

DiagnosisResult is the validated output from the bounded Gemini diagnosis
or from the deterministic fallback diagnosis. It is never used to directly
authorize or execute financial actions.

StrategyScore provides an inspectable, deterministic ranking of candidate
recovery strategies.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from .enums import CaseType, FailureCategory, RecoveryStrategy


# Locked action spaces per case type
PRIMARY_STRATEGIES = [
    RecoveryStrategy.SMART_RETRY,
    RecoveryStrategy.PAYMENT_LINK,
    RecoveryStrategy.HUMAN_ESCALATION,
    RecoveryStrategy.STOP,
]

SECONDARY_STRATEGIES = [
    RecoveryStrategy.SUBSCRIPTION_RETRY,
    RecoveryStrategy.UPDATE_PAYMENT_METHOD,
    RecoveryStrategy.HUMAN_ESCALATION,
    RecoveryStrategy.STOP,
]


def get_allowed_strategies(case_type: CaseType) -> List[RecoveryStrategy]:
    """Return the locked action space for a given case type."""
    if case_type == CaseType.SUBSCRIPTION_RECURRING:
        return SECONDARY_STRATEGIES
    return PRIMARY_STRATEGIES


class DiagnosisResult(BaseModel):
    """Structured output from Gemini diagnosis or fallback.

    This schema is used to validate LLM responses. Malformed or invalid
    responses are rejected and the fallback path is used instead.

    The diagnosis does NOT authorize or execute any action.
    """
    case_id: str
    diagnosis: str = Field(description="1-2 sentence root cause summary")
    failure_category: FailureCategory
    candidate_strategies: List[RecoveryStrategy] = Field(
        description="Ordered list of recommended strategies from the locked action space"
    )
    rationale: str = Field(description="Brief explanation of strategy recommendation")
    confidence: float = Field(ge=0.0, le=1.0, description="Diagnosis confidence score")
    is_fallback: bool = Field(default=False, description="True if rule-based fallback was used")

    @field_validator("candidate_strategies")
    @classmethod
    def validate_strategies_not_empty(cls, v):
        if not v:
            raise ValueError("candidate_strategies must contain at least one strategy")
        return v


class StrategyScore(BaseModel):
    """Inspectable score for a single candidate strategy.

    The signal_contributions dict shows exactly how each signal
    contributed to the final score, enabling full transparency.
    """
    strategy: RecoveryStrategy
    score: float
    signal_contributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of how each scoring signal contributed to the total score"
    )


class StrategyRankingResult(BaseModel):
    """Complete scoring result with ranked strategies.

    Given identical inputs and configuration, the scorer always
    produces identical results.
    """
    case_id: str
    case_type: CaseType
    ranked_strategies: List[StrategyScore] = Field(
        description="Strategies ranked by score (highest first)"
    )
    recommended_strategy: RecoveryStrategy = Field(
        description="Top-ranked strategy (highest score)"
    )
    recommended_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Normalized confidence for the recommendation"
    )

    @property
    def strategy_names(self) -> List[str]:
        """List of strategy names in ranked order."""
        return [s.strategy.value for s in self.ranked_strategies]

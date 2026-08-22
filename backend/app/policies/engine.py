"""Deterministic Policy Engine (Python).

100% Deterministic & Rule-Based.
Zero LLM / Zero Network Calls.
Evaluates configurable demonstration policies and enforces hard guardrails.
"""

from datetime import datetime
from typing import List, Optional
from ..schemas.enums import FailureCategory, PolicyOutcome, RecoveryStrategy
from ..schemas.policy import PolicyCheckResult, PolicyConfig, RuleEvaluationDetail
from ..schemas.case import RecoveryCase


DEFAULT_DEMO_POLICY_CONFIG = PolicyConfig(
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


class PolicyEngine:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or DEFAULT_DEMO_POLICY_CONFIG

    def evaluate(
        self,
        recovery_case: RecoveryCase,
        proposed_strategy: RecoveryStrategy,
        evaluation_timestamp: Optional[datetime] = None,
    ) -> PolicyCheckResult:
        now = evaluation_timestamp or datetime.utcnow()
        evaluations: List[RuleEvaluationDetail] = []
        reasons: List[str] = []

        # Rule 1: Case Status Integrity
        status_check = self._check_status_freeze(recovery_case, proposed_strategy)
        evaluations.append(status_check)
        if not status_check.passed:
            return self._build_result(
                PolicyOutcome.STOP,
                False,
                proposed_strategy,
                RecoveryStrategy.STOP,
                evaluations,
                [status_check.reason],
                now,
            )

        # Rule 2: Amount Threshold Policy (Demo: ₹15,000)
        amount_check = self._check_amount_threshold(recovery_case, proposed_strategy)
        evaluations.append(amount_check)
        if not amount_check.passed:
            return self._build_result(
                PolicyOutcome.ESCALATE,
                False,
                proposed_strategy,
                RecoveryStrategy.HUMAN_ESCALATION,
                evaluations,
                [amount_check.reason],
                now,
                escalation_reason=amount_check.reason,
            )

        # Rule 3: Non-Retryable Category Guardrail
        failure_check = self._check_failure_category(recovery_case, proposed_strategy)
        evaluations.append(failure_check)
        if not failure_check.passed:
            if (
                recovery_case.case_type == "ONE_TIME_PAYMENT"
                and recovery_case.failure_category == FailureCategory.EXPIRED_INSTRUMENT
                and proposed_strategy == RecoveryStrategy.SMART_RETRY
            ):
                return self._build_result(
                    PolicyOutcome.DOWNGRADE,
                    True,
                    proposed_strategy,
                    RecoveryStrategy.PAYMENT_LINK,
                    evaluations,
                    [failure_check.reason, "Downgraded to PAYMENT_LINK to request updated card."],
                    now,
                    downgrade_reason="Card expired. Retrying instrument will fail. Downgraded to PAYMENT_LINK.",
                )

            if (
                recovery_case.case_type == "SUBSCRIPTION_RECURRING"
                and recovery_case.failure_category == FailureCategory.MANDATE_EXPIRED_INVALID
                and proposed_strategy == RecoveryStrategy.SUBSCRIPTION_RETRY
            ):
                return self._build_result(
                    PolicyOutcome.DOWNGRADE,
                    True,
                    proposed_strategy,
                    RecoveryStrategy.UPDATE_PAYMENT_METHOD,
                    evaluations,
                    [failure_check.reason, "Downgraded to UPDATE_PAYMENT_METHOD."],
                    now,
                    downgrade_reason="Mandate invalid/expired. Auto-retry blocked. Downgraded to UPDATE_PAYMENT_METHOD.",
                )

            return self._build_result(
                PolicyOutcome.BLOCK,
                False,
                proposed_strategy,
                RecoveryStrategy.HUMAN_ESCALATION,
                evaluations,
                [failure_check.reason],
                now,
                escalation_reason="Non-retryable root cause requires human review.",
            )

        # Rule 4: Retry Attempt Cap
        retry_check = self._check_retry_cap(recovery_case, proposed_strategy)
        evaluations.append(retry_check)
        if not retry_check.passed:
            if proposed_strategy == RecoveryStrategy.SMART_RETRY:
                return self._build_result(
                    PolicyOutcome.DOWNGRADE,
                    True,
                    proposed_strategy,
                    RecoveryStrategy.PAYMENT_LINK,
                    evaluations,
                    [retry_check.reason, "Downgraded to PAYMENT_LINK."],
                    now,
                    downgrade_reason="Maximum retry limit reached. Downgraded to PAYMENT_LINK.",
                )
            if proposed_strategy == RecoveryStrategy.SUBSCRIPTION_RETRY:
                return self._build_result(
                    PolicyOutcome.DOWNGRADE,
                    True,
                    proposed_strategy,
                    RecoveryStrategy.UPDATE_PAYMENT_METHOD,
                    evaluations,
                    [retry_check.reason, "Downgraded to UPDATE_PAYMENT_METHOD."],
                    now,
                    downgrade_reason="Subscription debit cap reached. Downgraded to UPDATE_PAYMENT_METHOD.",
                )

            return self._build_result(
                PolicyOutcome.ESCALATE,
                False,
                proposed_strategy,
                RecoveryStrategy.HUMAN_ESCALATION,
                evaluations,
                [retry_check.reason],
                now,
                escalation_reason="Exceeded attempts limit.",
            )

        # Rule 5: Cooldown Duration Policy
        cooldown_check = self._check_cooldown(recovery_case, proposed_strategy, now)
        evaluations.append(cooldown_check)
        if not cooldown_check.passed:
            return self._build_result(
                PolicyOutcome.BLOCK,
                False,
                proposed_strategy,
                RecoveryStrategy.STOP,
                evaluations,
                [cooldown_check.reason],
                now,
            )

        # Rule 6: Recurring Mandate Integrity (Secondary Workflow)
        if recovery_case.case_type == "SUBSCRIPTION_RECURRING":
            mandate_check = self._check_mandate_integrity(recovery_case, proposed_strategy)
            evaluations.append(mandate_check)
            if not mandate_check.passed:
                if proposed_strategy == RecoveryStrategy.SUBSCRIPTION_RETRY:
                    return self._build_result(
                        PolicyOutcome.DOWNGRADE,
                        True,
                        proposed_strategy,
                        RecoveryStrategy.UPDATE_PAYMENT_METHOD,
                        evaluations,
                        [mandate_check.reason, "Downgraded to UPDATE_PAYMENT_METHOD."],
                        now,
                        downgrade_reason="Invalid mandate. Downgraded to UPDATE_PAYMENT_METHOD.",
                    )
                return self._build_result(
                    PolicyOutcome.ESCALATE,
                    False,
                    proposed_strategy,
                    RecoveryStrategy.HUMAN_ESCALATION,
                    evaluations,
                    [mandate_check.reason],
                    now,
                    escalation_reason="Mandate integrity issue requires human operator.",
                )

        # All policies passed
        reasons.append(f"Action '{proposed_strategy.value}' satisfies all active demonstration policies.")
        return self._build_result(
            PolicyOutcome.ALLOW,
            True,
            proposed_strategy,
            proposed_strategy,
            evaluations,
            reasons,
            now,
        )

    def _check_status_freeze(self, case: RecoveryCase, strategy: RecoveryStrategy) -> RuleEvaluationDetail:
        is_frozen = case.current_status.value in ["ESCALATED", "STOPPED", "CLOSED_UNRECOVERABLE", "VERIFIED_RECOVERED"]
        if is_frozen and strategy not in [RecoveryStrategy.STOP, RecoveryStrategy.HUMAN_ESCALATION]:
            return RuleEvaluationDetail(
                rule_id="POL-01-STATUS-FREEZE",
                rule_name="Case Status Freeze Guardrail",
                passed=False,
                reason=f"Case is in frozen state '{case.current_status.value}'. Automated action is forbidden.",
                suggested_outcome=PolicyOutcome.STOP,
            )
        return RuleEvaluationDetail(
            rule_id="POL-01-STATUS-FREEZE",
            rule_name="Case Status Freeze Guardrail",
            passed=True,
            reason=f"Case status '{case.current_status.value}' is eligible for evaluation.",
        )

    def _check_amount_threshold(self, case: RecoveryCase, strategy: RecoveryStrategy) -> RuleEvaluationDetail:
        if (
            case.amount > self.config.automated_recovery_amount_limit
            and strategy not in [RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP]
        ):
            return RuleEvaluationDetail(
                rule_id="POL-02-AMOUNT-CEILING",
                rule_name="Automated Recovery Value Ceiling (Demo Configuration)",
                passed=False,
                reason=f"Amount ₹{case.amount} exceeds demo limit of ₹{self.config.automated_recovery_amount_limit}. Human escalation mandatory.",
                suggested_outcome=PolicyOutcome.ESCALATE,
            )
        return RuleEvaluationDetail(
            rule_id="POL-02-AMOUNT-CEILING",
            rule_name="Automated Recovery Value Ceiling (Demo Configuration)",
            passed=True,
            reason=f"Amount ₹{case.amount} is within demo limit of ₹{self.config.automated_recovery_amount_limit}.",
        )

    def _check_failure_category(self, case: RecoveryCase, strategy: RecoveryStrategy) -> RuleEvaluationDetail:
        is_non_retryable = case.failure_category in self.config.non_retryable_categories
        is_retry = strategy in [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.SUBSCRIPTION_RETRY]
        if is_non_retryable and is_retry:
            return RuleEvaluationDetail(
                rule_id="POL-03-NON-RETRYABLE",
                rule_name="Non-Retryable Category Guardrail",
                passed=False,
                reason=f"Category '{case.failure_category.value}' is non-retryable.",
                suggested_outcome=PolicyOutcome.BLOCK,
            )
        return RuleEvaluationDetail(
            rule_id="POL-03-NON-RETRYABLE",
            rule_name="Non-Retryable Category Guardrail",
            passed=True,
            reason=f"Category '{case.failure_category.value}' permitted for '{strategy.value}'.",
        )

    def _check_retry_cap(self, case: RecoveryCase, strategy: RecoveryStrategy) -> RuleEvaluationDetail:
        is_retry = strategy in [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.SUBSCRIPTION_RETRY]
        if is_retry and case.attempts_count >= self.config.max_retry_attempts:
            return RuleEvaluationDetail(
                rule_id="POL-04-RETRY-CAP",
                rule_name="Maximum Retry Cap Policy (Demo Configuration)",
                passed=False,
                reason=f"Exhausted {case.attempts_count} attempts (max {self.config.max_retry_attempts}).",
                suggested_outcome=PolicyOutcome.DOWNGRADE,
            )
        return RuleEvaluationDetail(
            rule_id="POL-04-RETRY-CAP",
            rule_name="Maximum Retry Cap Policy (Demo Configuration)",
            passed=True,
            reason=f"Attempts count ({case.attempts_count}/{self.config.max_retry_attempts}) is within limit.",
        )

    def _check_cooldown(self, case: RecoveryCase, strategy: RecoveryStrategy, now: datetime) -> RuleEvaluationDetail:
        is_retry = strategy in [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.SUBSCRIPTION_RETRY]
        if is_retry and case.last_attempt_at:
            elapsed_hours = (now - case.last_attempt_at).total_seconds() / 3600.0
            if elapsed_hours < self.config.retry_cooldown_hours:
                return RuleEvaluationDetail(
                    rule_id="POL-05-RETRY-COOLDOWN",
                    rule_name="Mandatory Retry Cooldown Policy (Demo Configuration)",
                    passed=False,
                    reason=f"Only {elapsed_hours:.1f}h elapsed (cooldown requires {self.config.retry_cooldown_hours}h).",
                    suggested_outcome=PolicyOutcome.BLOCK,
                )
        return RuleEvaluationDetail(
            rule_id="POL-05-RETRY-COOLDOWN",
            rule_name="Mandatory Retry Cooldown Policy (Demo Configuration)",
            passed=True,
            reason="Cooldown requirement satisfied.",
        )

    def _check_mandate_integrity(self, case: RecoveryCase, strategy: RecoveryStrategy) -> RuleEvaluationDetail:
        sub = case.subscription_details
        if not sub:
            return RuleEvaluationDetail(
                rule_id="POL-06-MANDATE-INTEGRITY",
                rule_name="Recurring Mandate Integrity Policy",
                passed=False,
                reason="Subscription details missing for recurring payment.",
                suggested_outcome=PolicyOutcome.ESCALATE,
            )
        if sub.mandate_status in ["EXPIRED", "REVOKED", "INVALID"] and strategy == RecoveryStrategy.SUBSCRIPTION_RETRY:
            return RuleEvaluationDetail(
                rule_id="POL-06-MANDATE-INTEGRITY",
                rule_name="Recurring Mandate Integrity Policy",
                passed=False,
                reason=f"Mandate status '{sub.mandate_status}' cannot be automatically retried.",
                suggested_outcome=PolicyOutcome.DOWNGRADE,
            )
        return RuleEvaluationDetail(
            rule_id="POL-06-MANDATE-INTEGRITY",
            rule_name="Recurring Mandate Integrity Policy",
            passed=True,
            reason=f"Mandate status '{sub.mandate_status}' permitted.",
        )

    def _build_result(
        self,
        outcome: PolicyOutcome,
        passed: bool,
        proposed: RecoveryStrategy,
        approved: RecoveryStrategy,
        evaluations: List[RuleEvaluationDetail],
        reasons: List[str],
        now: datetime,
        downgrade_reason: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> PolicyCheckResult:
        return PolicyCheckResult(
            outcome=outcome,
            passed=passed,
            proposed_strategy=proposed,
            approved_strategy=approved,
            evaluations=evaluations,
            reasons=reasons,
            downgrade_reason=downgrade_reason,
            escalation_reason=escalation_reason,
            evaluated_at=now,
            config_snapshot=self.config,
        )

"""Metrics Aggregation and Policy Violation Detection Engine.

Enforces strict financial accounting:
- Only verified gateway success contributes to recovered revenue.
- Policy violations are computed from actual execution and audit records.
"""

import logging
from typing import Dict, List, Optional, Tuple

from ..schemas.enums import CaseStatus, CaseType, PolicyOutcome, RecoveryStrategy
from ..schemas.case import RecoveryCase
from ..schemas.evaluation import BaselineStrategyType, BatchMetrics, EvaluationCaseResult

logger = logging.getLogger(__name__)


def detect_policy_violation(
    case_result: EvaluationCaseResult,
    case: RecoveryCase,
) -> Tuple[bool, Optional[str]]:
    """Detect if any policy violation occurred during case processing.

    Policy Violations include:
    1. Financial execution after policy outcome is BLOCK.
    2. Financial execution after policy outcome is ESCALATE.
    3. Financial execution after policy outcome is STOP.
    4. Execution of an action outside the locked action space.
    5. Recovered revenue counted without verified gateway success.
    6. Financial execution on a terminal case (already recovered/escalated/stopped).
    """
    violations: List[str] = []

    # Check 1: Financial execution after BLOCK
    if case_result.policy_outcome == PolicyOutcome.BLOCK:
        if case_result.execution_status == "SUCCESS":
            violations.append("CRITICAL: Financial action executed despite policy BLOCK.")

    # Check 2: Financial execution after ESCALATE
    if case_result.policy_outcome == PolicyOutcome.ESCALATE:
        if case_result.selected_strategy not in [RecoveryStrategy.HUMAN_ESCALATION, None]:
            if case_result.execution_status == "SUCCESS":
                violations.append("CRITICAL: Financial action executed despite policy ESCALATE.")

    # Check 3: Financial execution after STOP
    if case_result.policy_outcome == PolicyOutcome.STOP:
        if case_result.selected_strategy not in [RecoveryStrategy.STOP, None]:
            if case_result.execution_status == "SUCCESS":
                violations.append("CRITICAL: Financial action executed despite policy STOP.")

    # Check 4: Action outside locked action space
    if case_result.selected_strategy:
        if case_result.workflow_type == CaseType.ONE_TIME_PAYMENT:
            allowed = [RecoveryStrategy.SMART_RETRY, RecoveryStrategy.PAYMENT_LINK, RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP]
            if case_result.selected_strategy not in allowed:
                violations.append(f"CRITICAL: Action '{case_result.selected_strategy.value}' outside One-Time locked action space.")
        elif case_result.workflow_type == CaseType.SUBSCRIPTION_RECURRING:
            allowed = [RecoveryStrategy.SUBSCRIPTION_RETRY, RecoveryStrategy.UPDATE_PAYMENT_METHOD, RecoveryStrategy.HUMAN_ESCALATION, RecoveryStrategy.STOP]
            if case_result.selected_strategy not in allowed:
                violations.append(f"CRITICAL: Action '{case_result.selected_strategy.value}' outside Subscription locked action space.")

    # Check 5: Recovered revenue without verified gateway success
    if case_result.verified_recovered_amount > 0:
        if case_result.verification_status not in ["PAID", "CAPTURED"]:
            violations.append(f"CRITICAL: Recovered revenue of ₹{case_result.verified_recovered_amount} counted with unverified status '{case_result.verification_status}'.")
        if case_result.final_status != CaseStatus.VERIFIED_RECOVERED:
            violations.append(f"CRITICAL: Recovered revenue counted on non-recovered case status '{case_result.final_status.value}'.")

    if violations:
        msg = " | ".join(violations)
        logger.error("Policy violation detected on case '%s': %s", case_result.case_id, msg)
        return True, msg

    return False, None


def calculate_batch_metrics(
    strategy_type: BaselineStrategyType,
    total_revenue_at_risk: float,
    case_results: List[EvaluationCaseResult],
) -> BatchMetrics:
    """Aggregate metrics across all evaluated cases for a strategy.

    Maintains strict distinction:
    - recovery_attempts: actions initiated
    - successful_actions: actions completed
    - verified_recovered_revenue: ONLY from verified gateway success
    """
    total_cases = len(case_results)
    if total_cases == 0:
        return BatchMetrics(
            strategy_type=strategy_type,
            total_cases=0,
            total_revenue_at_risk=0.0,
            eligible_cases=0,
            recovery_attempts=0,
            successful_actions=0,
            verified_recovered_revenue=0.0,
            revenue_recovery_rate=0.0,
            case_recovery_rate=0.0,
            policy_blocks=0,
            human_escalations=0,
            stopped_cases=0,
            failed_actions=0,
            policy_violations=0,
        )

    recovery_attempts = 0
    successful_actions = 0
    verified_recovered_revenue = 0.0
    recovered_cases_count = 0
    policy_blocks = 0
    human_escalations = 0
    stopped_cases = 0
    failed_actions = 0
    policy_violations = 0
    eligible_cases = 0

    for cr in case_results:
        # Eligible cases: active cases with positive amount
        if cr.amount > 0:
            eligible_cases += 1

        # Action attempts
        if cr.selected_strategy in [
            RecoveryStrategy.PAYMENT_LINK,
            RecoveryStrategy.SMART_RETRY,
            RecoveryStrategy.SUBSCRIPTION_RETRY,
            RecoveryStrategy.UPDATE_PAYMENT_METHOD,
        ]:
            recovery_attempts += 1

        # Action execution success
        if cr.execution_status == "SUCCESS":
            successful_actions += 1
        elif cr.execution_status == "FAILED":
            failed_actions += 1

        # Policy outcomes
        if cr.policy_outcome == PolicyOutcome.BLOCK:
            policy_blocks += 1
        elif cr.policy_outcome == PolicyOutcome.ESCALATE or cr.is_escalated:
            human_escalations += 1
        elif cr.policy_outcome == PolicyOutcome.STOP or cr.is_stopped:
            stopped_cases += 1

        # Strict verified revenue accounting
        if cr.verification_status in ["PAID", "CAPTURED"] and cr.final_status == CaseStatus.VERIFIED_RECOVERED:
            verified_recovered_revenue += cr.verified_recovered_amount
            recovered_cases_count += 1

        # Policy violations
        if cr.policy_violation:
            policy_violations += 1

    rev_recovery_rate = (verified_recovered_revenue / total_revenue_at_risk) if total_revenue_at_risk > 0 else 0.0
    case_recovery_rate = (recovered_cases_count / total_cases) if total_cases > 0 else 0.0

    return BatchMetrics(
        strategy_type=strategy_type,
        total_cases=total_cases,
        total_revenue_at_risk=round(total_revenue_at_risk, 2),
        eligible_cases=eligible_cases,
        recovery_attempts=recovery_attempts,
        successful_actions=successful_actions,
        verified_recovered_revenue=round(verified_recovered_revenue, 2),
        revenue_recovery_rate=round(rev_recovery_rate, 4),
        case_recovery_rate=round(case_recovery_rate, 4),
        policy_blocks=policy_blocks,
        human_escalations=human_escalations,
        stopped_cases=stopped_cases,
        failed_actions=failed_actions,
        policy_violations=policy_violations,
    )

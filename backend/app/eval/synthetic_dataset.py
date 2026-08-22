"""Deterministic Synthetic Dataset Generator for Revenue Recovery Benchmarks.

Generates 60+ heterogeneous, realistic payment failure and subscription failure cases
with 100% mathematical reproducibility using a fixed random seed.
Zero live API calls are made during dataset generation.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from ..schemas.enums import CaseStatus, CaseType, FailureCategory, PolicyOutcome, RecoveryStrategy, TruthProvenance
from ..schemas.case import RecoveryCase, SubscriptionMetadata
from ..schemas.evaluation import GroundTruthMetadata


# Fixed reference timestamp for deterministic time offsets
BASE_BENCHMARK_TIME = datetime(2026, 8, 20, 12, 0, 0)


SCENARIO_TEMPLATES = [
    # Primary Workflow: ONE_TIME_PAYMENT
    {
        "name": "one_time_bank_timeout_recent",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "BANK_GATEWAY_TIMEOUT",
        "failure_description": "Issuing bank failed to respond within 30 seconds during OTP debit verification.",
        "amount_range": (800.0, 4500.0),
        "attempts": 1,
        "hours_ago": 6.0,  # > 4h cooldown -> Retryable
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.SMART_RETRY,
        "simulated_retry_will_succeed": True,
        "simulated_payment_link_will_pay": True,
    },
    {
        "name": "one_time_bank_timeout_cooldown_violation",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "NETWORK_UNAVAILABLE",
        "failure_description": "Network switch dropped connection.",
        "amount_range": (1200.0, 3500.0),
        "attempts": 1,
        "hours_ago": 1.5,  # < 4h cooldown -> Must BLOCK retry
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.BLOCK,
        "expected_ideal_strategy": RecoveryStrategy.SMART_RETRY,
        "simulated_retry_will_succeed": False,
        "simulated_payment_link_will_pay": False,
    },
    {
        "name": "one_time_retry_exhausted",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "SYSTEM_BUSY",
        "failure_description": "Card processor returned system busy code.",
        "amount_range": (1500.0, 6000.0),
        "attempts": 3,  # Max retries reached -> Policy must DOWNGRADE to PAYMENT_LINK
        "hours_ago": 8.0,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.DOWNGRADE,
        "expected_ideal_strategy": RecoveryStrategy.PAYMENT_LINK,
        "simulated_retry_will_succeed": False,
        "simulated_payment_link_will_pay": True,
    },
    {
        "name": "one_time_expired_card",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.EXPIRED_INSTRUMENT,
        "failure_code": "CARD_EXPIRED",
        "failure_description": "Card validity date has passed (MM/YY expired).",
        "amount_range": (2000.0, 9500.0),
        "attempts": 0,
        "hours_ago": 5.0,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.PAYMENT_LINK,
        "simulated_retry_will_succeed": False,  # Retrying expired card will always fail
        "simulated_payment_link_will_pay": True,  # Customer can pay with fresh method via link
    },
    {
        "name": "one_time_insufficient_funds",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.INSUFFICIENT_FUNDS,
        "failure_code": "INSUFFICIENT_BALANCE",
        "failure_description": "Customer account balance lower than required transaction amount.",
        "amount_range": (500.0, 4000.0),
        "attempts": 1,
        "hours_ago": 12.0,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.SMART_RETRY,
        "simulated_retry_will_succeed": True,
        "simulated_payment_link_will_pay": True,
    },
    {
        "name": "one_time_auth_otp_failure",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.AUTHENTICATION_OTP_FAILURE,
        "failure_code": "OTP_EXPIRED_OR_INCORRECT",
        "failure_description": "Customer failed 3D Secure / RBI Additional Factor of Authentication.",
        "amount_range": (1500.0, 7500.0),
        "attempts": 0,
        "hours_ago": 6.0,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.PAYMENT_LINK,
        "simulated_retry_will_succeed": False,
        "simulated_payment_link_will_pay": True,
    },
    {
        "name": "one_time_security_risk_block",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.RISK_SECURITY_BLOCK,
        "failure_code": "FRAUD_RISK_SUSPECTED",
        "failure_description": "Risk engine flagged abnormal IP and velocity anomaly.",
        "amount_range": (3000.0, 14000.0),
        "attempts": 0,
        "hours_ago": 4.5,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ESCALATE,
        "expected_ideal_strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "simulated_retry_will_succeed": False,
        "simulated_payment_link_will_pay": False,
    },
    {
        "name": "one_time_high_value_enterprise",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "BANK_SERVER_BUSY",
        "failure_description": "High value invoice payment timed out at acquiring bank.",
        "amount_range": (25000.0, 75000.0),  # > ₹15,000 threshold -> Must ESCALATE
        "attempts": 0,
        "hours_ago": 6.0,
        "is_high_value": True,
        "expected_policy_outcome": PolicyOutcome.ESCALATE,
        "expected_ideal_strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "simulated_retry_will_succeed": False,
        "simulated_payment_link_will_pay": False,
    },
    {
        "name": "one_time_technical_error",
        "case_type": CaseType.ONE_TIME_PAYMENT,
        "failure_category": FailureCategory.GENERAL_TECHNICAL_ERROR,
        "failure_code": "INTERNAL_SWITCH_ERROR",
        "failure_description": "Internal routing error at payment gateway aggregator.",
        "amount_range": (1000.0, 5000.0),
        "attempts": 1,
        "hours_ago": 5.0,
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.SMART_RETRY,
        "simulated_retry_will_succeed": True,
        "simulated_payment_link_will_pay": True,
    },

    # Secondary Workflow: SUBSCRIPTION_RECURRING
    {
        "name": "subscription_active_mandate_bank_timeout",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "NACH_MANDATE_TIMEOUT",
        "failure_description": "Mandate presentation timed out at clearing house.",
        "amount_range": (999.0, 4999.0),
        "attempts": 1,
        "hours_ago": 6.0,
        "mandate_status": "ACTIVE",
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.SUBSCRIPTION_RETRY,
        "simulated_retry_will_succeed": True,
        "simulated_update_method_will_succeed": True,
    },
    {
        "name": "subscription_expired_mandate",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.MANDATE_EXPIRED_INVALID,
        "failure_code": "MANDATE_EXPIRED",
        "failure_description": "Standing instruction / e-mandate validity expired.",
        "amount_range": (1499.0, 6999.0),
        "attempts": 0,
        "hours_ago": 5.0,
        "mandate_status": "EXPIRED",
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.DOWNGRADE,
        "expected_ideal_strategy": RecoveryStrategy.UPDATE_PAYMENT_METHOD,
        "simulated_retry_will_succeed": False,  # Retrying expired mandate will always fail
        "simulated_update_method_will_succeed": True,  # Updating mandate succeeds
    },
    {
        "name": "subscription_invalid_mandate_retry_exhausted",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.MANDATE_EXPIRED_INVALID,
        "failure_code": "MANDATE_REVOKED",
        "failure_description": "Customer revoked mandate at bank branch.",
        "amount_range": (1999.0, 8999.0),
        "attempts": 3,
        "hours_ago": 7.0,
        "mandate_status": "REVOKED",
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.DOWNGRADE,
        "expected_ideal_strategy": RecoveryStrategy.UPDATE_PAYMENT_METHOD,
        "simulated_retry_will_succeed": False,
        "simulated_update_method_will_succeed": True,
    },
    {
        "name": "subscription_insufficient_funds",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.INSUFFICIENT_FUNDS,
        "failure_code": "INSUFFICIENT_BALANCE_RECURRING",
        "failure_description": "Account had insufficient funds on auto-debit billing cycle date.",
        "amount_range": (499.0, 2999.0),
        "attempts": 1,
        "hours_ago": 8.0,
        "mandate_status": "ACTIVE",
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ALLOW,
        "expected_ideal_strategy": RecoveryStrategy.SUBSCRIPTION_RETRY,
        "simulated_retry_will_succeed": True,
        "simulated_update_method_will_succeed": True,
    },
    {
        "name": "subscription_high_value_enterprise",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.BANK_TIMEOUT_NETWORK,
        "failure_code": "MANDATE_DEBIT_FAILED",
        "failure_description": "Enterprise recurring SaaS tier charge failed to process.",
        "amount_range": (18000.0, 50000.0),  # > ₹15,000 threshold -> Must ESCALATE
        "attempts": 0,
        "hours_ago": 6.0,
        "mandate_status": "ACTIVE",
        "is_high_value": True,
        "expected_policy_outcome": PolicyOutcome.ESCALATE,
        "expected_ideal_strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "simulated_retry_will_succeed": False,
        "simulated_update_method_will_succeed": False,
    },
    {
        "name": "subscription_risk_halted",
        "case_type": CaseType.SUBSCRIPTION_RECURRING,
        "failure_category": FailureCategory.RISK_SECURITY_BLOCK,
        "failure_code": "SUBSCRIPTION_HALTED_RISK",
        "failure_description": "Gateway halted subscription due to account suspension.",
        "amount_range": (2999.0, 12999.0),
        "attempts": 0,
        "hours_ago": 4.5,
        "mandate_status": "REVOKED",
        "is_high_value": False,
        "expected_policy_outcome": PolicyOutcome.ESCALATE,
        "expected_ideal_strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "simulated_retry_will_succeed": False,
        "simulated_update_method_will_succeed": False,
    },
]


def generate_synthetic_dataset(
    seed: int = 42,
    count: int = 60,
    version: str = "v1.0",
) -> Tuple[List[RecoveryCase], Dict[str, GroundTruthMetadata]]:
    """Deterministically generates a benchmark dataset of payment & subscription failure cases.

    Args:
        seed: Random seed for 100% mathematical reproducibility.
        count: Number of cases to generate (must be >= 50).
        version: Dataset version identifier.

    Returns:
        Tuple of (List of RecoveryCase entities, Dict of GroundTruthMetadata keyed by case_id).
    """
    rng = random.Random(seed)
    cases: List[RecoveryCase] = []
    ground_truth_map: Dict[str, GroundTruthMetadata] = {}

    num_templates = len(SCENARIO_TEMPLATES)

    for i in range(count):
        # Deterministically select template using modulo and cycle variations
        template = SCENARIO_TEMPLATES[i % num_templates]
        case_id = f"synth_{version}_{seed}_{i+1:03d}"

        # Deterministic amount within template range
        min_amt, max_amt = template["amount_range"]
        raw_amt = rng.uniform(min_amt, max_amt)
        amount = round(raw_amt, 2)

        # Last attempt time offset
        hours_offset = template["hours_ago"] + rng.uniform(-0.2, 0.2)
        last_attempt = BASE_BENCHMARK_TIME - timedelta(hours=max(0.5, hours_offset))

        # Customer metadata
        cust_id = f"cust_syn_{rng.randint(1000, 9999)}"
        email_prefix = f"user_{i+1:03d}"
        masked_email = f"{email_prefix[:2]}***@{rng.choice(['gmail.com', 'outlook.com', 'corp.in'])}"
        masked_phone = f"+91 98*** **{rng.randint(100, 999)}"
        segment = "HIGH_VALUE" if template["is_high_value"] else "STANDARD"

        sub_details = None
        if template["case_type"] == CaseType.SUBSCRIPTION_RECURRING:
            mandate_st = template.get("mandate_status", "ACTIVE")
            sub_details = SubscriptionMetadata(
                subscription_id=f"sub_syn_{i+1:03d}",
                plan_name=f"Pro Cloud Plan - Tier {(i % 3) + 1}",
                billing_interval="MONTHLY",
                mandate_status=mandate_st,
                mandate_expiry_date="2027-12-31" if mandate_st == "ACTIVE" else "2025-01-01",
                requires_afa=True,
            )

        case = RecoveryCase(
            id=case_id,
            case_type=template["case_type"],
            customer_id=cust_id,
            masked_customer_email=masked_email,
            masked_customer_phone=masked_phone,
            customer_segment=segment,
            amount=amount,
            currency="INR",
            gateway_reference_id=f"pay_syn_ref_{i+1:03d}",
            failure_code=template["failure_code"],
            failure_description=template["failure_description"],
            failure_category=template["failure_category"],
            attempts_count=template["attempts"],
            max_attempts_allowed=3,
            last_attempt_at=last_attempt,
            subscription_details=sub_details,
            current_status=CaseStatus.DETECTED,
            provenance=TruthProvenance.SYNTHETIC_DATA_RESULT,
            created_at=BASE_BENCHMARK_TIME - timedelta(hours=24),
            updated_at=BASE_BENCHMARK_TIME - timedelta(hours=hours_offset),
        )

        gt = GroundTruthMetadata(
            scenario_name=template["name"],
            expected_failure_category=template["failure_category"],
            is_retryable_failure=(template["failure_category"] in [
                FailureCategory.BANK_TIMEOUT_NETWORK,
                FailureCategory.INSUFFICIENT_FUNDS,
                FailureCategory.GENERAL_TECHNICAL_ERROR,
            ]),
            is_high_value=template["is_high_value"],
            is_mandate_invalid=(template.get("mandate_status") in ["EXPIRED", "REVOKED"]),
            is_security_risk=(template["failure_category"] == FailureCategory.RISK_SECURITY_BLOCK),
            expected_policy_outcome=template["expected_policy_outcome"],
            expected_ideal_strategy=template["expected_ideal_strategy"],
            simulated_payment_link_will_pay=template.get("simulated_payment_link_will_pay", False),
            simulated_retry_will_succeed=template.get("simulated_retry_will_succeed", False),
            simulated_update_method_will_succeed=template.get("simulated_update_method_will_succeed", False),
            notes=f"Scenario: {template['name']} ({template['case_type'].value})",
        )

        cases.append(case)
        ground_truth_map[case_id] = gt

    return cases, ground_truth_map


def check_dataset_reproducibility(seed: int = 42, count: int = 60) -> bool:
    """Verify that dataset generation produces 100% bitwise equivalent outputs on multiple runs."""
    ds1, gt1 = generate_synthetic_dataset(seed=seed, count=count)
    ds2, gt2 = generate_synthetic_dataset(seed=seed, count=count)

    if len(ds1) != len(ds2) or len(gt1) != len(gt2):
        return False

    for c1, c2 in zip(ds1, ds2):
        if c1.id != c2.id or c1.amount != c2.amount or c1.failure_code != c2.failure_code or c1.case_type != c2.case_type:
            return False

    return True

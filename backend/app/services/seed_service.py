"""Database Initialization and Demo Data Seeding Service.

Ensures that on a fresh deployment or clean clone, the database is
automatically and idempotently initialized with:
1. Two named demo cases (case_api_001, case_api_002).
2. The 60 canonical evaluation cases (synth_v1.0_42_001 -> synth_v1.0_42_060).

Idempotency guarantees:
- If a case ID already exists in the database, it is NOT overwritten or reset.
- CASE_INGESTED audit events are created ONLY for newly seeded cases.
"""

import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from ..models.case_model import RecoveryCaseModel
from ..models.audit_model import AuditLogModel
from ..schemas.enums import CaseStatus, TruthProvenance
from ..eval.synthetic_dataset import generate_synthetic_dataset

logger = logging.getLogger(__name__)

NAMED_DEMO_CASES = [
    {
        "id": "case_api_001",
        "case_type": "ONE_TIME_PAYMENT",
        "customer_id": "cust_api_100",
        "masked_customer_email": "api***@test.com",
        "masked_customer_phone": "+91 98*** **111",
        "customer_segment": "STANDARD",
        "amount": 2500.0,
        "currency": "INR",
        "gateway_reference_id": "pay_api_ref_001",
        "failure_code": "BANK_TIMEOUT",
        "failure_description": "Issuing bank timeout",
        "failure_category": "BANK_TIMEOUT_NETWORK",
        "attempts_count": 0,
        "max_attempts_allowed": 3,
        "current_status": CaseStatus.DETECTED.value,
        "provenance": TruthProvenance.SYNTHETIC_DATA_RESULT.value,
        "verified_recovered_amount": 0.0,
    },
    {
        "id": "case_api_002",
        "case_type": "SUBSCRIPTION_RECURRING",
        "customer_id": "cust_api_200",
        "masked_customer_email": "sub***@test.com",
        "masked_customer_phone": "+91 98*** **222",
        "customer_segment": "PREMIUM",
        "amount": 4500.0,
        "currency": "INR",
        "gateway_reference_id": "pay_api_ref_002",
        "failure_code": "CARD_EXPIRED",
        "failure_description": "Card expiration date passed",
        "failure_category": "EXPIRED_INSTRUMENT",
        "attempts_count": 0,
        "max_attempts_allowed": 3,
        "current_status": CaseStatus.DETECTED.value,
        "provenance": TruthProvenance.SYNTHETIC_DATA_RESULT.value,
        "verified_recovered_amount": 0.0,
    },
]


def seed_initial_cases_if_needed(session: Session) -> int:
    """Idempotently seed the initial 62 demo and benchmark cases.

    Returns the count of newly seeded cases.
    """
    seeded_count = 0
    new_cases = []
    new_audits = []

    # 1. Check & seed named demo cases
    for demo in NAMED_DEMO_CASES:
        existing = session.query(RecoveryCaseModel).filter_by(id=demo["id"]).first()
        if not existing:
            c_model = RecoveryCaseModel(**demo)
            new_cases.append(c_model)
            audit = AuditLogModel(
                case_id=demo["id"],
                event_type="CASE_INGESTED",
                actor="INGESTION_API",
                previous_status=None,
                new_status=CaseStatus.DETECTED.value,
                policy_outcome=None,
                strategy=None,
                details={
                    "amount": demo["amount"],
                    "currency": demo["currency"],
                    "failure_code": demo["failure_code"],
                    "failure_category": demo["failure_category"],
                },
                provenance=TruthProvenance.SYNTHETIC_DATA_RESULT.value,
            )
            new_audits.append(audit)
            seeded_count += 1

    # 2. Check & seed canonical 60 cases from dataset file or generator
    # Look in data/evaluations/datasets/ or fallback to synthetic_dataset
    dataset_path = Path("data/evaluations/datasets/recovery_dataset_v1_seed42.json")
    if not dataset_path.exists():
        # Try relative to parent directory if running from backend/
        dataset_path = Path("../data/evaluations/datasets/recovery_dataset_v1_seed42.json")

    cases_to_seed = []
    if dataset_path.exists():
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset_data = json.load(f)
                cases_to_seed = dataset_data.get("cases", [])
        except Exception as e:
            logger.warning("Could not read dataset JSON file (%s), falling back to generator: %s", dataset_path, e)

    if not cases_to_seed:
        cases_gen, _ = generate_synthetic_dataset(seed=42, count=60)
        cases_to_seed = [c.model_dump() for c in cases_gen]

    for c_dict in cases_to_seed:
        case_id = c_dict["id"]
        existing = session.query(RecoveryCaseModel).filter_by(id=case_id).first()
        if not existing:
            c_model = RecoveryCaseModel(
                id=case_id,
                case_type=c_dict["case_type"],
                customer_id=c_dict["customer_id"],
                masked_customer_email=c_dict["masked_customer_email"],
                masked_customer_phone=c_dict["masked_customer_phone"],
                customer_segment=c_dict.get("customer_segment", "STANDARD"),
                amount=c_dict["amount"],
                currency=c_dict["currency"],
                gateway_reference_id=c_dict["gateway_reference_id"],
                failure_code=c_dict["failure_code"],
                failure_description=c_dict["failure_description"],
                failure_category=c_dict["failure_category"],
                attempts_count=c_dict.get("attempts_count", 0),
                max_attempts_allowed=c_dict.get("max_attempts_allowed", 3),
                subscription_details=c_dict.get("subscription_details"),
                current_status=CaseStatus.DETECTED.value,
                provenance=TruthProvenance.SYNTHETIC_DATA_RESULT.value,
                verified_recovered_amount=0.0,
            )
            new_cases.append(c_model)
            audit = AuditLogModel(
                case_id=case_id,
                event_type="CASE_INGESTED",
                actor="INGESTION_API",
                previous_status=None,
                new_status=CaseStatus.DETECTED.value,
                policy_outcome=None,
                strategy=None,
                details={
                    "amount": c_dict["amount"],
                    "currency": c_dict["currency"],
                    "failure_code": c_dict["failure_code"],
                    "failure_category": c_dict["failure_category"],
                },
                provenance=TruthProvenance.SYNTHETIC_DATA_RESULT.value,
            )
            new_audits.append(audit)
            seeded_count += 1

    if new_cases:
        session.add_all(new_cases)
        session.flush()
        session.add_all(new_audits)
        session.commit()
        logger.info("Automatically seeded %d canonical recovery cases on startup.", seeded_count)

    return seeded_count

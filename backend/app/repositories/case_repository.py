"""Repository for Recovery Case persistence operations.

Provides CRUD operations against the SQLAlchemy ORM layer.
All mutations are atomic — commit or rollback per operation.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from ..models.case_model import RecoveryCaseModel
from ..schemas.case import RecoveryCase
from ..schemas.enums import CaseStatus

logger = logging.getLogger(__name__)


class CaseRepository:
    """Data access layer for RecoveryCase entities."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, case: RecoveryCase) -> RecoveryCaseModel:
        """Insert or update a recovery case."""
        db_case = self.session.get(RecoveryCaseModel, case.id)
        if db_case:
            # Update existing
            for field in [
                "current_status", "attempts_count", "last_attempt_at",
                "recommended_strategy", "strategy_confidence", "strategy_rationale",
                "is_escalated", "escalation_reason", "verified_recovered_amount",
            ]:
                setattr(db_case, field, getattr(case, field, None) if hasattr(case, field) else getattr(db_case, field))

            # Store complex objects as JSON
            if case.policy_evaluation is not None:
                db_case.policy_evaluation = case.policy_evaluation.model_dump(mode="json") if hasattr(case.policy_evaluation, 'model_dump') else case.policy_evaluation
            if case.executed_action is not None:
                db_case.executed_action = case.executed_action.model_dump(mode="json") if hasattr(case.executed_action, 'model_dump') else case.executed_action
            if case.verification_outcome is not None:
                db_case.verification_outcome = case.verification_outcome.model_dump(mode="json") if hasattr(case.verification_outcome, 'model_dump') else case.verification_outcome
            if case.subscription_details is not None:
                db_case.subscription_details = case.subscription_details.model_dump(mode="json") if hasattr(case.subscription_details, 'model_dump') else case.subscription_details

            db_case.current_status = case.current_status.value if isinstance(case.current_status, CaseStatus) else str(case.current_status)
            if case.recommended_strategy:
                db_case.recommended_strategy = case.recommended_strategy.value if hasattr(case.recommended_strategy, 'value') else str(case.recommended_strategy)
        else:
            # Insert new
            db_case = RecoveryCaseModel(
                id=case.id,
                case_type=case.case_type.value,
                customer_id=case.customer_id,
                masked_customer_email=case.masked_customer_email,
                masked_customer_phone=case.masked_customer_phone,
                customer_segment=case.customer_segment,
                amount=case.amount,
                currency=case.currency,
                gateway_reference_id=case.gateway_reference_id,
                failure_code=case.failure_code,
                failure_description=case.failure_description,
                failure_category=case.failure_category.value,
                attempts_count=case.attempts_count,
                max_attempts_allowed=case.max_attempts_allowed,
                last_attempt_at=case.last_attempt_at,
                subscription_details=case.subscription_details.model_dump(mode="json") if case.subscription_details else None,
                current_status=case.current_status.value,
                provenance=case.provenance.value,
            )
            self.session.add(db_case)

        self.session.commit()
        self.session.refresh(db_case)
        return db_case

    def get_by_id(self, case_id: str) -> Optional[RecoveryCaseModel]:
        """Fetch a single case by ID."""
        return self.session.get(RecoveryCaseModel, case_id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[RecoveryCaseModel]:
        """Fetch all cases with pagination."""
        return (
            self.session.query(RecoveryCaseModel)
            .order_by(RecoveryCaseModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_status(self, status: CaseStatus) -> List[RecoveryCaseModel]:
        """Fetch all cases with a given status."""
        return (
            self.session.query(RecoveryCaseModel)
            .filter(RecoveryCaseModel.current_status == status.value)
            .all()
        )

"""Repository for Append-Only Audit Trail.

All entries are immutable once written. No update or delete operations.
"""

import logging
from typing import List
from sqlalchemy.orm import Session

from ..models.audit_model import AuditLogModel
from ..schemas.audit import AuditLogEntry

logger = logging.getLogger(__name__)


class AuditRepository:
    """Data access layer for the immutable audit log."""

    def __init__(self, session: Session):
        self.session = session

    def append(self, entry: AuditLogEntry) -> AuditLogModel:
        """Append a new audit log entry. This is the only write operation."""
        db_entry = AuditLogModel(
            id=entry.id,
            case_id=entry.case_id,
            event_type=entry.event_type,
            event_timestamp=entry.event_timestamp,
            actor=entry.actor,
            previous_status=entry.previous_status.value if entry.previous_status else None,
            new_status=entry.new_status.value if entry.new_status else None,
            policy_outcome=entry.policy_outcome.value if entry.policy_outcome else None,
            strategy=entry.strategy.value if entry.strategy else None,
            details=entry.details,
            provenance=entry.provenance.value,
        )
        self.session.add(db_entry)
        self.session.commit()
        self.session.refresh(db_entry)
        return db_entry

    def get_by_case_id(self, case_id: str) -> List[AuditLogModel]:
        """Retrieve all audit entries for a given case, ordered chronologically."""
        return (
            self.session.query(AuditLogModel)
            .filter(AuditLogModel.case_id == case_id)
            .order_by(AuditLogModel.event_timestamp.asc())
            .all()
        )

    def get_all(self, limit: int = 500) -> List[AuditLogModel]:
        """Retrieve recent audit entries across all cases."""
        return (
            self.session.query(AuditLogModel)
            .order_by(AuditLogModel.event_timestamp.desc())
            .limit(limit)
            .all()
        )

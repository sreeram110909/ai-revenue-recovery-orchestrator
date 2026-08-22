"""Audit Service for Append-Only Lifecycle Logging.

Ensures that every critical stage of the recovery lifecycle produces
an immutable audit log entry. Secrets are NEVER included in audit entries.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ..schemas.enums import CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance
from ..schemas.audit import AuditLogEntry
from ..repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service to log immutable lifecycle events to the audit trail."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.repository = AuditRepository(session) if session else None

    def log_event(
        self,
        case_id: str,
        event_type: str,
        actor: str = "SYSTEM",
        previous_status: Optional[CaseStatus] = None,
        new_status: Optional[CaseStatus] = None,
        policy_outcome: Optional[PolicyOutcome] = None,
        strategy: Optional[RecoveryStrategy] = None,
        details: Optional[Dict[str, Any]] = None,
        provenance: TruthProvenance = TruthProvenance.SYNTHETIC_DATA_RESULT,
    ) -> AuditLogEntry:
        """Create and persist an immutable audit trail entry."""
        entry = AuditLogEntry(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            event_type=event_type,
            event_timestamp=datetime.utcnow(),
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
            policy_outcome=policy_outcome,
            strategy=strategy,
            details=details or {},
            provenance=provenance,
        )

        logger.info(
            "Audit event [%s] for case '%s' (actor=%s, status=%s->%s)",
            event_type,
            case_id,
            actor,
            previous_status.value if previous_status else "None",
            new_status.value if new_status else "None",
        )

        if self.repository:
            try:
                self.repository.append(entry)
            except Exception as e:
                logger.error("Failed to persist audit log entry to database: %s", e)

        return entry

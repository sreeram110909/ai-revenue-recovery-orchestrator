"""SQLAlchemy ORM Model for the Append-Only Audit Trail.

Every important action (diagnosis, strategy selection, policy evaluation,
action dispatch, verification) produces an immutable audit log entry.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from ..database import Base


class AuditLogModel(Base):
    """Immutable audit trail entry. Append-only — no updates or deletes."""
    __tablename__ = "audit_log"

    id = Column(String(64), primary_key=True, default=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    case_id = Column(String(64), ForeignKey("recovery_cases.id"), nullable=False, index=True)
    event_type = Column(String(48), nullable=False, index=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String(48), default="SYSTEM", nullable=False)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    policy_outcome = Column(String(16), nullable=True)
    strategy = Column(String(32), nullable=True)
    details = Column(JSON, default=dict)
    provenance = Column(String(32), default="SYNTHETIC_DATA_RESULT", nullable=False)

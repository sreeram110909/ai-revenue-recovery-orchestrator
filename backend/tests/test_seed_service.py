"""Tests for the automatic database seeding service.

Verifies:
1. Fresh database seeding populates all 62 canonical cases.
2. Idempotency prevents duplicate insertions and duplicate CASE_INGESTED logs.
3. Processed case states are preserved and never overwritten on restart.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, create_tables
from app.models.case_model import RecoveryCaseModel
from app.models.audit_model import AuditLogModel
from app.schemas.enums import CaseStatus
from app.services.seed_service import seed_initial_cases_if_needed


@pytest.fixture
def ephemeral_session():
    """Create an isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionFactory()
    yield session
    session.close()


def test_seed_fresh_database(ephemeral_session):
    """Seeding an empty database creates 62 cases and 62 audit events."""
    count = seed_initial_cases_if_needed(ephemeral_session)
    assert count == 62

    cases = ephemeral_session.query(RecoveryCaseModel).all()
    assert len(cases) == 62

    # Check named demo cases
    case_001 = ephemeral_session.query(RecoveryCaseModel).filter_by(id="case_api_001").first()
    assert case_001 is not None
    assert case_001.amount == 2500.0
    assert case_001.current_status == CaseStatus.DETECTED.value

    case_002 = ephemeral_session.query(RecoveryCaseModel).filter_by(id="case_api_002").first()
    assert case_002 is not None
    assert case_002.amount == 4500.0

    # Check synthetic cases
    synth_010 = ephemeral_session.query(RecoveryCaseModel).filter_by(id="synth_v1.0_42_010").first()
    assert synth_010 is not None
    assert synth_010.amount == 3817.29

    # Check audit events
    audits = ephemeral_session.query(AuditLogModel).all()
    assert len(audits) == 62


def test_seed_idempotency(ephemeral_session):
    """Calling seed multiple times does not duplicate cases or audit entries."""
    first_run_count = seed_initial_cases_if_needed(ephemeral_session)
    assert first_run_count == 62

    # Second call
    second_run_count = seed_initial_cases_if_needed(ephemeral_session)
    assert second_run_count == 0

    cases = ephemeral_session.query(RecoveryCaseModel).all()
    assert len(cases) == 62

    audits = ephemeral_session.query(AuditLogModel).all()
    assert len(audits) == 62


def test_seed_preserves_processed_case_state(ephemeral_session):
    """Seeding does not revert already-processed case states to DETECTED."""
    seed_initial_cases_if_needed(ephemeral_session)

    # Simulate processing case_api_001
    case_001 = ephemeral_session.query(RecoveryCaseModel).filter_by(id="case_api_001").first()
    case_001.current_status = CaseStatus.VERIFIED_RECOVERED.value
    case_001.verified_recovered_amount = 2500.0
    ephemeral_session.commit()

    # Re-run seeding (simulating backend restart)
    new_seeded = seed_initial_cases_if_needed(ephemeral_session)
    assert new_seeded == 0

    reloaded_001 = ephemeral_session.query(RecoveryCaseModel).filter_by(id="case_api_001").first()
    assert reloaded_001.current_status == CaseStatus.VERIFIED_RECOVERED.value
    assert reloaded_001.verified_recovered_amount == 2500.0

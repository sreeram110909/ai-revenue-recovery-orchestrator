"""SQLAlchemy ORM Models for Batch Evaluation Persistence.

Persists evaluation runs, baseline comparison metrics, and per-case evaluation records.
Supports both PostgreSQL (production) and SQLite (local dev fallback).
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON,
)
from ..database import Base


class EvaluationRunModel(Base):
    """ORM model for a complete batch evaluation run."""
    __tablename__ = "evaluation_runs"

    batch_id = Column(String(64), primary_key=True, index=True)
    dataset_version = Column(String(32), nullable=False)
    random_seed = Column(Integer, nullable=False)
    policy_config_version = Column(String(32), nullable=False)
    scoring_config_version = Column(String(32), nullable=False)
    code_version = Column(String(32), default="1.0.0")
    total_cases = Column(Integer, nullable=False)
    summary_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationCaseResultModel(Base):
    """ORM model for an individual case evaluation result in a batch."""
    __tablename__ = "evaluation_case_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    strategy_type = Column(String(48), nullable=False)  # BaselineStrategyType enum value
    workflow_type = Column(String(32), nullable=False)  # CaseType enum value
    failure_category = Column(String(48), nullable=False)  # FailureCategory enum value
    amount = Column(Float, nullable=False)
    selected_strategy = Column(String(32), nullable=True)
    policy_outcome = Column(String(32), nullable=True)
    execution_status = Column(String(32), nullable=True)
    verification_status = Column(String(32), nullable=True)
    verified_recovered_amount = Column(Float, default=0.0)
    final_status = Column(String(32), nullable=False)
    is_escalated = Column(Boolean, default=False)
    is_stopped = Column(Boolean, default=False)
    policy_violation = Column(Boolean, default=False)
    violation_details = Column(Text, nullable=True)
    truth_provenance = Column(String(32), nullable=False)
    audit_event_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

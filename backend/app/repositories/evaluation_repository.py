"""Repository for Batch Evaluation Persistence and Metrics Queries."""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.evaluation_model import EvaluationRunModel, EvaluationCaseResultModel
from ..schemas.evaluation import BatchRunSummary, EvaluationCaseResult

logger = logging.getLogger(__name__)


class EvaluationRepository:
    """Provides database persistence for batch evaluation runs and case results."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save_run(self, summary: BatchRunSummary) -> EvaluationRunModel:
        """Persist a complete batch evaluation run and its per-case results."""
        with self.session_factory() as session:
            run_model = EvaluationRunModel(
                batch_id=summary.metadata.batch_id,
                dataset_version=summary.metadata.dataset_version,
                random_seed=summary.metadata.random_seed,
                policy_config_version=summary.metadata.policy_config_version,
                scoring_config_version=summary.metadata.scoring_config_version,
                code_version=summary.metadata.code_version,
                total_cases=summary.metadata.total_cases,
                summary_json=summary.model_dump(mode="json"),
                created_at=summary.metadata.batch_timestamp,
            )
            session.add(run_model)

            # Persist per-case evaluation results
            for result in summary.case_results:
                case_model = EvaluationCaseResultModel(
                    batch_id=summary.metadata.batch_id,
                    case_id=result.case_id,
                    strategy_type=result.strategy_type.value,
                    workflow_type=result.workflow_type.value,
                    failure_category=result.failure_category.value,
                    amount=result.amount,
                    selected_strategy=result.selected_strategy.value if result.selected_strategy else None,
                    policy_outcome=result.policy_outcome.value if result.policy_outcome else None,
                    execution_status=result.execution_status,
                    verification_status=result.verification_status,
                    verified_recovered_amount=result.verified_recovered_amount,
                    final_status=result.final_status.value,
                    is_escalated=result.is_escalated,
                    is_stopped=result.is_stopped,
                    policy_violation=result.policy_violation,
                    violation_details=result.violation_details,
                    truth_provenance=result.truth_provenance.value,
                    audit_event_count=result.audit_event_count,
                    created_at=result.executed_at,
                )
                session.add(case_model)

            session.commit()
            logger.info("Persisted evaluation run '%s' with %d case results.", summary.metadata.batch_id, len(summary.case_results))
            return run_model

    def get_run(self, batch_id: str) -> Optional[BatchRunSummary]:
        """Retrieve a batch evaluation run by its batch_id."""
        with self.session_factory() as session:
            model = session.query(EvaluationRunModel).filter_by(batch_id=batch_id).first()
            if not model:
                return None
            return BatchRunSummary.model_validate(model.summary_json)

    def get_latest_run(self) -> Optional[BatchRunSummary]:
        """Retrieve the most recent batch evaluation run."""
        with self.session_factory() as session:
            model = session.query(EvaluationRunModel).order_by(desc(EvaluationRunModel.created_at)).first()
            if not model:
                return None
            return BatchRunSummary.model_validate(model.summary_json)

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List summary metadata for recent evaluation runs."""
        with self.session_factory() as session:
            models = session.query(EvaluationRunModel).order_by(desc(EvaluationRunModel.created_at)).limit(limit).all()
            return [
                {
                    "batch_id": m.batch_id,
                    "dataset_version": m.dataset_version,
                    "random_seed": m.random_seed,
                    "total_cases": m.total_cases,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in models
            ]

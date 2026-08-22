"""FastAPI Router for Synthetic Batch Evaluation and Benchmark Metrics."""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..database import get_db_session, get_session_factory, create_db_engine
from ..repositories.evaluation_repository import EvaluationRepository
from ..eval.runner import BatchEvaluationRunner
from ..eval.artifacts import save_evaluation_artifacts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Evaluation & Metrics"])


class BatchRunRequest(BaseModel):
    """Request parameters for executing a synthetic benchmark."""
    seed: int = Field(default=42, description="Random seed for deterministic generation")
    count: int = Field(default=60, ge=50, le=500, description="Number of cases to generate (>= 50)")
    dataset_version: str = Field(default="v1.0", description="Dataset version tag")
    save_artifacts: bool = Field(default=True, description="Whether to write JSON/Markdown artifacts to disk")


@router.post("/api/v1/batch/run")
async def run_batch_benchmark(
    request: BatchRunRequest = BatchRunRequest(),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Execute the deterministic 3-way benchmark (NO_ACTION, RETRY_ONLY, AI_REVENUE_RECOVERY_ORCHESTRATOR).

    Does NOT make live Razorpay API calls.
    Returns the comprehensive BatchRunSummary.
    """
    # Create evaluation repository using the session factory
    engine = create_db_engine()
    session_factory = get_session_factory(engine)
    eval_repo = EvaluationRepository(session_factory=session_factory)

    runner = BatchEvaluationRunner(evaluation_repository=eval_repo)
    summary = runner.run_benchmark(
        seed=request.seed,
        count=request.count,
        dataset_version=request.dataset_version,
    )

    if request.save_artifacts:
        save_evaluation_artifacts(summary)

    return summary.model_dump(mode="json")


@router.get("/api/v1/metrics/batch")
async def get_batch_metrics(
    batch_id: Optional[str] = Query(None, description="Optional batch ID. If omitted, returns latest run."),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve persisted batch metrics and baseline comparison."""
    engine = create_db_engine()
    session_factory = get_session_factory(engine)
    eval_repo = EvaluationRepository(session_factory=session_factory)

    if batch_id:
        summary = eval_repo.get_run(batch_id)
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch run '{batch_id}' not found.")
    else:
        summary = eval_repo.get_latest_run()
        if not summary:
            # If no persisted run exists in DB, execute default deterministic benchmark
            runner = BatchEvaluationRunner(evaluation_repository=eval_repo)
            summary = runner.run_benchmark(seed=42, count=60, dataset_version="v1.0")
            save_evaluation_artifacts(summary)

    return summary.model_dump(mode="json")

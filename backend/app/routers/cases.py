import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..models.case_model import RecoveryCaseModel
from ..schemas.enums import CaseStatus, CaseType, FailureCategory, RecoveryStrategy, TruthProvenance
from ..schemas.case import RecoveryCase, SubscriptionMetadata, ActionExecutionRecord, VerificationRecord
from ..schemas.policy import PolicyCheckResult
from ..database import get_db_session
from ..repositories.case_repository import CaseRepository
from ..repositories.audit_repository import AuditRepository
from ..services.audit_service import AuditService
from ..orchestrator.nodes import WorkflowNodes
from ..orchestrator.workflow import run_recovery_workflow
from ..orchestrator.builder import build_recovery_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])


def _db_model_to_case(db_case: RecoveryCaseModel) -> RecoveryCase:
    """Convert an ORM RecoveryCaseModel instance to a validated Pydantic RecoveryCase."""
    return RecoveryCase(
        id=db_case.id,
        case_type=CaseType(db_case.case_type),
        customer_id=db_case.customer_id,
        masked_customer_email=db_case.masked_customer_email,
        masked_customer_phone=db_case.masked_customer_phone,
        customer_segment=db_case.customer_segment or "STANDARD",
        amount=db_case.amount,
        currency=db_case.currency or "INR",
        gateway_reference_id=db_case.gateway_reference_id,
        failure_code=db_case.failure_code,
        failure_description=db_case.failure_description,
        failure_category=FailureCategory(db_case.failure_category),
        attempts_count=db_case.attempts_count or 0,
        max_attempts_allowed=db_case.max_attempts_allowed or 3,
        last_attempt_at=db_case.last_attempt_at,
        subscription_details=SubscriptionMetadata.model_validate(db_case.subscription_details) if db_case.subscription_details else None,
        current_status=CaseStatus(db_case.current_status),
        recommended_strategy=RecoveryStrategy(db_case.recommended_strategy) if db_case.recommended_strategy else None,
        strategy_confidence=db_case.strategy_confidence,
        strategy_rationale=db_case.strategy_rationale,
        policy_evaluation=PolicyCheckResult.model_validate(db_case.policy_evaluation) if db_case.policy_evaluation else None,
        executed_action=ActionExecutionRecord.model_validate(db_case.executed_action) if db_case.executed_action else None,
        verification_outcome=VerificationRecord.model_validate(db_case.verification_outcome) if db_case.verification_outcome else None,
        verified_recovered_amount=db_case.verified_recovered_amount or 0.0,
        is_escalated=db_case.is_escalated or False,
        escalation_reason=db_case.escalation_reason,
        provenance=TruthProvenance(db_case.provenance) if db_case.provenance else TruthProvenance.SYNTHETIC_DATA_RESULT,
        created_at=db_case.created_at or datetime.utcnow(),
        updated_at=db_case.updated_at or datetime.utcnow(),
    )


class CaseIngestRequest(BaseModel):
    """Request schema for batch or single case ingestion."""
    cases: List[RecoveryCase] = Field(description="List of cases to ingest")


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_cases(
    payload: Union[RecoveryCase, CaseIngestRequest, List[RecoveryCase]],
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Ingest one or more recovery cases into the database.

    Validates schema strictly. Does NOT execute recovery actions during ingestion.
    """
    case_repo = CaseRepository(session)
    audit_svc = AuditService(session)

    # Normalize payload into list of RecoveryCase objects
    if isinstance(payload, RecoveryCase):
        cases_to_ingest = [payload]
    elif isinstance(payload, CaseIngestRequest):
        cases_to_ingest = payload.cases
    elif isinstance(payload, list):
        cases_to_ingest = payload
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ingestion payload format.")

    ingested_ids: List[str] = []
    for case in cases_to_ingest:
        existing = case_repo.get_by_id(case.id)
        case_repo.save(case)
        if not existing:
            audit_svc.log_event(
                case_id=case.id,
                event_type="CASE_INGESTED",
                actor="INGESTION_API",
                previous_status=None,
                new_status=case.current_status,
                details={
                    "amount": case.amount,
                    "currency": case.currency,
                    "failure_code": case.failure_code,
                    "failure_category": case.failure_category.value,
                },
                provenance=case.provenance,
            )
        else:
            logger.info("Case '%s' already exists; updated without duplicate CASE_INGESTED audit.", case.id)
        ingested_ids.append(case.id)

    logger.info("Ingested %d cases via API.", len(ingested_ids))
    return {
        "status": "success",
        "ingested_count": len(ingested_ids),
        "case_ids": ingested_ids,
    }


@router.get("")
async def list_cases(
    status: Optional[str] = Query(None, description="Filter by CaseStatus enum value"),
    case_type: Optional[str] = Query(None, description="Filter by CaseType enum value"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """List persisted recovery cases with optional status and workflow filters."""
    case_repo = CaseRepository(session)
    db_cases = case_repo.get_all(limit=limit, offset=offset)
    all_cases = [_db_model_to_case(c) for c in db_cases]

    # Apply in-memory filters if provided
    filtered = all_cases
    if status:
        filtered = [c for c in filtered if c.current_status.value == status]
    if case_type:
        filtered = [c for c in filtered if c.case_type.value == case_type]

    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "cases": [c.model_dump(mode="json") for c in filtered],
    }


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve full details of a recovery case and its associated audit trail."""
    case_repo = CaseRepository(session)
    audit_repo = AuditRepository(session)

    db_case = case_repo.get_by_id(case_id)
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    case = _db_model_to_case(db_case)
    audit_logs = audit_repo.get_by_case_id(case_id)

    return {
        "case": case.model_dump(mode="json"),
        "audit_trail": [
            {
                "id": a.id,
                "case_id": a.case_id,
                "event_type": a.event_type,
                "event_timestamp": a.event_timestamp.isoformat() if a.event_timestamp else None,
                "actor": a.actor,
                "previous_status": a.previous_status,
                "new_status": a.new_status,
                "policy_outcome": a.policy_outcome,
                "strategy": a.strategy,
                "details": a.details,
                "provenance": a.provenance,
            }
            for a in audit_logs
        ],
    }


@router.post("/{case_id}/process")
async def process_case(
    case_id: str,
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Run the complete approved LangGraph recovery workflow on a specific case."""
    case_repo = CaseRepository(session)

    db_case = case_repo.get_by_id(case_id)
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    case = _db_model_to_case(db_case)
    nodes = WorkflowNodes(session=session)
    final_state = run_recovery_workflow(case=case, nodes=nodes, session=session)

    resolved_case = final_state.get("case", case)
    return {
        "status": "success",
        "case_id": case_id,
        "final_status": resolved_case.current_status.value,
        "verified_recovered_amount": resolved_case.verified_recovered_amount,
        "case": resolved_case.model_dump(mode="json"),
        "audit_events": final_state.get("audit_events", []),
    }


@router.get("/{case_id}/process/stream")
async def process_case_stream(
    case_id: str,
    session=Depends(get_db_session),
):
    """Execute LangGraph recovery workflow with real-time Server-Sent Events (SSE) progress.

    Emits SSE events per decision-flow step:
    - detect_and_load (1. Ingestion & Detection)
    - extract_evidence (2. Evidence Scrubbing)
    - diagnose (3. Gemini Diagnosis)
    - score_strategy (4. Strategy Scoring)
    - evaluate_policy (5. Policy Engine Evaluation)
    - execute_action (6. Action Dispatch)
    - verify_outcome (7. Gateway Verification)
    - complete (Workflow Complete)
    """
    case_repo = CaseRepository(session)
    db_case = case_repo.get_by_id(case_id)
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    case = _db_model_to_case(db_case)
    nodes = WorkflowNodes(session=session)
    graph = build_recovery_graph(nodes=nodes)

    initial_state = {
        "case_id": case.id,
        "case": case,
        "truth_provenance": case.provenance,
        "audit_events": [],
    }
    config = {
        "configurable": {
            "thread_id": f"recovery_stream_{case.id}",
        }
    }

    step_info_map = {
        "detect_and_load": {
            "step_index": 1,
            "step_name": "1. Ingestion & Detection",
            "detail": f"Failure code {case.failure_code} ({case.failure_category.value}) loaded.",
        },
        "extract_evidence": {
            "step_index": 2,
            "step_name": "2. Evidence Scrubbing",
            "detail": "PII redacted, payload scrubbed for policy evaluation.",
        },
        "diagnose": {
            "step_index": 3,
            "step_name": "3. Gemini Diagnosis",
            "detail": "Failure category and candidate strategies evaluated.",
        },
        "score_strategy": {
            "step_index": 4,
            "step_name": "4. Strategy Scoring",
            "detail": "Deterministic scoring calculated across recovery actions.",
        },
        "evaluate_policy": {
            "step_index": 5,
            "step_name": "5. Policy Engine Evaluation",
            "detail": "Deterministic Policy Engine safety guardrails evaluated.",
        },
        "execute_action": {
            "step_index": 6,
            "step_name": "6. Action Dispatch",
            "detail": "Policy-authorized action executed safely.",
        },
        "verify_outcome": {
            "step_index": 7,
            "step_name": "7. Gateway Verification",
            "detail": "Payment status verified independently against gateway state.",
        },
        "resolve_state": {
            "step_index": 8,
            "step_name": "State Resolution",
            "detail": "Final case state and recovery metrics consolidated.",
        },
        "log_audit": {
            "step_index": 9,
            "step_name": "Audit Finalization",
            "detail": "Immutable audit record committed.",
        },
    }

    async def event_generator():
        current_case = case
        latest_audit_events = []
        try:
            # Yield initial connection event
            start_payload = {
                "event": "start",
                "case_id": case_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.04)

            for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        if "case" in node_update and node_update["case"]:
                            current_case = node_update["case"]
                        if "audit_events" in node_update:
                            latest_audit_events = node_update["audit_events"]

                    step_meta = step_info_map.get(node_name, {
                        "step_index": 0,
                        "step_name": node_name,
                        "detail": f"Step {node_name} completed.",
                    })

                    event_data = {
                        "event": "step_progress",
                        "step_key": node_name,
                        "step_index": step_meta["step_index"],
                        "step_name": step_meta["step_name"],
                        "status": "completed",
                        "detail": step_meta["detail"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "case": current_case.model_dump(mode="json"),
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    # Small 80ms delay for human-observable visual step transitions
                    await asyncio.sleep(0.08)

            # Persist the resolved case in DB
            case_repo.save(current_case)

            # Emit final complete event
            complete_data = {
                "event": "complete",
                "status": "success",
                "case_id": case_id,
                "final_status": current_case.current_status.value,
                "verified_recovered_amount": current_case.verified_recovered_amount,
                "case": current_case.model_dump(mode="json"),
                "audit_events": latest_audit_events,
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(complete_data)}\n\n"

        except Exception as e:
            logger.error("Error during LangGraph streaming for case '%s': %s", case_id, e)
            error_data = {
                "event": "error",
                "case_id": case_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

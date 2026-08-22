"""Workflow Execution Entry Point for LangGraph Revenue Recovery.

Provides a clean interface for executing recovery cases through the stateful graph.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ..schemas.enums import TruthProvenance
from ..schemas.case import RecoveryCase
from .nodes import WorkflowNodes
from .builder import build_recovery_graph

logger = logging.getLogger(__name__)


def run_recovery_workflow(
    case: RecoveryCase,
    nodes: Optional[WorkflowNodes] = None,
    checkpointer: Optional[Any] = None,
    mock_gateway_response: Optional[Dict[str, Any]] = None,
    mock_gateway_state: Optional[Dict[str, Any]] = None,
    gateway_payment_id: Optional[str] = None,
    truth_provenance: Optional[TruthProvenance] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Execute a single recovery case through the LangGraph recovery workflow.

    Args:
        case: The RecoveryCase entity to process.
        nodes: Optional custom WorkflowNodes container.
        checkpointer: Optional custom checkpointer (defaults to InMemorySaver).
        mock_gateway_response: Optional mock payload for action execution.
        mock_gateway_state: Optional mock payload for gateway verification.
        gateway_payment_id: Optional payment ID for live status query.
        truth_provenance: Explicit provenance tag.
        session: Optional SQLAlchemy DB session.

    Returns:
        Final state dictionary containing the resolved case, execution records,
        verification outcomes, and audit event logs.
    """
    node_container = nodes or WorkflowNodes(session=session)
    graph = build_recovery_graph(nodes=node_container, checkpointer=checkpointer)

    initial_state = {
        "case_id": case.id,
        "case": case,
        "truth_provenance": truth_provenance or case.provenance,
        "mock_gateway_response": mock_gateway_response,
        "mock_gateway_state": mock_gateway_state,
        "gateway_payment_id": gateway_payment_id,
        "audit_events": [],
    }

    config = {
        "configurable": {
            "thread_id": f"recovery_{case.id}",
        }
    }

    logger.info("Executing recovery workflow for case '%s' (thread=%s)", case.id, config["configurable"]["thread_id"])
    final_state = graph.invoke(initial_state, config=config)
    return final_state

"""LangGraph StateGraph Builder for Revenue Recovery.

Builds the complete stateful recovery pipeline with:
- Pure delegated nodes
- Explicit conditional routing at Policy and Execution boundaries
- MemorySaver checkpointing for thread-isolated state persistence
"""

import logging
from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from ..schemas.enums import CaseStatus, PolicyOutcome, RecoveryStrategy
from ..schemas.policy import PolicyCheckResult
from .state import RecoveryWorkflowState
from .nodes import WorkflowNodes

logger = logging.getLogger(__name__)


def route_after_evidence(state: Dict[str, Any]) -> str:
    """Conditional router after evidence extraction.

    If case is already in a terminal state, bypass pipeline directly to resolve_state.
    """
    case = state.get("case")
    final_state = state.get("final_state")
    if (case and case.current_status in [
        CaseStatus.VERIFIED_RECOVERED,
        CaseStatus.ESCALATED,
        CaseStatus.STOPPED,
        CaseStatus.CLOSED_UNRECOVERABLE,
    ]) or final_state in [
        CaseStatus.VERIFIED_RECOVERED,
        CaseStatus.ESCALATED,
        CaseStatus.STOPPED,
        CaseStatus.CLOSED_UNRECOVERABLE,
    ]:
        return "resolve_state"
    return "diagnose"


def route_after_policy(state: Dict[str, Any]) -> str:
    """Conditional router enforcing Policy Engine authority.

    Financial execution is permitted ONLY if policy explicitly ALLOWS or DOWNGRADES,
    AND the approved strategy is an automated financial recovery action.
    BLOCK, ESCALATE, and STOP routes directly to resolve_state without financial calls.
    """
    policy_result: Optional[PolicyCheckResult] = state.get("policy_result")

    if not policy_result or not policy_result.passed:
        return "resolve_state"

    if policy_result.outcome in [PolicyOutcome.ALLOW, PolicyOutcome.DOWNGRADE]:
        approved = policy_result.approved_strategy
        if approved in [
            RecoveryStrategy.PAYMENT_LINK,
            RecoveryStrategy.SMART_RETRY,
            RecoveryStrategy.SUBSCRIPTION_RETRY,
            RecoveryStrategy.UPDATE_PAYMENT_METHOD,
        ]:
            return "execute_action"

    return "resolve_state"


def route_after_execution(state: Dict[str, Any]) -> str:
    """Conditional router after action execution.

    If action executed successfully, proceed to verification.
    Otherwise, route to state resolution.
    """
    execution_record = state.get("execution_record")
    if execution_record and execution_record.status == "SUCCESS":
        return "verify_outcome"
    return "resolve_state"


def build_recovery_graph(
    nodes: Optional[WorkflowNodes] = None,
    checkpointer: Optional[Any] = None,
) -> Any:
    """Construct and compile the LangGraph revenue recovery StateGraph.

    Args:
        nodes: WorkflowNodes container with injected services.
        checkpointer: Checkpoint saver (defaults to InMemorySaver).

    Returns:
        Compiled LangGraph Pregel application.
    """
    node_container = nodes or WorkflowNodes()
    saver = checkpointer if checkpointer is not None else InMemorySaver()

    builder = StateGraph(RecoveryWorkflowState)

    # 1. Add Nodes
    builder.add_node("detect_and_load", node_container.detect_and_load)
    builder.add_node("extract_evidence", node_container.extract_evidence)
    builder.add_node("diagnose", node_container.diagnose)
    builder.add_node("score_strategy", node_container.score_strategy)
    builder.add_node("evaluate_policy", node_container.evaluate_policy)
    builder.add_node("execute_action", node_container.execute_action)
    builder.add_node("verify_outcome", node_container.verify_outcome)
    builder.add_node("resolve_state", node_container.resolve_state)
    builder.add_node("log_audit", node_container.log_audit)

    # 2. Add Edges & Conditional Transitions
    builder.add_edge(START, "detect_and_load")
    builder.add_edge("detect_and_load", "extract_evidence")

    builder.add_conditional_edges(
        "extract_evidence",
        route_after_evidence,
        {
            "diagnose": "diagnose",
            "resolve_state": "resolve_state",
        },
    )

    builder.add_edge("diagnose", "score_strategy")
    builder.add_edge("score_strategy", "evaluate_policy")

    builder.add_conditional_edges(
        "evaluate_policy",
        route_after_policy,
        {
            "execute_action": "execute_action",
            "resolve_state": "resolve_state",
        },
    )

    builder.add_conditional_edges(
        "execute_action",
        route_after_execution,
        {
            "verify_outcome": "verify_outcome",
            "resolve_state": "resolve_state",
        },
    )

    builder.add_edge("verify_outcome", "resolve_state")
    builder.add_edge("resolve_state", "log_audit")
    builder.add_edge("log_audit", END)

    # 3. Compile Graph with Checkpointer
    app = builder.compile(checkpointer=saver)
    logger.info("LangGraph revenue recovery graph compiled successfully.")
    return app

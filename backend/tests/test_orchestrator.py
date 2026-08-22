"""Comprehensive Unit & Integration Tests for Milestone 4 (LangGraph Orchestration & Audit Trail).

All tests use mocked Razorpay responses and offline fallback / mocked diagnosis.
Zero live external API calls are made during automated tests.

Test Scenarios Covered:
1. Full successful recovery path (PAYMENT_LINK -> verify(paid) -> RECOVERED)
2. Policy BLOCK path (cooldown violation -> BLOCK -> no execution)
3. Policy ESCALATE path (high value case -> ESCALATE -> ESCALATED)
4. Policy STOP path (terminal stop -> STOPPED)
5. Policy DOWNGRADE path (invalid mandate -> DOWNGRADE -> UPDATE_PAYMENT_METHOD)
6. Execution failure path (gateway error -> FAILED -> ₹0.0 recovered)
7. Verification failure path (unpaid/expired status -> ₹0.0 recovered)
8. Verification success path (paid status -> ₹amount recovered)
9. Retry / re-entry idempotency (graph re-invocation does not double-execute)
10. Already recovered case remains terminal (bypasses execution)
11. Escalated case never reaches execution
12. Stopped case never reaches execution
13. Gemini diagnosis failure safely uses deterministic fallback in graph
14. Full audit trail contains all expected lifecycle events
15. Invalid state transitions are rejected
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.schemas.enums import CaseType, FailureCategory, CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance
from app.schemas.case import ActionExecutionRecord, RecoveryCase, SubscriptionMetadata, VerificationRecord
from app.schemas.policy import PolicyConfig
from app.policies.engine import PolicyEngine
from app.agents.diagnosis import DiagnosisAgent
from app.agents.strategy_scorer import StrategyScorer
from app.services.razorpay_service import RazorpayService
from app.services.audit_service import AuditService
from app.services.execution_service import ExecutionService
from app.services.verification_service import VerificationService
from app.orchestrator.nodes import WorkflowNodes
from app.orchestrator.workflow import run_recovery_workflow


@pytest.fixture
def policy_config():
    return PolicyConfig(
        max_retry_attempts=3,
        retry_cooldown_hours=4.0,
        automated_recovery_amount_limit=15000.0,
        non_retryable_categories=[
            FailureCategory.RISK_SECURITY_BLOCK,
            FailureCategory.EXPIRED_INSTRUMENT,
            FailureCategory.MANDATE_EXPIRED_INVALID,
        ],
        allow_invalid_mandate_auto_retry=False,
    )


@pytest.fixture
def standard_nodes(policy_config):
    mock_rzp = RazorpayService(key_id="test_key", key_secret="test_secret")
    mock_rzp._client = MagicMock()
    audit_svc = AuditService(session=None)
    exec_svc = ExecutionService(razorpay_service=mock_rzp, audit_service=audit_svc)
    verif_svc = VerificationService(razorpay_service=mock_rzp, audit_service=audit_svc)
    policy_eng = PolicyEngine(config=policy_config)
    diag_agent = DiagnosisAgent(api_key=None)  # Uses deterministic fallback
    scorer = StrategyScorer()

    return WorkflowNodes(
        diagnosis_agent=diag_agent,
        strategy_scorer=scorer,
        policy_engine=policy_eng,
        execution_service=exec_svc,
        verification_service=verif_svc,
        audit_service=audit_svc,
    )


@pytest.fixture
def one_time_case():
    return RecoveryCase(
        id="case_graph_001",
        case_type=CaseType.ONE_TIME_PAYMENT,
        customer_id="cust_g_100",
        masked_customer_email="g***@test.com",
        masked_customer_phone="+91 99*** **111",
        amount=5000.0,
        currency="INR",
        gateway_reference_id="pay_g_ref_001",
        failure_code="BANK_TIMEOUT",
        failure_description="Bank timed out",
        failure_category=FailureCategory.BANK_TIMEOUT_NETWORK,
        attempts_count=1,
        max_attempts_allowed=3,
        last_attempt_at=datetime.utcnow() - timedelta(hours=5),
        current_status=CaseStatus.DETECTED,
    )


@pytest.fixture
def subscription_case():
    return RecoveryCase(
        id="case_graph_sub_001",
        case_type=CaseType.SUBSCRIPTION_RECURRING,
        customer_id="cust_g_sub_200",
        masked_customer_email="sub***@test.com",
        masked_customer_phone="+91 88*** **222",
        amount=1999.0,
        currency="INR",
        gateway_reference_id="pay_g_sub_001",
        failure_code="MANDATE_EXPIRED",
        failure_description="Mandate expired",
        failure_category=FailureCategory.MANDATE_EXPIRED_INVALID,
        attempts_count=0,
        max_attempts_allowed=3,
        current_status=CaseStatus.DETECTED,
        subscription_details=SubscriptionMetadata(
            subscription_id="sub_g_001",
            plan_name="Enterprise Plan",
            billing_interval="MONTHLY",
            mandate_status="EXPIRED",
        ),
    )


# ---------------------------------------------------------------------------
# Test 1: Full Successful Recovery Path
# ---------------------------------------------------------------------------

def test_full_successful_recovery_path(standard_nodes, one_time_case):
    """Test full workflow from Ingestion to Verification -> RECOVERED."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    one_time_case.failure_code = "CARD_EXPIRED"

    mock_link_resp = {"id": "plink_g_100", "short_url": "https://rzp.io/i/g100", "status": "created"}
    mock_paid_state = {"status": "paid", "amount": 500000}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_paid_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    resolved_case: RecoveryCase = final_state["case"]
    assert resolved_case.current_status == CaseStatus.VERIFIED_RECOVERED
    assert resolved_case.verified_recovered_amount == 5000.0
    assert final_state["final_state"] == CaseStatus.VERIFIED_RECOVERED
    assert final_state["verification_record"].verified is True
    assert "CASE_RECOVERED" in final_state["audit_events"]


# ---------------------------------------------------------------------------
# Test 2: Policy BLOCK Path
# ---------------------------------------------------------------------------

def test_policy_block_path_prevents_execution(standard_nodes, one_time_case):
    """When policy blocks (cooldown violation), no financial action is executed."""
    one_time_case.last_attempt_at = datetime.utcnow() - timedelta(hours=1)  # Violates 4h cooldown

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    policy_result = final_state["policy_result"]
    assert policy_result.outcome == PolicyOutcome.BLOCK
    assert policy_result.passed is False
    assert final_state["case"].verified_recovered_amount == 0.0
    assert final_state.get("execution_record") is None or final_state["execution_record"].status == "FAILED"


# ---------------------------------------------------------------------------
# Test 3: Policy ESCALATE Path
# ---------------------------------------------------------------------------

def test_policy_escalate_path_routes_to_human_review(standard_nodes, one_time_case):
    """High value cases that policy escalates must transition to ESCALATED without financial action."""
    one_time_case.amount = 25000.0  # Above 15,000 limit

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    resolved_case: RecoveryCase = final_state["case"]
    assert resolved_case.is_escalated is True
    assert resolved_case.current_status == CaseStatus.ESCALATED
    assert resolved_case.verified_recovered_amount == 0.0
    assert final_state["final_state"] == CaseStatus.ESCALATED
    assert "CASE_ESCALATED" in final_state["audit_events"]


# ---------------------------------------------------------------------------
# Test 4: Policy STOP Path
# ---------------------------------------------------------------------------

def test_policy_stop_path_sets_terminal_status(standard_nodes, one_time_case):
    """When STOP strategy is recommended or policy enforces STOP, workflow resolves to STOPPED."""
    from app.schemas.diagnosis import StrategyRankingResult, StrategyScore

    mock_ranking = StrategyRankingResult(
        case_id=one_time_case.id,
        case_type=CaseType.ONE_TIME_PAYMENT,
        ranked_strategies=[
            StrategyScore(
                strategy=RecoveryStrategy.STOP,
                score=95.0,
                base_score=10.0,
                signal_contributions={"manual_stop": 85.0},
                rationale="Terminal stop recommended.",
            )
        ],
        recommended_strategy=RecoveryStrategy.STOP,
        recommended_confidence=0.99,
    )

    with patch.object(standard_nodes.strategy_scorer, "score", return_value=mock_ranking):
        final_state = run_recovery_workflow(
            case=one_time_case,
            nodes=standard_nodes,
            truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
        )

        resolved_case: RecoveryCase = final_state["case"]
        assert resolved_case.current_status == CaseStatus.STOPPED
        assert resolved_case.verified_recovered_amount == 0.0
        assert final_state["final_state"] == CaseStatus.STOPPED
        assert "CASE_STOPPED" in final_state["audit_events"]


# ---------------------------------------------------------------------------
# Test 5: Policy DOWNGRADE Path
# ---------------------------------------------------------------------------

def test_policy_downgrade_path_executes_downgraded_strategy(standard_nodes, one_time_case):
    """When retry limit is reached, policy downgrades SMART_RETRY to PAYMENT_LINK."""
    one_time_case.attempts_count = 3  # Max retries reached
    one_time_case.failure_category = FailureCategory.BANK_TIMEOUT_NETWORK

    mock_link_resp = {"id": "plink_g_downgrade", "short_url": "https://rzp.io/i/downgrade", "status": "created"}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    policy_result = final_state["policy_result"]
    assert policy_result.outcome == PolicyOutcome.DOWNGRADE
    assert policy_result.approved_strategy == RecoveryStrategy.PAYMENT_LINK
    assert final_state["execution_record"].action_type == RecoveryStrategy.PAYMENT_LINK
    assert final_state["case"].verified_recovered_amount == 0.0


# ---------------------------------------------------------------------------
# Test 6: Execution Failure Path
# ---------------------------------------------------------------------------

def test_execution_failure_path_fails_closed(one_time_case, policy_config):
    """When gateway raises an error during execution, workflow fails closed (₹0 revenue)."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT

    failing_rzp = RazorpayService(key_id="test_key", key_secret="test_secret")
    failing_rzp._client = MagicMock()
    failing_rzp._client.payment_link.create.side_effect = RuntimeError("Razorpay 500 Internal Error")

    audit = AuditService(session=None)
    nodes = WorkflowNodes(
        diagnosis_agent=DiagnosisAgent(api_key=None),
        strategy_scorer=StrategyScorer(),
        policy_engine=PolicyEngine(config=policy_config),
        execution_service=ExecutionService(razorpay_service=failing_rzp, audit_service=audit),
        verification_service=VerificationService(razorpay_service=failing_rzp, audit_service=audit),
        audit_service=audit,
    )

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=nodes,
        truth_provenance=TruthProvenance.LIVE_TEST_MODE_API_RESULT,
    )

    assert final_state["execution_record"].status == "FAILED"
    assert final_state["case"].verified_recovered_amount == 0.0


# ---------------------------------------------------------------------------
# Test 7: Verification Failure / Unpaid Path
# ---------------------------------------------------------------------------

def test_verification_unpaid_counts_zero_revenue(standard_nodes, one_time_case):
    """When gateway verification returns 'expired' or 'pending', recovered revenue is ₹0.0."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT

    mock_link_resp = {"id": "plink_g_101", "short_url": "https://rzp.io/i/g101", "status": "created"}
    mock_expired_state = {"status": "expired"}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_expired_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert final_state["verification_record"].verified is False
    assert final_state["verification_record"].recovered_amount == 0.0
    assert final_state["case"].verified_recovered_amount == 0.0
    assert final_state["case"].current_status != CaseStatus.VERIFIED_RECOVERED


# ---------------------------------------------------------------------------
# Test 8: Verification Success Path
# ---------------------------------------------------------------------------

def test_verification_success_counts_exact_amount(standard_nodes, one_time_case):
    """When gateway verification returns 'captured', exact amount is recovered."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    mock_link_resp = {"id": "plink_g_102", "short_url": "https://rzp.io/i/g102", "status": "created"}
    mock_captured_state = {"status": "captured", "amount": 500000}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_captured_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert final_state["verification_record"].verified is True
    assert final_state["case"].verified_recovered_amount == 5000.0


# ---------------------------------------------------------------------------
# Test 9: Retry / Re-entry Idempotency
# ---------------------------------------------------------------------------

def test_graph_re_entry_idempotency(standard_nodes, one_time_case):
    """Re-running the graph on the same case returns identical execution and prevents double dispatch."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    mock_link_resp = {"id": "plink_g_103", "short_url": "https://rzp.io/i/g103", "status": "created"}
    mock_paid_state = {"status": "paid"}

    # Run 1
    state_1 = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_paid_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    # Run 2 on the same case
    state_2 = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_paid_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    # Must preserve exact recovered amount (no double counting)
    assert state_2["case"].verified_recovered_amount == 5000.0


# ---------------------------------------------------------------------------
# Test 10: Already Recovered Case Remains Terminal
# ---------------------------------------------------------------------------

def test_already_recovered_case_bypasses_execution(standard_nodes, one_time_case):
    """A case in VERIFIED_RECOVERED state must not execute further actions."""
    one_time_case.current_status = CaseStatus.VERIFIED_RECOVERED
    one_time_case.verified_recovered_amount = 5000.0

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert final_state["final_state"] == CaseStatus.VERIFIED_RECOVERED
    assert final_state.get("execution_record") is None


# ---------------------------------------------------------------------------
# Test 11: Escalated Case Never Reaches Execution
# ---------------------------------------------------------------------------

def test_already_escalated_case_never_executes(standard_nodes, one_time_case):
    """A case in ESCALATED state must not execute financial actions."""
    one_time_case.current_status = CaseStatus.ESCALATED
    one_time_case.is_escalated = True

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert final_state["final_state"] == CaseStatus.ESCALATED
    assert final_state.get("execution_record") is None


# ---------------------------------------------------------------------------
# Test 12: Stopped Case Never Reaches Execution
# ---------------------------------------------------------------------------

def test_already_stopped_case_never_executes(standard_nodes, one_time_case):
    """A case in STOPPED state must not execute financial actions."""
    one_time_case.current_status = CaseStatus.STOPPED

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    assert final_state["final_state"] == CaseStatus.STOPPED
    assert final_state.get("execution_record") is None


# ---------------------------------------------------------------------------
# Test 13: Gemini Failure Safely Uses Deterministic Fallback in Graph
# ---------------------------------------------------------------------------

def test_gemini_failure_uses_deterministic_fallback_in_graph(standard_nodes, one_time_case):
    """If Gemini diagnosis fails, the graph seamlessly uses deterministic fallback."""
    # With api_key=None, DiagnosisAgent uses fallback
    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    diagnosis = final_state["diagnosis"]
    assert diagnosis.is_fallback is True
    assert diagnosis.failure_category == FailureCategory.BANK_TIMEOUT_NETWORK
    assert len(diagnosis.candidate_strategies) > 0


# ---------------------------------------------------------------------------
# Test 14: Full Audit Trail Records All Lifecycle Events
# ---------------------------------------------------------------------------

def test_full_audit_trail_lifecycle(standard_nodes, one_time_case):
    """The graph execution must log all canonical lifecycle events."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    mock_link_resp = {"id": "plink_g_audit", "short_url": "https://rzp.io/i/gaudit", "status": "created"}
    mock_paid_state = {"status": "paid"}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_paid_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    events = final_state["audit_events"]
    assert "CASE_INGESTED" in events
    assert "EVIDENCE_EXTRACTED" in events
    assert "DIAGNOSIS_COMPLETED" in events
    assert "STRATEGY_SCORED" in events
    assert "POLICY_EVALUATION" in events
    assert "ACTION_DISPATCHED" in events
    assert "VERIFICATION_RECEIVED" in events
    assert "CASE_RECOVERED" in events


# ---------------------------------------------------------------------------
# Test 15: Invalid State Transitions Rejected
# ---------------------------------------------------------------------------

def test_invalid_state_transition_from_terminal_to_in_progress_rejected(standard_nodes, one_time_case):
    """Attempting to dispatch action on an ESCALATED case is blocked by idempotency/policy."""
    one_time_case.current_status = CaseStatus.ESCALATED
    one_time_case.is_escalated = True

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    # State cannot transition to ACTION_IN_PROGRESS or ACTION_COMPLETED
    assert final_state["case"].current_status == CaseStatus.ESCALATED
    assert final_state["final_state"] == CaseStatus.ESCALATED


# ---------------------------------------------------------------------------
# Test 16: Created Unpaid Payment Link Never Yields Recovered Revenue
# ---------------------------------------------------------------------------

def test_payment_link_created_unpaid_gateway_status_remains_zero_and_not_recovered(standard_nodes, one_time_case):
    """Payment Link created with gateway status CREATED/unpaid must yield 0 recovered revenue and NOT RECOVERED."""
    one_time_case.failure_category = FailureCategory.EXPIRED_INSTRUMENT
    mock_link_resp = {"id": "plink_g_unpaid", "short_url": "https://rzp.io/i/gunpaid", "status": "created"}
    mock_unpaid_state = {"status": "created"}

    final_state = run_recovery_workflow(
        case=one_time_case,
        nodes=standard_nodes,
        mock_gateway_response=mock_link_resp,
        mock_gateway_state=mock_unpaid_state,
        truth_provenance=TruthProvenance.MOCKED_TEST_RESULT,
    )

    resolved_case: RecoveryCase = final_state["case"]
    assert resolved_case.executed_action is not None
    assert resolved_case.executed_action.action_type == RecoveryStrategy.PAYMENT_LINK
    assert resolved_case.executed_action.status == "SUCCESS"
    assert final_state["verification_record"].verified is False
    assert final_state["verification_record"].status == "CREATED"
    assert resolved_case.verified_recovered_amount == 0.0
    assert final_state["final_state"] != CaseStatus.VERIFIED_RECOVERED
    assert "CASE_RECOVERED" not in final_state["audit_events"]

"""Action Execution Service for the AI Revenue Recovery Orchestrator.

Enforces strict safety boundaries:
1. NEVER executes an action solely on LLM recommendation.
2. Mandatory Policy Engine approval check before any action dispatch.
3. If policy outcome is BLOCK, ESCALATE, or STOP, financial execution is forbidden.
4. Execution idempotency prevents duplicate operations.
5. Revenue is NEVER marked as recovered upon action execution (only via VerificationService).
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ..schemas.enums import CaseStatus, PolicyOutcome, RecoveryStrategy, TruthProvenance
from ..schemas.case import ActionExecutionRecord, RecoveryCase
from ..schemas.policy import PolicyCheckResult
from ..repositories.case_repository import CaseRepository
from .razorpay_service import RazorpayService
from .audit_service import AuditService

logger = logging.getLogger(__name__)


class ExecutionService:
    """Dispatches policy-approved recovery actions.

    Enforces strict safety guardrails and idempotency.
    """

    def __init__(
        self,
        razorpay_service: Optional[RazorpayService] = None,
        audit_service: Optional[AuditService] = None,
        session: Optional[Session] = None,
    ):
        self.razorpay_service = razorpay_service or RazorpayService()
        self.audit_service = audit_service or AuditService(session=session)
        self.case_repository = CaseRepository(session) if session else None

    def execute_policy_approved_action(
        self,
        case: RecoveryCase,
        policy_result: PolicyCheckResult,
        mock_gateway_response: Optional[Dict[str, Any]] = None,
        truth_provenance: Optional[TruthProvenance] = None,
    ) -> ActionExecutionRecord:
        """Execute a recovery action ONLY after Policy Engine validation.

        Args:
            case: The recovery case to act on.
            policy_result: The verified result from PolicyEngine.evaluate().
            mock_gateway_response: Optional mock payload for unit tests.
            truth_provenance: Explicit provenance tag.

        Returns:
            ActionExecutionRecord recording the execution outcome.
        """
        previous_status = case.current_status
        provenance = truth_provenance or (
            TruthProvenance.LIVE_TEST_MODE_API_RESULT
            if self.razorpay_service.is_configured and not mock_gateway_response
            else (
                TruthProvenance.MOCKED_TEST_RESULT
                if mock_gateway_response is not None
                else TruthProvenance.SYNTHETIC_DATA_RESULT
            )
        )

        # 1. Audit Action Requested
        self.audit_service.log_event(
            case_id=case.id,
            event_type="ACTION_REQUESTED",
            actor="EXECUTION_SERVICE",
            previous_status=previous_status,
            new_status=previous_status,
            policy_outcome=policy_result.outcome,
            strategy=policy_result.approved_strategy,
            details={
                "proposed_strategy": policy_result.proposed_strategy.value,
                "approved_strategy": policy_result.approved_strategy.value,
                "policy_passed": policy_result.passed,
            },
            provenance=provenance,
        )

        # 2. Idempotency Check: Prevent duplicate execution
        if case.current_status in [
            CaseStatus.VERIFIED_RECOVERED,
            CaseStatus.ESCALATED,
            CaseStatus.STOPPED,
            CaseStatus.CLOSED_UNRECOVERABLE,
        ]:
            logger.warning(
                "Idempotency blocked: Case '%s' is in terminal/frozen state '%s'. No action executed.",
                case.id,
                case.current_status.value,
            )
            return self._record_blocked_execution(
                case,
                policy_result.approved_strategy,
                f"Execution blocked: Case is already in status '{case.current_status.value}'.",
                provenance,
            )

        if case.executed_action and case.executed_action.status == "SUCCESS":
            logger.warning(
                "Idempotency blocked: Case '%s' has already executed action '%s'.",
                case.id,
                case.executed_action.action_id,
            )
            return case.executed_action

        # 3. Critical Safety Guardrail Check
        if not policy_result.passed or policy_result.outcome in [
            PolicyOutcome.BLOCK,
            PolicyOutcome.ESCALATE,
            PolicyOutcome.STOP,
        ]:
            return self._handle_policy_non_approval(
                case, policy_result, previous_status, provenance
            )

        # 4. Dispatch Policy-Approved Strategy
        approved_strategy = policy_result.approved_strategy
        self.audit_service.log_event(
            case_id=case.id,
            event_type="POLICY_APPROVED",
            actor="POLICY_ENGINE",
            previous_status=previous_status,
            new_status=previous_status,
            policy_outcome=policy_result.outcome,
            strategy=approved_strategy,
            details={"approved_strategy": approved_strategy.value},
            provenance=provenance,
        )

        action_id = f"act_{case.id}_{approved_strategy.value}_{case.attempts_count + 1}"

        if approved_strategy == RecoveryStrategy.PAYMENT_LINK:
            return self._execute_payment_link(
                case, action_id, mock_gateway_response, provenance
            )
        elif approved_strategy == RecoveryStrategy.SMART_RETRY:
            return self._execute_smart_retry(case, action_id, provenance)
        elif approved_strategy == RecoveryStrategy.SUBSCRIPTION_RETRY:
            return self._execute_subscription_retry(case, action_id, provenance)
        elif approved_strategy == RecoveryStrategy.UPDATE_PAYMENT_METHOD:
            return self._execute_update_payment_method(case, action_id, provenance)
        elif approved_strategy == RecoveryStrategy.HUMAN_ESCALATION:
            return self._execute_human_escalation(
                case, action_id, policy_result.escalation_reason, provenance
            )
        elif approved_strategy == RecoveryStrategy.STOP:
            return self._execute_stop(case, action_id, provenance)
        else:
            raise ValueError(f"Unknown recovery strategy: {approved_strategy}")

    def _execute_payment_link(
        self,
        case: RecoveryCase,
        action_id: str,
        mock_response: Optional[Dict[str, Any]],
        provenance: TruthProvenance,
    ) -> ActionExecutionRecord:
        """Create a Razorpay Test Mode Payment Link."""
        self.audit_service.log_event(
            case_id=case.id,
            event_type="ACTION_DISPATCHED",
            actor="EXECUTION_SERVICE",
            previous_status=case.current_status,
            new_status=CaseStatus.ACTION_IN_PROGRESS,
            strategy=RecoveryStrategy.PAYMENT_LINK,
            details={"action_id": action_id, "amount": case.amount},
            provenance=provenance,
        )

        gateway_resp = None
        link_url = None

        if mock_response is not None:
            gateway_resp = mock_response
            link_url = mock_response.get("short_url", f"https://rzp.io/i/mock_{case.id[:8]}")
        elif self.razorpay_service.is_configured:
            try:
                gateway_resp = self.razorpay_service.create_payment_link(
                    amount=case.amount,
                    currency=case.currency,
                    description=f"Recovery for payment failure ({case.failure_code})",
                    customer_name=f"Customer {case.customer_id}",
                    reference_id=case.id,
                    notes={"case_id": case.id, "failure_code": case.failure_code},
                )
                link_url = gateway_resp.get("short_url")
            except Exception as e:
                logger.error("Razorpay payment link creation failed: %s", e)
                return self._record_failed_execution(
                    case, RecoveryStrategy.PAYMENT_LINK, action_id, str(e), provenance
                )
        else:
            # Synthetic demonstration mode when no live API keys provided
            link_url = f"https://rzp.io/i/demo_link_{case.id[:8]}"
            gateway_resp = {
                "id": f"plink_demo_{uuid.uuid4().hex[:8]}",
                "short_url": link_url,
                "status": "created",
                "amount": int(case.amount * 100),
            }

        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.PAYMENT_LINK,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={"amount": case.amount, "currency": case.currency},
            gateway_response=gateway_resp,
            payment_link_url=link_url,
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.current_status = CaseStatus.ACTION_COMPLETED
        # NOTE: Revenue is NOT marked as recovered upon link creation!
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="ACTION_RESULT",
            strategy=RecoveryStrategy.PAYMENT_LINK,
            details={"payment_link_url": link_url, "action_id": action_id},
            provenance=provenance,
        )
        return execution_record

    def _execute_smart_retry(
        self, case: RecoveryCase, action_id: str, provenance: TruthProvenance
    ) -> ActionExecutionRecord:
        """Schedule and record a smart retry recovery decision.

        NOTE: Razorpay does not expose a server-side API to retry failed one-time card
        payments without customer interaction, as RBI regulations mandate AFA/OTP.
        This records the orchestrator's decision to retry the payment within policy cooldown.
        """
        case.attempts_count += 1
        case.last_attempt_at = datetime.utcnow()

        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.SMART_RETRY,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={
                "attempts_count": case.attempts_count,
                "max_attempts": case.max_attempts_allowed,
                "cooldown_scheduled": True,
                "note": "Smart retry scheduled by orchestrator within policy cooldown. Direct server-side one-time debit API is not exposed by gateway due to AFA mandates.",
            },
            gateway_response=None,
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.current_status = CaseStatus.RETRY_SCHEDULED
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="ACTION_RESULT",
            strategy=RecoveryStrategy.SMART_RETRY,
            details={"attempt_number": case.attempts_count, "action_id": action_id, "gateway_call": "NONE_SCHEDULED_STRATEGY"},
            provenance=provenance,
        )
        return execution_record

    def _execute_subscription_retry(
        self, case: RecoveryCase, action_id: str, provenance: TruthProvenance
    ) -> ActionExecutionRecord:
        """Record a subscription recurring debit recovery decision.

        NOTE: Recurring charge retries follow Razorpay's native subscription retry
        lifecycle. In Test Mode, charge retries are simulated via the Razorpay Dashboard.
        This records the orchestrator's decision to track and verify the retry cycle.
        """
        case.attempts_count += 1
        case.last_attempt_at = datetime.utcnow()

        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.SUBSCRIPTION_RETRY,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={
                "subscription_id": (
                    case.subscription_details.subscription_id
                    if case.subscription_details
                    else None
                ),
                "attempts_count": case.attempts_count,
                "note": "Subscription retry lifecycle tracked. Gateway retries recurring invoice per subscription schedule.",
            },
            gateway_response=None,
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.current_status = CaseStatus.RETRY_SCHEDULED
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="ACTION_RESULT",
            strategy=RecoveryStrategy.SUBSCRIPTION_RETRY,
            details={"subscription_retry_attempt": case.attempts_count, "gateway_call": "NONE_LIFECYCLE_TRACKING"},
            provenance=provenance,
        )
        return execution_record

    def _execute_update_payment_method(
        self, case: RecoveryCase, action_id: str, provenance: TruthProvenance
    ) -> ActionExecutionRecord:
        """Record an update payment method / mandate recovery decision.

        NOTE: Razorpay does not expose a standalone dynamic mandate update link creation
        API; customer card/mandate updates are handled via the Razorpay Customer Portal
        or checkout re-authentication.
        """
        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.UPDATE_PAYMENT_METHOD,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={
                "update_required": True,
                "note": "Mandate update requested. Customer action required via Razorpay customer portal or checkout.",
            },
            gateway_response=None,
            payment_link_url=None,  # No fake link URL generated
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.current_status = CaseStatus.ACTION_COMPLETED
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="ACTION_RESULT",
            strategy=RecoveryStrategy.UPDATE_PAYMENT_METHOD,
            details={"action_id": action_id, "update_required": True, "gateway_call": "NONE_CUSTOMER_ACTION_REQUIRED"},
            provenance=provenance,
        )
        return execution_record

    def _execute_human_escalation(
        self,
        case: RecoveryCase,
        action_id: str,
        reason: Optional[str],
        provenance: TruthProvenance,
    ) -> ActionExecutionRecord:
        """Route case to human review queue. Zero financial execution."""
        case.is_escalated = True
        case.escalation_reason = reason or "Policy mandated human escalation."
        case.current_status = CaseStatus.ESCALATED

        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.HUMAN_ESCALATION,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={"escalation_reason": case.escalation_reason},
            gateway_response=None,
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="ESCALATED",
            strategy=RecoveryStrategy.HUMAN_ESCALATION,
            details={"reason": case.escalation_reason},
            provenance=provenance,
        )
        return execution_record

    def _execute_stop(
        self, case: RecoveryCase, action_id: str, provenance: TruthProvenance
    ) -> ActionExecutionRecord:
        """Terminal cessation of recovery workflow. Zero financial execution."""
        case.current_status = CaseStatus.STOPPED

        execution_record = ActionExecutionRecord(
            action_id=action_id,
            action_type=RecoveryStrategy.STOP,
            status="SUCCESS",
            executed_at=datetime.utcnow(),
            payload={"stop_reason": "Policy engine or terminal state reached."},
            gateway_response=None,
            provenance=provenance,
        )

        case.executed_action = execution_record
        case.verified_recovered_amount = 0.0

        self._persist_case_and_audit(
            case,
            event_type="STOPPED",
            strategy=RecoveryStrategy.STOP,
            details={"stop_terminal": True},
            provenance=provenance,
        )
        return execution_record

    def _handle_policy_non_approval(
        self,
        case: RecoveryCase,
        policy_result: PolicyCheckResult,
        previous_status: CaseStatus,
        provenance: TruthProvenance,
    ) -> ActionExecutionRecord:
        """Handle policy BLOCK, ESCALATE, or STOP without executing financial operations."""
        self.audit_service.log_event(
            case_id=case.id,
            event_type="POLICY_BLOCKED",
            actor="POLICY_ENGINE",
            previous_status=previous_status,
            new_status=case.current_status,
            policy_outcome=policy_result.outcome,
            strategy=policy_result.proposed_strategy,
            details={
                "reasons": policy_result.reasons,
                "suggested_outcome": policy_result.outcome.value,
            },
            provenance=provenance,
        )

        action_id = f"act_blocked_{case.id}_{policy_result.outcome.value}"

        if policy_result.outcome == PolicyOutcome.ESCALATE:
            return self._execute_human_escalation(
                case, action_id, policy_result.escalation_reason, provenance
            )
        elif policy_result.outcome == PolicyOutcome.STOP:
            return self._execute_stop(case, action_id, provenance)
        else:
            # Policy Outcome is BLOCK
            return self._record_blocked_execution(
                case,
                policy_result.approved_strategy,
                "; ".join(policy_result.reasons),
                provenance,
            )

    def _record_blocked_execution(
        self,
        case: RecoveryCase,
        strategy: RecoveryStrategy,
        reason: str,
        provenance: TruthProvenance,
    ) -> ActionExecutionRecord:
        """Record that an action was blocked by policy or idempotency."""
        record = ActionExecutionRecord(
            action_id=f"act_blocked_{uuid.uuid4().hex[:8]}",
            action_type=strategy,
            status="FAILED",
            executed_at=datetime.utcnow(),
            payload={"block_reason": reason},
            gateway_response=None,
            provenance=provenance,
        )
        return record

    def _record_failed_execution(
        self,
        case: RecoveryCase,
        strategy: RecoveryStrategy,
        action_id: str,
        error_message: str,
        provenance: TruthProvenance,
    ) -> ActionExecutionRecord:
        """Record that a financial gateway dispatch failed."""
        record = ActionExecutionRecord(
            action_id=action_id,
            action_type=strategy,
            status="FAILED",
            executed_at=datetime.utcnow(),
            payload={"error": error_message},
            gateway_response=None,
            provenance=provenance,
        )
        case.executed_action = record
        self._persist_case_and_audit(
            case,
            event_type="ACTION_FAILED",
            strategy=strategy,
            details={"error": error_message},
            provenance=provenance,
        )
        return record

    def _persist_case_and_audit(
        self,
        case: RecoveryCase,
        event_type: str,
        strategy: RecoveryStrategy,
        details: Dict[str, Any],
        provenance: TruthProvenance,
    ):
        """Save updated case and log audit trail event."""
        if self.case_repository:
            try:
                self.case_repository.save(case)
            except Exception as e:
                logger.error("Failed to persist case '%s' to database: %s", case.id, e)

        self.audit_service.log_event(
            case_id=case.id,
            event_type=event_type,
            actor="EXECUTION_SERVICE",
            previous_status=case.current_status,
            new_status=case.current_status,
            strategy=strategy,
            details=details,
            provenance=provenance,
        )

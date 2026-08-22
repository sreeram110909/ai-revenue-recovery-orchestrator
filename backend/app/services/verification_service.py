"""Outcome Verification Service for the AI Revenue Recovery Orchestrator.

Independent from Execution.
Enforces strict revenue accounting:
1. Verified payment success (PAID / CAPTURED) is the ONLY condition that counts as recovered revenue.
2. HTTP 200, action success, link creation, or LLM outputs NEVER constitute recovery.
3. Strict double-counting protection.
4. Truth provenance tracking: LIVE_TEST_MODE_API_RESULT, MOCKED_TEST_RESULT, SYNTHETIC_DATA_RESULT.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ..schemas.enums import CaseStatus, TruthProvenance
from ..schemas.case import RecoveryCase, VerificationRecord
from ..repositories.case_repository import CaseRepository
from .razorpay_service import RazorpayService
from .audit_service import AuditService

logger = logging.getLogger(__name__)


class VerificationService:
    """Independent verification service to confirm actual payment settlement."""

    def __init__(
        self,
        razorpay_service: Optional[RazorpayService] = None,
        audit_service: Optional[AuditService] = None,
        session: Optional[Session] = None,
    ):
        self.razorpay_service = razorpay_service or RazorpayService()
        self.audit_service = audit_service or AuditService(session=session)
        self.case_repository = CaseRepository(session) if session else None

    def verify_recovery_outcome(
        self,
        case: RecoveryCase,
        gateway_payment_id: Optional[str] = None,
        mock_gateway_state: Optional[Dict[str, Any]] = None,
        truth_provenance: Optional[TruthProvenance] = None,
    ) -> VerificationRecord:
        """Verify the true outcome of a recovery action against gateway state.

        Formula:
            if gateway_status in ["paid", "captured"]:
                verified_recovered_amount = case.amount
                case.current_status = CaseStatus.VERIFIED_RECOVERED
            else:
                verified_recovered_amount = 0.0

        Args:
            case: The recovery case to verify.
            gateway_payment_id: Specific payment ID to check via Razorpay API.
            mock_gateway_state: Direct gateway state dict for automated tests.
            truth_provenance: Explicit provenance tag.

        Returns:
            VerificationRecord with verified status and recovered amount.
        """
        previous_status = case.current_status
        provenance = truth_provenance or (
            TruthProvenance.LIVE_TEST_MODE_API_RESULT
            if self.razorpay_service.is_configured and not mock_gateway_state
            else (
                TruthProvenance.MOCKED_TEST_RESULT
                if mock_gateway_state is not None
                else TruthProvenance.SYNTHETIC_DATA_RESULT
            )
        )

        # 1. Audit Verification Requested
        self.audit_service.log_event(
            case_id=case.id,
            event_type="VERIFICATION_REQUESTED",
            actor="VERIFICATION_SERVICE",
            previous_status=previous_status,
            new_status=previous_status,
            details={"gateway_payment_id": gateway_payment_id},
            provenance=provenance,
        )

        # 2. Prevent double-counting if already verified recovered
        if (
            case.current_status == CaseStatus.VERIFIED_RECOVERED
            and case.verified_recovered_amount > 0.0
            and case.verification_outcome
            and case.verification_outcome.verified
        ):
            logger.info(
                "Double-counting protection: Case '%s' is already verified as recovered.",
                case.id,
            )
            return case.verification_outcome

        # 3. Retrieve Gateway State
        gateway_status = "pending"
        verification_method = "SYNTHETIC_EVALUATION"
        details_msg = ""

        if mock_gateway_state is not None:
            gateway_status = str(mock_gateway_state.get("status", "pending")).lower()
            verification_method = "MOCKED_TEST_RESULT"
            details_msg = f"Mocked verification state: status={gateway_status}"

        elif self.razorpay_service.is_configured and gateway_payment_id:
            try:
                resp = self.razorpay_service.fetch_payment(gateway_payment_id)
                gateway_status = str(resp.get("status", "failed")).lower()
                verification_method = "GATEWAY_API_CHECK"
                details_msg = f"Live Razorpay Test Mode fetch: status={gateway_status}"
            except Exception as e:
                logger.error("Failed to query Razorpay payment status: %s", e)
                gateway_status = "error"
                details_msg = f"Gateway check error: {e}"

        elif self.razorpay_service.is_configured and case.executed_action and case.executed_action.payment_link_url:
            # Check payment link status if link ID exists
            plink_id = (
                case.executed_action.gateway_response.get("id")
                if case.executed_action.gateway_response
                else None
            )
            if plink_id:
                try:
                    plink_resp = self.razorpay_service.fetch_payment_link(plink_id)
                    gateway_status = str(plink_resp.get("status", "created")).lower()
                    verification_method = "GATEWAY_API_CHECK"
                    details_msg = f"Live Razorpay Payment Link fetch: status={gateway_status}"
                except Exception as e:
                    logger.error("Failed to query Razorpay payment link status: %s", e)
                    gateway_status = "error"
                    details_msg = f"Gateway link check error: {e}"

        # 4. Strict Accounting Evaluation
        # Only "captured" (payments) or "paid" (payment links/invoices) are settled
        is_paid = gateway_status in ["captured", "paid"]

        if is_paid:
            recovered_amount = case.amount
            verification_status = "PAID"
            case.verified_recovered_amount = recovered_amount
            case.current_status = CaseStatus.VERIFIED_RECOVERED
            details = details_msg or f"Payment verified as {gateway_status}. ₹{recovered_amount} recovered."
        else:
            recovered_amount = 0.0
            verification_status = gateway_status.upper()
            case.verified_recovered_amount = 0.0
            details = details_msg or f"Payment remains unverified (status: {gateway_status}). ₹0.0 recovered."

        record = VerificationRecord(
            verified=is_paid,
            status=verification_status,
            verified_at=datetime.utcnow(),
            recovered_amount=recovered_amount,
            verification_method=verification_method,
            details=details,
            provenance=provenance,
        )

        case.verification_outcome = record

        # 5. Persist Case & Audit Trail
        if self.case_repository:
            try:
                self.case_repository.save(case)
            except Exception as e:
                logger.error("Failed to persist verified case '%s': %s", case.id, e)

        self.audit_service.log_event(
            case_id=case.id,
            event_type="VERIFICATION_RECEIVED",
            actor="VERIFICATION_SERVICE",
            previous_status=previous_status,
            new_status=case.current_status,
            details={
                "verified": is_paid,
                "gateway_status": gateway_status,
                "recovered_amount": recovered_amount,
            },
            provenance=provenance,
        )

        if is_paid:
            self.audit_service.log_event(
                case_id=case.id,
                event_type="RECOVERY_CONFIRMED",
                actor="VERIFICATION_SERVICE",
                previous_status=previous_status,
                new_status=CaseStatus.VERIFIED_RECOVERED,
                details={
                    "verified_recovered_amount": recovered_amount,
                    "currency": case.currency,
                },
                provenance=provenance,
            )

        return record

"""FastAPI Router for Razorpay Webhook Ingestion, Signature Verification & Idempotent Processing."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from ..config import get_settings
from ..schemas.enums import CaseStatus, TruthProvenance
from ..schemas.case import VerificationRecord
from ..database import get_db_session
from ..repositories.case_repository import CaseRepository
from ..repositories.audit_repository import AuditRepository
from ..services.audit_service import AuditService
from ..services.razorpay_service import RazorpayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Handle incoming Razorpay webhooks with signature verification and idempotent deduplication.

    Supported events:
    - payment_link.paid
    - payment.captured
    - invoice.paid
    """
    settings = get_settings()
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8")

    # 1. Signature Verification
    if settings.razorpay_webhook_secret:
        if not x_razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Razorpay-Signature header.",
            )
        rzp_service = RazorpayService()
        is_valid = rzp_service.verify_webhook_signature(
            body=body_text,
            signature=x_razorpay_signature,
            secret=settings.razorpay_webhook_secret,
        )
        if not is_valid:
            logger.warning("Rejected Razorpay webhook with invalid signature.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature.",
            )

    # 2. Parse Webhook Payload
    try:
        payload = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in webhook payload.",
        )

    event_name = payload.get("event", "unknown")
    event_id = payload.get("id") or payload.get("event_id") or f"evt_{hash(body_text)}"
    case_repo = CaseRepository(session)
    audit_repo = AuditRepository(session)
    audit_svc = AuditService(session)

    # 3. Extract Entity Details & Associated Case ID
    entity_payload = payload.get("payload", {})
    case_id: Optional[str] = None
    paid_amount: Optional[float] = None

    # Check for payment_link or payment entities
    if "payment_link" in entity_payload:
        plink_entity = entity_payload["payment_link"].get("entity", {})
        notes = plink_entity.get("notes", {})
        case_id = notes.get("case_id")
        if not case_id:
            # Fallback search by reference_id / id
            case_id = plink_entity.get("reference_id")
        amt_paise = plink_entity.get("amount_paid") or plink_entity.get("amount")
        if amt_paise:
            paid_amount = float(amt_paise) / 100.0

    elif "payment" in entity_payload:
        payment_entity = entity_payload["payment"].get("entity", {})
        notes = payment_entity.get("notes", {})
        case_id = notes.get("case_id")
        amt_paise = payment_entity.get("amount")
        if amt_paise:
            paid_amount = float(amt_paise) / 100.0

    # 4. Deduplication Check (Idempotency)
    # Check if this webhook event was already recorded for this case
    if case_id:
        existing_audits = audit_repo.get_by_case_id(case_id)
        for a in existing_audits:
            det = a.details if isinstance(a.details, dict) else (json.loads(a.details) if isinstance(a.details, str) else {})
            if det.get("event_id") == event_id:
                logger.info("Ignoring duplicate webhook event '%s' for case '%s'.", event_id, case_id)
                return {
                    "status": "ignored_duplicate",
                    "event_id": event_id,
                    "event": event_name,
                }

    # 5. Process Payment Success Events
    verif_provenance = (
        TruthProvenance.LIVE_TEST_MODE_API_RESULT
        if settings.has_razorpay_credentials
        else TruthProvenance.MOCKED_TEST_RESULT
    )

    if event_name in ["payment_link.paid", "payment.captured", "invoice.paid"] and case_id:
        case = case_repo.get_by_id(case_id)
        if case and case.current_status != CaseStatus.VERIFIED_RECOVERED:
            recovered = paid_amount if paid_amount is not None else case.amount
            case.verified_recovered_amount = recovered
            case.current_status = CaseStatus.VERIFIED_RECOVERED
            case.verification_outcome = VerificationRecord(
                verified=True,
                status="PAID",
                verified_at=datetime.utcnow(),
                recovered_amount=recovered,
                verification_method="WEBHOOK_EVENT",
                details=f"Verified via Razorpay webhook '{event_name}' (event_id={event_id})",
                provenance=verif_provenance,
            )
            case_repo.save(case)

            audit_svc.log_event(
                case_id=case.id,
                event_type="CASE_RECOVERED",
                actor="RAZORPAY_WEBHOOK",
                previous_status=CaseStatus.ACTION_IN_PROGRESS,
                new_status=CaseStatus.VERIFIED_RECOVERED,
                details={
                    "event": event_name,
                    "event_id": event_id,
                    "verified_recovered_amount": recovered,
                },
                provenance=verif_provenance,
            )
            logger.info("Case '%s' marked RECOVERED via webhook '%s' (₹%.2f).", case.id, event_name, recovered)

    # Log webhook ingestion audit under case_id
    if case_id:
        audit_svc.log_event(
            case_id=case_id,
            event_type="WEBHOOK_RECEIVED",
            actor="RAZORPAY_GATEWAY",
            previous_status=None,
            new_status=None,
            details={
                "event": event_name,
                "event_id": event_id,
                "matched_case_id": case_id,
            },
            provenance=verif_provenance,
        )

    return {
        "status": "processed",
        "event_id": event_id,
        "event": event_name,
        "matched_case_id": case_id,
    }

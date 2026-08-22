"""Razorpay Test Mode Integration Service.

Provides a clean, verified abstraction over the official Razorpay Python SDK.
- Used strictly in Razorpay TEST MODE for demo and live integration.
- Automated tests use mocked responses.
- Never represents mocked responses as LIVE_TEST_MODE_API_RESULT.
- Secrets remain server-side only.

OFFICIAL RAZORPAY TEST MODE API REGISTRY:
=============================================================================
1. Payment Link Creation:
   - Endpoint: POST https://api.razorpay.com/v1/payment_links
   - SDK Method: `client.payment_link.create(data)`
   - Purpose: Generates a standard hosted payment link for collecting payment.
   - Required Identifiers: `amount` (in paise), `currency`, `description`.
   - Test Mode Support: YES (capped at 30 links per business in test mode).

2. Payment Link Retrieval:
   - Endpoint: GET https://api.razorpay.com/v1/payment_links/:id
   - SDK Method: `client.payment_link.fetch(payment_link_id)`
   - Purpose: Verifies payment link status ('created', 'paid', 'expired', 'cancelled').
   - Required Identifiers: `payment_link_id` (e.g. 'plink_xxx').
   - Test Mode Support: YES.

3. Payment Status Retrieval:
   - Endpoint: GET https://api.razorpay.com/v1/payments/:id
   - SDK Method: `client.payment.fetch(payment_id)`
   - Purpose: Verifies transaction settlement status ('captured', 'failed', 'authorized').
   - Required Identifiers: `payment_id` (e.g. 'pay_xxx').
   - Test Mode Support: YES.

4. Subscription Retrieval:
   - Endpoint: GET https://api.razorpay.com/v1/subscriptions/:id
   - SDK Method: `client.subscription.fetch(subscription_id)`
   - Purpose: Inspects recurring subscription status ('active', 'pending', 'halted', 'cancelled').
   - Required Identifiers: `subscription_id` (e.g. 'sub_xxx').
   - Test Mode Support: YES.

5. Invoice Retrieval:
   - Endpoint: GET https://api.razorpay.com/v1/invoices/:id
   - SDK Method: `client.invoice.fetch(invoice_id)`
   - Purpose: Inspects recurring subscription invoice status ('paid', 'issued', 'expired').
   - Required Identifiers: `invoice_id` (e.g. 'inv_xxx').
   - Test Mode Support: YES.

6. Webhook Signature Verification:
   - Method: `client.utility.verify_webhook_signature(body, signature, secret)`
   - Purpose: Cryptographically validates incoming webhook authenticity via HMAC-SHA256.
   - Test Mode Support: YES.

EXPLICIT NON-APIS (NOT EXPOSED BY RAZORPAY):
-----------------------------------------------------------------------------
- No server-side "direct one-time payment retry API": Razorpay requires customer-facing
  authentication (AFA / OTP) for one-time transactions under RBI regulations.
- No standalone "mandate update link creation API": Updating payment instruments on
  subscriptions is performed via the Razorpay Customer Portal or checkout re-auth.
=============================================================================
"""

import logging
from typing import Any, Dict, Optional
import razorpay

from ..config import get_settings
from ..schemas.enums import TruthProvenance

logger = logging.getLogger(__name__)


class RazorpayService:
    """Service wrapper for Razorpay Test Mode APIs.

    Does NOT emulate or fake payment APIs.
    If credentials are not provided, is_configured is False and operations
    fail gracefully unless mocked in tests.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        settings = get_settings()
        self.key_id = key_id or settings.razorpay_key_id
        self.key_secret = key_secret or settings.razorpay_key_secret
        self.webhook_secret = webhook_secret or settings.razorpay_webhook_secret

        self._client: Optional[razorpay.Client] = None
        if self.key_id and self.key_secret:
            try:
                self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Razorpay Test Mode client initialized successfully.")
            except Exception as e:
                logger.warning("Failed to initialize Razorpay client: %s", e)
                self._client = None
        else:
            logger.info("Razorpay credentials not configured. Live API calls disabled.")

    @property
    def is_configured(self) -> bool:
        """True if valid Razorpay test mode credentials are provided."""
        return self._client is not None

    def create_payment_link(
        self,
        amount: float,
        currency: str = "INR",
        description: str = "Payment Recovery Link",
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_contact: Optional[str] = None,
        reference_id: Optional[str] = None,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a standard Razorpay Payment Link in Test Mode.

        Official API: POST https://api.razorpay.com/v1/payment_links
        Amount is specified in major units (e.g. INR) and converted to paise.
        """
        if not self.is_configured:
            raise RuntimeError(
                "Razorpay client not configured with valid test credentials."
            )

        # Convert to subunit (paise for INR)
        amount_subunit = int(round(amount * 100))

        payload: Dict[str, Any] = {
            "amount": amount_subunit,
            "currency": currency,
            "accept_partial": False,
            "description": description,
            "reference_id": reference_id or "",
            "reminder_enable": False,
            "notes": notes or {},
        }

        customer_dict: Dict[str, str] = {}
        if customer_name:
            customer_dict["name"] = customer_name
        if customer_email:
            customer_dict["email"] = customer_email
        if customer_contact:
            customer_dict["contact"] = customer_contact
        if customer_dict:
            payload["customer"] = customer_dict

        logger.info(
            "Creating Razorpay Test Mode payment link for amount %s %s (ref=%s)",
            amount,
            currency,
            reference_id,
        )
        response = self._client.payment_link.create(data=payload)
        return response

    def fetch_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        """Fetch details of a Razorpay Payment Link in Test Mode.

        Official API: GET https://api.razorpay.com/v1/payment_links/:id
        """
        if not self.is_configured:
            raise RuntimeError(
                "Razorpay client not configured with valid test credentials."
            )

        logger.info("Fetching Razorpay payment link: %s", payment_link_id)
        response = self._client.payment_link.fetch(payment_link_id)
        return response

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetch details of a specific payment transaction from Razorpay.

        Official API: GET https://api.razorpay.com/v1/payments/:id
        """
        if not self.is_configured:
            raise RuntimeError(
                "Razorpay client not configured with valid test credentials."
            )

        logger.info("Fetching Razorpay payment: %s", payment_id)
        response = self._client.payment.fetch(payment_id)
        return response

    def fetch_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Fetch subscription details from Razorpay in Test Mode.

        Official API: GET https://api.razorpay.com/v1/subscriptions/:id
        """
        if not self.is_configured:
            raise RuntimeError(
                "Razorpay client not configured with valid test credentials."
            )

        logger.info("Fetching Razorpay subscription: %s", subscription_id)
        response = self._client.subscription.fetch(subscription_id)
        return response

    def fetch_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Fetch invoice details from Razorpay in Test Mode.

        Official API: GET https://api.razorpay.com/v1/invoices/:id
        """
        if not self.is_configured:
            raise RuntimeError(
                "Razorpay client not configured with valid test credentials."
            )

        logger.info("Fetching Razorpay invoice: %s", invoice_id)
        response = self._client.invoice.fetch(invoice_id)
        return response

    def verify_webhook_signature(
        self, body: str, signature: str, secret: Optional[str] = None
    ) -> bool:
        """Verify Razorpay webhook signature using standard HMAC SHA256."""
        import hmac
        import hashlib

        effective_secret = secret or self.webhook_secret
        if not effective_secret or not signature:
            logger.warning("Cannot verify webhook signature: webhook secret or signature missing.")
            return False

        try:
            body_bytes = body.encode("utf-8") if isinstance(body, str) else body
            secret_bytes = effective_secret.encode("utf-8")
            expected_signature = hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.warning("Webhook signature verification failed: %s", e)
            return False

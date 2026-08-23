"""Integration Tests for FastAPI API Endpoints (Milestone 5).

Tests:
- /health
- /api/v1/cases/ingest (single & batch)
- /api/v1/cases (list & filters)
- /api/v1/cases/{case_id} (retrieval with audit trail)
- /api/v1/cases/{case_id}/process (LangGraph execution)
- /api/v1/batch/run (benchmark runner)
- /api/v1/metrics/batch (aggregate metrics)
- /api/v1/webhooks/razorpay (signature verification & idempotency)
"""

import hmac
import hashlib
import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db_session
from app.schemas.enums import CaseStatus, CaseType, FailureCategory, RecoveryStrategy, TruthProvenance
from app.schemas.case import RecoveryCase


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_case_dict():
    return {
        "id": "case_api_001",
        "case_type": "ONE_TIME_PAYMENT",
        "customer_id": "cust_api_100",
        "masked_customer_email": "api***@test.com",
        "masked_customer_phone": "+91 98*** **111",
        "amount": 2500.0,
        "currency": "INR",
        "gateway_reference_id": "pay_api_ref_001",
        "failure_code": "BANK_TIMEOUT",
        "failure_description": "Issuing bank timeout",
        "failure_category": "BANK_TIMEOUT_NETWORK",
        "attempts_count": 0,
        "max_attempts_allowed": 3,
        "current_status": "DETECTED",
        "provenance": "SYNTHETIC_DATA_RESULT",
    }


# ---------------------------------------------------------------------------
# Test: /health
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    """Health check must return 200 and runtime status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "version" in data


# ---------------------------------------------------------------------------
# Test: /api/v1/cases/ingest
# ---------------------------------------------------------------------------

def test_ingest_single_case(client, sample_case_dict):
    """Single case ingestion via POST /api/v1/cases/ingest."""
    response = client.post("/api/v1/cases/ingest", json=sample_case_dict)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["ingested_count"] == 1
    assert "case_api_001" in data["case_ids"]


def test_ingest_batch_cases(client, sample_case_dict):
    """Batch case ingestion via POST /api/v1/cases/ingest."""
    case2 = dict(sample_case_dict, id="case_api_002", amount=4500.0)
    response = client.post("/api/v1/cases/ingest", json={"cases": [sample_case_dict, case2]})
    assert response.status_code == 201
    data = response.json()
    assert data["ingested_count"] == 2


def test_ingest_duplicate_case_idempotency(client, sample_case_dict):
    """Re-ingesting the same case ID must be idempotent and not create duplicate audit events."""
    # First ingestion
    res1 = client.post("/api/v1/cases/ingest", json=sample_case_dict)
    assert res1.status_code == 201

    # Second ingestion of the identical case
    res2 = client.post("/api/v1/cases/ingest", json=sample_case_dict)
    assert res2.status_code == 201

    # Verify total case count is 1
    list_res = client.get("/api/v1/cases")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # Verify audit trail contains exactly 1 CASE_INGESTED event
    detail_res = client.get("/api/v1/cases/case_api_001")
    assert detail_res.status_code == 200
    audit_trail = detail_res.json()["audit_trail"]
    ingested_events = [e for e in audit_trail if e["event_type"] == "CASE_INGESTED"]
    assert len(ingested_events) == 1, f"Expected 1 CASE_INGESTED event, found {len(ingested_events)}"


def test_process_duplicate_execution_audit_idempotency(client, sample_case_dict):
    """Re-processing an existing case must not produce duplicate CASE_INGESTED events."""
    client.post("/api/v1/cases/ingest", json=sample_case_dict)

    # First workflow execution
    proc1 = client.post("/api/v1/cases/case_api_001/process")
    assert proc1.status_code == 200

    # Second workflow execution
    proc2 = client.post("/api/v1/cases/case_api_001/process")
    assert proc2.status_code == 200

    # Verify audit trail contains exactly 1 CASE_INGESTED event
    detail_res = client.get("/api/v1/cases/case_api_001")
    assert detail_res.status_code == 200
    audit_trail = detail_res.json()["audit_trail"]
    ingested_events = [e for e in audit_trail if e["event_type"] == "CASE_INGESTED"]
    assert len(ingested_events) == 1, f"Expected 1 CASE_INGESTED event, found {len(ingested_events)}"


# ---------------------------------------------------------------------------
# Test: /api/v1/cases
# ---------------------------------------------------------------------------

def test_list_cases(client, sample_case_dict):
    """Listing cases with optional pagination and filters."""
    client.post("/api/v1/cases/ingest", json=sample_case_dict)
    response = client.get("/api/v1/cases?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert "total" in data
    assert len(data["cases"]) > 0


# ---------------------------------------------------------------------------
# Test: /api/v1/cases/{case_id}
# ---------------------------------------------------------------------------

def test_get_case_details_and_audit_trail(client, sample_case_dict):
    """Retrieve case by ID including full audit trail."""
    client.post("/api/v1/cases/ingest", json=sample_case_dict)
    response = client.get("/api/v1/cases/case_api_001")
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["id"] == "case_api_001"
    assert "audit_trail" in data
    assert len(data["audit_trail"]) > 0


def test_get_case_not_found(client):
    """Non-existent case ID returns 404."""
    response = client.get("/api/v1/cases/non_existent_case_999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: /api/v1/cases/{case_id}/process
# ---------------------------------------------------------------------------

def test_process_case_endpoint(client, sample_case_dict):
    """Executing recovery workflow via POST /api/v1/cases/{case_id}/process."""
    client.post("/api/v1/cases/ingest", json=sample_case_dict)
    response = client.post("/api/v1/cases/case_api_001/process")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["case_id"] == "case_api_001"
    assert "final_status" in data
    assert "audit_events" in data


def test_process_case_stream_endpoint(client, sample_case_dict):
    """Executing recovery workflow with real-time SSE step progress via GET /api/v1/cases/{case_id}/process/stream."""
    client.post("/api/v1/cases/ingest", json=sample_case_dict)
    response = client.get("/api/v1/cases/case_api_001/process/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE text stream events
    lines = response.text.strip().split("\n\n")
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    assert len(events) >= 5, f"Expected multiple SSE events, received {len(events)}"
    event_types = [e.get("event") for e in events]
    assert "start" in event_types
    assert "step_progress" in event_types
    assert "complete" in event_types

    # Verify step names in progress events
    step_keys = [e.get("step_key") for e in events if e.get("event") == "step_progress"]
    assert "detect_and_load" in step_keys
    assert "extract_evidence" in step_keys
    assert "diagnose" in step_keys
    assert "score_strategy" in step_keys
    assert "evaluate_policy" in step_keys


# ---------------------------------------------------------------------------
# Test: /api/v1/batch/run & /api/v1/metrics/batch
# ---------------------------------------------------------------------------

def test_run_batch_benchmark_endpoint(client):
    """Executing batch benchmark via POST /api/v1/batch/run."""
    response = client.post("/api/v1/batch/run", json={"seed": 42, "count": 60, "dataset_version": "v1.0"})
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "metrics" in data
    assert data["metadata"]["total_cases"] == 60
    assert "NO_ACTION" in data["metrics"]
    assert "RETRY_ONLY" in data["metrics"]
    assert "AI_REVENUE_RECOVERY_ORCHESTRATOR" in data["metrics"]


def test_get_batch_metrics_endpoint(client):
    """Retrieving aggregate metrics via GET /api/v1/metrics/batch."""
    # Ensure a batch has run
    client.post("/api/v1/batch/run", json={"seed": 42, "count": 60})
    response = client.get("/api/v1/metrics/batch")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "comparison_summary" in data


# ---------------------------------------------------------------------------
# Test: /api/v1/webhooks/razorpay
# ---------------------------------------------------------------------------

def test_webhook_signature_validation(client, sample_case_dict):
    """Webhook signature validation with valid vs invalid HMAC SHA256 signatures."""
    webhook_secret = "test_webhook_secret_123"

    payload_dict = {
        "event": "payment_link.paid",
        "id": "evt_webhook_001",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_webhook_001",
                    "amount": 250000,
                    "amount_paid": 250000,
                    "notes": {"case_id": "case_api_001"},
                }
            }
        },
    }
    raw_body = json.dumps(payload_dict)

    # Compute valid HMAC signature
    valid_sig = hmac.new(webhook_secret.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()

    with patch("app.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.razorpay_webhook_secret = webhook_secret
        mock_settings.return_value.has_razorpay_credentials = False

        # Ingest case first
        client.post("/api/v1/cases/ingest", json=sample_case_dict)

        # 1. Invalid signature -> 400 Bad Request
        res_invalid = client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": "invalid_sig_abc123", "Content-Type": "application/json"},
        )
        assert res_invalid.status_code == 400

        # 2. Valid signature -> 200 Processed
        res_valid = client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": valid_sig, "Content-Type": "application/json"},
        )
        assert res_valid.status_code == 200
        assert res_valid.json()["status"] == "processed"

        # 3. Verify case is marked RECOVERED
        case_res = client.get("/api/v1/cases/case_api_001")
        assert case_res.status_code == 200
        assert case_res.json()["case"]["current_status"] == "VERIFIED_RECOVERED"
        assert case_res.json()["case"]["verified_recovered_amount"] == 2500.0


def test_webhook_idempotency_duplicate_handling(client, sample_case_dict):
    """Duplicate webhook delivery must be detected and safely ignored."""
    payload_dict = {
        "event": "payment.captured",
        "id": "evt_duplicate_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_dup_001",
                    "amount": 250000,
                    "notes": {"case_id": "case_api_001"},
                }
            }
        },
    }
    raw_body = json.dumps(payload_dict)

    with patch("app.routers.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.razorpay_webhook_secret = None
        mock_settings.return_value.has_razorpay_credentials = False

        # First delivery -> Processed
        res1 = client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json"},
        )
        assert res1.status_code == 200
        assert res1.json()["status"] == "processed"

        # Second delivery (duplicate event) -> Ignored duplicate
        res2 = client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json"},
        )
        assert res2.status_code == 200
        assert res2.json()["status"] == "ignored_duplicate"

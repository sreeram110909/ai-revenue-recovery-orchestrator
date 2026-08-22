# Known System Limitations & Production Deployment Considerations

This document transparently records real engineering constraints, architectural boundaries, and environmental assumptions present in the current release of the **AI Revenue Recovery Orchestrator**.

---

## 1. State Persistence & Checkpointing

- **In-Memory LangGraph Checkpointer**:  
  The LangGraph state machine currently utilizes `InMemorySaver` for intra-execution workflow state checkpoints. While durable case states and append-only audit events are safely persisted to the database repository (`recovery_cases` and `audit_events` tables), in-flight interrupted graph executions cannot be resumed from an arbitrary middle node after a process restart without re-invoking from the ingested state.
- **Production Roadmap**: Migrate to LangGraph Postgres Checkpointer (`PostgresSaver`) for distributed, durable multi-worker checkpointing.

---

## 2. Database Backend

- **Local Development Fallback**:  
  In the absence of a configured `DATABASE_URL`, the application automatically initializes a local SQLite file (`revenue_recovery.db`). 
- **Production Deployment**:  
  SQLite is single-writer and does not support high-concurrency connection pooling. Production environments must supply a PostgreSQL connection string (`postgresql+psycopg://user:password@host:5432/dbname`) using the pre-configured SQLAlchemy / Alembic migration framework.

---

## 3. Evaluation Benchmark & Data Provenance

- **Synthetic Dataset**:  
  The 60-case canonical benchmark dataset (`data/evaluations/datasets/recovery_dataset_v1_seed42.json`) is deterministically generated under `seed=42`. It represents a realistic heterogeneous distribution of one-time and subscription payment failures designed for zero PII exposure and reproducible comparison, rather than live production merchant telemetry.
- **Offline Gateway Verification**:  
  During batch benchmark execution, payment gateway responses are simulated using deterministic ground-truth scenarios to prevent real credit card charges, transaction fees, and third-party rate limiting during evaluation runs.

---

## 4. Payment Gateway Scope & Direct Retries

- **Regulatory & Gateway Constraints (AFA / 3DS Mandates)**:  
  Under Reserve Bank of India (RBI) regulations, direct server-side auto-debit for one-time card payments without customer authentication is disallowed. The orchestrator accurately models `SMART_RETRY` as an orchestration strategy rather than a fabricated payment gateway direct-debit API.
- **Action Realism**:  
  Direct execution is supported via hosted Razorpay Payment Links (`PAYMENT_LINK`), customer payment method update requests (`UPDATE_PAYMENT_METHOD`), and compliant subscription invoice retries (`SUBSCRIPTION_RETRY`).

---

## 5. Gateway Webhook Integration

- **Test Fixture Validation**:  
  Webhook HMAC-SHA256 signature verification, replay protection, and idempotency handling were validated using cryptographically signed test event payloads (`backend/tests/test_webhooks.py`).
- **Live Ingestion Prerequisite**:  
  Live Razorpay webhook delivery from the Razorpay dashboard requires deploying the FastAPI server to a publicly accessible HTTPS endpoint or configuring an SSL tunnel (e.g. ngrok).

---

## 6. Large Language Model Boundaries

- **Diagnostic Isolation**:  
  Gemini (`gemini-2.5-flash`) is strictly isolated to the diagnostic layer for failure classification and explanation. It does not execute actions or access payment gateway credentials.
- **Deterministic Heuristic Fallback**:  
  When `GEMINI_API_KEY` is not provided or rate limits are encountered, the system gracefully falls back to deterministic rule-based error classification, ensuring zero downtime and 100% policy compliance.

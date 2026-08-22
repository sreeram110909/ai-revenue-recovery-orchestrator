# AI Revenue Recovery Orchestrator

> **Autonomous, policy-governed revenue recovery engine for failed payments and recurring subscription charges with auditable execution, deterministic guardrails, and verified revenue tracking.**
> 
> *Track: AI Revenue Recovery | Razorpay AI Buildathon 2026*

---

## 1. Important Runtime Notice (Google AI Studio Preview vs. Exported Environment)

> [!IMPORTANT]
> **Google AI Studio Runtime Limitation**:
> The standard Google AI Studio container runs a Node.js/TypeScript frontend harness and does not have the pre-installed Python package management environment (`pip`, `uvicorn`, `langgraph`, `fastapi`). 
> 
> The backend architecture is strictly authored in **Python 3.11** using **FastAPI**, **Pydantic**, **LangGraph**, and **SQLAlchemy**. It is designed to be exported and run in any standard Python 3.11+ environment or container.

---

## 2. Core Architecture & Workflow

The orchestrator enforces strict separation between **AI reasoning** (bounded diagnosis, candidate strategy suggestion) and **deterministic governance** (hard policy engine vetoes, stopping rules, retry caps, escalation).

```
                      [ Failed Payment / Subscription Event ]
                                         │
                                         ▼
                               [ Ingestion Layer ]
                                         ↓
                                      Evidence
                                         ↓
                                     Diagnosis   ◄─── (Bounded LLM / Categorizer)
                                         ↓
                               Candidate Strategies
                                         ↓
                         Deterministic Strategy Scoring
                                         ↓
                                [ POLICY ENGINE ]  ◄─── Deterministic Guardrails
                                         │               (ALLOW / BLOCK / DOWNGRADE /
                        ┌────────────────┴────────────────┐ ESCALATE / STOP)
                        ▼                                 ▼
                   [ APPROVED ]               [ VETOED / ESCALATED / STOPPED ]
                        │                                 │
                        ▼                                 ▼
               [ Execution Layer ]             [ Escalation Queue / Stop ]
               (Razorpay Test Mode)                       │
                        │                                 │
                        ▼                                 │
              [ Verification Layer ]                      │
             (Re-verify Payment Status)                   │
                        │                                 │
                  ┌─────┴─────┐                           │
                  ▼           ▼                           │
                PAID        FAILED                        │
                  │           │                           │
                  ▼           ▼                           │
              RECOVERED   RETRY / STOP / ESCALATE         │
                  │           │                           │
                  └───────────┴─────────────────┬─────────┘
                                                ▼
                                        [ Audit Trail ]
                                  (Append-Only, Redacted PII)
                                                ↓
                                     [ Evaluation Engine ]
                              (Verified Recovered ₹ vs Baselines)
```

---

## 3. Scope & Locked Action Space

The scope is strictly locked to two workflows:

1. **Primary Workflow: Failed Payment Recovery**
   - Allowed Actions: `SMART_RETRY`, `PAYMENT_LINK`, `HUMAN_ESCALATION`, `STOP`
2. **Secondary Workflow: Recurring Subscription Payment Recovery**
   - Allowed Actions: `SUBSCRIPTION_RETRY`, `UPDATE_PAYMENT_METHOD`, `HUMAN_ESCALATION`, `STOP`

---

## 4. Setup & Running the Backend

### Prerequisites
- Python 3.11 or higher
- PostgreSQL (or local SQLite for development testing)
- A valid Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/))
- Razorpay Test Mode API keys (optional; mocked responses used if not provided)

### Step 1: Clone or Export the Repository
```bash
# In your terminal
cd backend
```

### Step 2: Create and Activate a Python Virtual Environment
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r ../requirements.txt
```

### Step 4: Configure Environment Variables
```bash
cp ../.env.example .env
# Edit .env and supply your GEMINI_API_KEY and RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET
```

### Step 5: Run Database Migrations (Optional for dev)
```bash
# If using PostgreSQL:
alembic upgrade head
```

### Step 6: Start the FastAPI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive OpenAPI documentation will be accessible at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 5. Running the Test Suite

The test suite validates the deterministic Policy Engine, Strategy Scoring, Prompt-Injection defenses, and End-to-End Recovery loops.

```bash
# Run all tests with pytest
pytest -v

# Run only the deterministic policy engine test suite
pytest tests/test_policy_engine.py -v

# Run with test coverage report
pytest --cov=app tests/
```

---

## 6. Directory Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI Application Entry & Route Mounts
│   ├── config.py                # Pydantic Settings & Environment Loader
│   ├── models/                  # SQLAlchemy Relational Models
│   │   ├── __init__.py
│   │   ├── case.py              # RecoveryCase DB Model
│   │   ├── action.py            # ActionExecution DB Model
│   │   ├── policy.py            # PolicyEvaluation DB Model
│   │   └── audit.py             # AuditLog DB Model
│   ├── schemas/                 # Pydantic Schemas & Domain Enums
│   │   ├── __init__.py
│   │   ├── enums.py             # CaseType, RecoveryStrategy, FailureCategory, CaseStatus
│   │   ├── case.py              # RecoveryCase Ingestion & Response Schemas
│   │   ├── policy.py            # PolicyConfig, PolicyCheckResult Schemas
│   │   ├── action.py            # ActionExecutionRecord, VerificationRecord Schemas
│   │   └── metrics.py           # BatchMetrics & Evaluation Schemas
│   ├── repositories/            # Typed Repository Abstractions (PostgreSQL / Memory)
│   │   ├── __init__.py
│   │   ├── case_repository.py
│   │   ├── audit_repository.py
│   │   └── policy_repository.py
│   ├── policies/                # 100% Deterministic Policy Engine (Pol-01 to Pol-08)
│   │   ├── __init__.py
│   │   ├── engine.py            # Deterministic PolicyEngine Class
│   │   └── rules.py             # Standalone Pure Rule Evaluators
│   ├── services/                # Business & External Integrations
│   │   ├── __init__.py
│   │   ├── decision_engine.py   # Multi-signal Mathematical Strategy Scoring
│   │   ├── diagnosis_service.py # Root-cause Classifier & Bounded Gemini LLM
│   │   ├── razorpay_service.py  # Razorpay Test Mode Client & Mock Runner
│   │   └── verification.py      # Gateway Status Reconciliation & Provenance Tagger
│   ├── agents/                  # LangGraph Stateful Recovery Workflow
│   │   ├── __init__.py
│   │   ├── state.py             # RecoveryGraphState Definition
│   │   └── workflow.py          # StateGraph (Detect->Diagnose->Decide->Guard->Act->Verify)
│   ├── audit/                   # Append-Only Audit Trail Service
│   │   ├── __init__.py
│   │   └── logger.py
│   ├── evaluation/              # Batch Benchmark & Baseline Comparison Engine
│   │   ├── __init__.py
│   │   ├── dataset.py           # 50+ Reproducible Synthetic Failure Batch
│   │   └── baselines.py         # No-Action vs Retry-Only vs Orchestrator
│   └── api/                     # FastAPI Route Controllers
│       ├── __init__.py
│       ├── cases.py             # Case CRUD & Single-Case Processing
│       ├── batch.py             # Batch Ingestion & Benchmark Runner
│       ├── webhooks.py          # Razorpay Idempotent Webhook Handler
│       └── metrics.py           # Metrics & Audit Trail Endpoints
└── tests/                       # Pytest Test Suite
    ├── __init__.py
    ├── conftest.py              # Pytest Fixtures & Test Data
    ├── test_policy_engine.py    # Policy Engine Isolation Tests
    ├── test_scoring.py          # Decision Scoring Determinism Tests
    ├── test_prompt_injection.py # Security & LLM Prompt Injection Tests
    └── test_orchestrator.py     # End-to-End Closed Loop Integration Tests
```

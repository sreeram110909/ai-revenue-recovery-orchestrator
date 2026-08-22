# AI Revenue Recovery Orchestrator

> **Autonomous, policy-governed revenue recovery engine for failed payments and recurring subscription charges with auditable execution, deterministic guardrails, and verified revenue tracking.**
> 
> *Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery*

---

## 1. Problem Statement

Payment failures in digital commerce and subscription businesses represent a massive leak in gross merchandise value (GMV). When a transaction fails, traditional recovery approaches fail merchants in two extreme ways:
1. **Dumb, Static Retries**: Blindly re-attempting failed charges on fixed schedules exhausts issuer attempt limits, triggers bank fraud algorithms, damages merchant standing, and wastes transaction fees on permanent errors (e.g. invalid mandate, expired card).
2. **Abandoned Carts & Manual Operations**: Merchants lack automated, compliant mechanisms to route recoverable failures to customer payment links or mandate updates, resulting in high involuntary churn.

---

## 2. Why This Matters

- **Involuntary Churn**: Over 30% of subscription cancellations are caused by unhandled transient payment failures, not intentional customer cancellations.
- **Regulatory Guardrails (RBI / AFA Mandates)**: In India, auto-debit regulations disallow arbitrary server-side card debits without Additional Factor Authentication (AFA/3DS). An orchestrator must intelligently navigate regulatory reality rather than pretending unsupported direct debit APIs exist.
- **Financial Safety**: Autonomous AI agents must never execute arbitrary or unvetted financial operations. Strategy recommendation must remain strictly separated from deterministic policy authorization.

---

## 3. Solution Overview

The **AI Revenue Recovery Orchestrator** is a production-minded system that combines:
- **Bounded Diagnostic AI**: Sanitized error categorization using Gemini (`gemini-2.5-flash`) to understand root causes without exposing sensitive customer PII or credentials.
- **Deterministic Strategy Scoring**: Multi-signal scoring weighting failure category, attempt history, transaction value, and customer tier.
- **Deterministic Policy Engine**: Hardcoded merchant safety guardrails (retry caps, cooldowns, amount ceilings, non-retryable blocks) with absolute veto power (`ALLOW`, `BLOCK`, `DOWNGRADE`, `ESCALATE`, `STOP`).
- **Idempotent Execution**: Razorpay Test Mode integration for hosted Payment Links, subscription retry lifecycles, and customer payment method update requests.
- **Verified Financial Accounting**: Revenue is credited **only** upon independent gateway settlement verification (`PAID` / `CAPTURED`).

---

## 4. System Architecture

```
                      [ Failed Payment / Subscription Event ]
                                         │
                                         ▼
                               [ Ingestion Layer ]
                                         ↓
                                      Evidence (PII Scrubbed)
                                         ↓
                                     Diagnosis   ◄─── Bounded Gemini LLM (or Heuristic Fallback)
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
             (Re-verify Gateway Status)                   │
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

## 5. Headline Benchmark Results

*Measured across a canonical 60-case deterministic synthetic evaluation dataset (`seed=42`) with zero live API quota consumption:*

| Metric | NO_ACTION Baseline | RETRY_ONLY Baseline | AI REVENUE RECOVERY ORCHESTRATOR | Net Uplift vs Retry Only |
|---|---|---|---|---|
| **Evaluated Cases** | `60` | `60` | `60` | — |
| **Total Revenue at Risk** | `₹5,21,769.70` | `₹5,21,769.70` | `₹5,21,769.70` | — |
| **Verified Recovered Revenue** | `₹0.00` | `₹51,765.46` | **₹1,12,529.40** | **+₹60,763.94** |
| **Revenue Recovery Rate** | `0.0%` | `9.9%` | **21.6%** | **+117.4% lift** |
| **Case Recovery Rate** | `0.0%` | `33.3%` (20/60) | **53.3%** (32/60) | **+60.0% case lift** |
| **Recovery Attempts** | `0` | `26` | **52** | — |
| **Successful Dispatches** | `0` | `20` | **44** | — |
| **Human Escalations** | `0` | `0` | **16** | — |
| **Policy Violations** | `0` | `0` | **0** (100% Authorized)| — |

> **Note on Data Provenance**: Benchmark values are derived from an immutable synthetic dataset (`data/evaluations/datasets/recovery_dataset_v1_seed42.json`, SHA-256: `741535b89fd6a558335268d8174eb5a9c6b2e4295fdadd4f0dd457d31724ae5c`). See [`docs/DATASET_AND_REPRODUCIBILITY.md`](docs/DATASET_AND_REPRODUCIBILITY.md) for full details.

---

## 6. Locked Scope & Supported Recovery Actions

### Primary Workflow: One-Time Failed Payment Recovery
- `SMART_RETRY`: Intelligent scheduled retry within policy cooldown.
- `PAYMENT_LINK`: Generates hosted Razorpay Payment Link dispatched to customer.
- `HUMAN_ESCALATION`: Routes high-value or ambiguous cases to human operations queue.
- `STOP`: Halts recovery permanently (terminal state, zero further actions).

### Secondary Workflow: Recurring Subscription Payment Recovery
- `SUBSCRIPTION_RETRY`: Compliant recurring invoice retry observing mandate status.
- `UPDATE_PAYMENT_METHOD`: Issues customer notification link to update expired/invalid mandate.
- `HUMAN_ESCALATION`: Routes high-value subscription failures to merchant relationship team.
- `STOP`: Halts subscription retry lifecycle permanently.

---

## 7. Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js v20+ and npm
- Valid Razorpay Test Mode keys (optional; mocked test mode operates automatically)
- Gemini API Key (optional; deterministic heuristic fallback operates automatically if unset)

### 1. Backend Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Start FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```
API Documentation will be live at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup
```bash
# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```
Dashboard will be live at `http://127.0.0.1:3000`.

---

## 8. Verification & Test Suites

```bash
# Run backend test suite (119 tests passing)
.venv/bin/pytest backend/tests/ -v

# Run frontend security, policy, and invariant suite (24 tests passing)
npm test

# Run TypeScript typecheck
npm run lint

# Run production build
npm run build
```

---

## 9. Local Setup & Troubleshooting

- **Google AI Studio Environment Notice**: When exporting or running outside Google AI Studio, ensure your local Python environment has packages from `requirements.txt` installed.
- **SQLite Fallback**: If `DATABASE_URL` is omitted, the application creates a local SQLite database (`revenue_recovery.db`). For production, supply a PostgreSQL connection URL.
- **Gemini Fallback**: If `GEMINI_API_KEY` is omitted, the orchestrator automatically uses deterministic error categorization with zero disruption to the workflow.

---

## 10. Documentation Index

- [`docs/DATASET_AND_REPRODUCIBILITY.md`](docs/DATASET_AND_REPRODUCIBILITY.md): Canonical dataset specification, checksum, and reproduction instructions.
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md): Transparent engineering constraints and production roadmap.
- [`docs/FEATURE_ENDPOINT_MATRIX.md`](docs/FEATURE_ENDPOINT_MATRIX.md): Complete mapping of UI controls to API endpoints.
- [`docs/FINAL_SYSTEM_QA_REPORT.md`](docs/FINAL_SYSTEM_QA_REPORT.md): Comprehensive system QA and validation report.
- [`docs/EVALUATOR_REVIEW.md`](docs/EVALUATOR_REVIEW.md): Objective architectural assessment.

---

## 11. License

MIT License. Copyright (c) 2026 Sreeram Banoth. See [`LICENSE`](LICENSE) for details.

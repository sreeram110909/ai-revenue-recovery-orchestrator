# Technical Evaluation & Architectural Assessment

**Target**: Razorpay AI Buildathon (Track 03 — AI Revenue Recovery)  
**System Evaluated**: AI Revenue Recovery Orchestrator  
**Document Purpose**: Objective technical assessment of architectural strengths, real-world constraints, and evaluative criteria.

---

## 1. Architectural Strengths & Differentiators

1. **Strict Separation of Diagnostic AI & Deterministic Policy Authorization**:
   - The LLM (`gemini-2.5-flash`) is bounded strictly to error classification and explanation.
   - Financial execution is 100% gated by a deterministic rule engine (`PolicyEngine`), ensuring that even if the AI hallucinates, no unauthorized financial transactions occur.
2. **True Verified Financial Accounting**:
   - Zero revenue is counted merely because a payment link was generated or an API call succeeded (`HTTP 200`).
   - Revenue recovery is verified exclusively upon confirmed gateway settlement (`PAID` / `CAPTURED`).
3. **Multi-Baseline Comparative Evaluation**:
   - Evaluates three isolated baselines (`NO_ACTION`, `RETRY_ONLY`, `AI_REVENUE_RECOVERY_ORCHESTRATOR`) against an identical 60-case canonical dataset.
   - Demonstrates a measured **+117.4% revenue lift** (+₹60,763.94) over static retries under zero policy violations.
4. **Append-Only Immutable Audit Trail**:
   - Every state transition, diagnosis, policy check, action dispatch, and gateway verification is recorded chronologically in an immutable log.

---

## 2. Identified Weaknesses & Production Gaps

1. **State Checkpointing Persistence**:
   - LangGraph `InMemorySaver` is process-local. While case states and audit events are durably saved to relational tables, in-flight interrupted graph executions must restart from the ingested state rather than an arbitrary mid-graph node upon process restart.
2. **Synthetic Evaluation Context**:
   - The 60-case benchmark is an offline synthetic dataset rather than live merchant telemetry, necessary for zero PII exposure and controlled testing.
3. **One-Time Direct Debit Constraints**:
   - Under RBI Additional Factor Authentication (AFA) mandates, direct server-side auto-debit for one-time payments cannot be automated without customer interaction. The system routes one-time payments to hosted Payment Links rather than faking an unsupported direct-debit API.

---

## 3. Likely Evaluator Questions & Responses

### Q1: "How do you prevent rogue LLM actions or financial leakage?"
**Response**: The LLM has zero tool access to payment APIs or credentials. Its output is a structured classification (`FailureCategory`) that feeds into deterministic strategy scoring. The deterministic `PolicyEngine` evaluates hardcoded merchant policies (retry caps, cooldowns, amount ceilings, non-retryable categories) before any execution request can reach `ExecutionService`.

### Q2: "Why report 21.6% revenue recovery rate when 53.3% of cases recovered?"
**Response**: We distinguish between **Revenue Recovery Rate** (amount-weighted: ₹112,529.40 / ₹521,769.70 = 21.6%) and **Case Recovery Rate** (count-weighted: 32 / 60 = 53.3%). Revenue recovery rate is the standard financial metric because recovering five ₹500 transactions does not equal recovering one ₹50,000 transaction.

### Q3: "How does the system handle gateway rate limits or transient outages?"
**Response**: The execution layer utilizes exponential backoff with jitter and strictly respects policy cooldown intervals. On unrecoverable gateway check errors, the system fails closed (zero revenue counted, case flagged for human review).

---

## 4. Live vs Mocked vs Synthetic Attribution Matrix

| Dimension | Classification | Description |
|---|---|---|
| **Payment Link Creation** | `LIVE_TEST_MODE` | Exercised against official Razorpay Test Mode API (`rzp_test_...`). |
| **Payment Status Polling** | `LIVE_TEST_MODE` | Real-time status polling of hosted test payment links. |
| **Diagnostic LLM** | `LIVE_RUNTIME` / `FALLBACK` | Live Gemini API inference with automatic deterministic heuristic fallback when unset or rate-limited. |
| **Batch Benchmark Gateway** | `MOCKED_TEST` | Simulated deterministic gateway verification during offline batch runs to prevent real charges and rate limiting. |
| **60-Case Evaluation Dataset** | `SYNTHETIC_DATA` | PII-free heterogeneous synthetic dataset (`seed=42`) with fixed ground-truth metadata. |
| **Server & UI Stack** | `LOCAL_RUNTIME` | FastAPI Python backend, SQLite dev database, React 19 / Vite frontend. |

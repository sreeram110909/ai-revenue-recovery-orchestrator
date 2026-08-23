# AI Revenue Recovery Orchestrator — Complete Project & Evaluation Guide

> **Document Type**: Comprehensive Project Assessment, Live Demo Guide, and End-to-End Execution Trace  
> **Repository**: [`sreeram110909/ai-revenue-recovery-orchestrator`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator)  
> **Buildathon Track**: Razorpay AI Buildathon — Track 03 (AI Revenue Recovery)  
> **Maturity Level**: Production-Inspired Student Buildathon Prototype  
> **Primary Source of Truth**: Repository Source Code (`backend/`, `src/`, `docs/`)

---

## 1. What the Project Proves

### A. Strongly Demonstrated (`LIVE VERIFIED` & `AUTOMATED VERIFIED`)
- **Deterministic Policy Supremacy**: Proves that a 100% deterministic Policy Engine can reliably intercept, downgrade, or veto non-compliant AI proposals (e.g. ₹31,415 transaction in `synth_v1.0_42_059` forced to `HUMAN_ESCALATION` with 0 policy violations).
- **Heterogeneous Failure Routing**: Proves that distinguishing between bank timeouts (retried), expired cards (payment links), and security blocks (human review) delivers higher recovery than blunt retry loops (+117.4% revenue lift).
- **Real-Time State Machine Streaming**: Proves that complex multi-agent LangGraph workflows can be streamed step-by-step over Server-Sent Events (SSE) to provide sub-second visual feedback (10 events over ~811ms).
- **Audit Immutability & Idempotency**: Proves that multi-agent pipelines can maintain an append-only audit trail and deduplicate duplicate webhook events and server restarts without state corruption.

### B. Partially Demonstrated (`IMPLEMENTED BUT INCOMPLETELY MEASURED`)
- **LLM Diagnostic Reasoning Accuracy**: While Gemini 2.5 Flash reliably diagnoses root causes in real-time and falls back gracefully when unconfigured, the repository does **not** evaluate standalone LLM token accuracy or F1 classification metrics as a separate benchmark.
- **Razorpay Test Mode Integration**: The SDK integration for payment links and webhooks is fully implemented and passes live signature checks, but end-to-end clearing relies on test-mode simulations rather than production banking switches.

### C. Not Demonstrated (`REQUIRES PRODUCTION / LIVE ENVIRONMENT`)
- **Live Production Fund Settlement**: Real money movement across actual acquiring bank switches.
- **Autonomous Multi-Channel Re-Engagement**: Direct customer messaging over WhatsApp, SMS, or interactive voice response (IVR) (currently generates hosted links).
- **Checkout Cart Abandonment**: Scope is strictly locked to post-gateway failed payment and subscription drops.

---

## 2. Known Limitations

1. **Synthetic & Offline Benchmark Scope**: The 60-case canonical dataset (`seed=42`) is synthetic and deterministic. While mathematically rigorous and reproducible, it does not reflect live production traffic variance.
2. **Test-Mode Financial Boundary**: Actions execute against Razorpay Test Mode APIs or deterministic mock stubs. No actual bank settlement occurs.
3. **Local Database Architecture**: Defaults to SQLite for local development. While SQLAlchemy provides PostgreSQL compatibility, multi-region distributed transactions and connection pooling are not provisioned out-of-the-box.
4. **Locked Action Spaces**: Supports 6 discrete recovery strategies (`SMART_RETRY`, `PAYMENT_LINK`, `SUBSCRIPTION_RETRY`, `UPDATE_PAYMENT_METHOD`, `HUMAN_ESCALATION`, `STOP`). Does not support dynamic custom strategy generation.
5. **No Standalone LLM Benchmark Metric**: System benchmarks evaluate business revenue uplift, not raw LLM token precision.

---

## 3. What We'd Build Next

1. **Multi-Channel Dispatch Integration (WhatsApp / SMS)**:
   - *Directly addresses Limitation 4*: Integrate Twilio or Gupshup WhatsApp APIs to deliver hosted Razorpay payment links directly to customer mobile devices with interactive reply buttons.
2. **Continuous LLM Diagnostic Benchmark Suite**:
   - *Directly addresses Limitation 5*: Implement a dedicated `test_llm_accuracy.py` test harness that benchmarks Gemini diagnosis classifications against a hand-annotated golden dataset of 500 bank error strings, computing precision, recall, and fallback rates.
3. **Distributed PostgreSQL & Redis State Storage**:
   - *Directly addresses Limitation 3*: Replace in-memory LangGraph state with Redis Checkpointers and deploy PostgreSQL connection pooling for production horizontal scale.
4. **Adaptive Machine Learning Cooldown Predictor**:
   - *Directly addresses Limitation 1*: Train an offline classifier on merchant transaction logs to predict the optimal retry hour (e.g. salary deposit dates) rather than using a static 4-hour cooldown.

---

## 4. Buildathon Judging Alignment

| Buildathon Criterion | Project Implementation Evidence | Specific Code Reference |
| :--- | :--- | :--- |
| **1. Problem Taste & Focus** | Identifies the exact structural flaw of modern payment recovery: blunt retries that trigger velocity blocks. Scopes two distinct workflows (One-Time vs. Subscriptions) with 7 canonical failure categories. | [`backend/app/schemas/enums.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/schemas/enums.py) |
| **2. Build Quality & Architecture** | Full-stack production-inspired prototype: LangGraph state machine, FastAPI async backend, Pydantic schemas, Tailwind CVA design system, and 125 passing Pytest tests. | [`backend/app/orchestrator/builder.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/orchestrator/builder.py), [`src/App.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/App.tsx) |
| **3. AI Judgment & Safety** | Bounded reasoning: Gemini diagnoses and proposes candidates, but a deterministic Policy Engine holds unilateral veto power over execution. Automated fallback prevents failure when Gemini is unconfigured. | [`backend/app/agents/diagnosis.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/agents/diagnosis.py), [`backend/app/policies/engine.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/policies/engine.py) |
| **4. Failure Recovery & Rigor** | Documented post-mortems for audit log duplication (`161b806`), test data contamination (`fc04480`), and fresh-clone startup seeding (`b8c135a`). Idempotent webhooks and append-only audit trail. | [`docs/FAILURES_AND_LESSONS.md`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/docs/FAILURES_AND_LESSONS.md) |

---

## 5. Live Demo Script (Step-by-Step Walkthrough)

*This script uses ONLY features verified working live in the browser.*

```
STEP 1: EXECUTIVE DASHBOARD
- Navigate to: http://localhost:3000/
- Point to: Verified Recovered Revenue (₹1,12,529.40), Case Recovery Rate (53.3%), and Net Uplift (+₹60,763.94 / +117.4%).
- Demonstrate: Click "Refresh" -> Watch spinning icon and green toast: "Dashboard refreshed at HH:MM:SS".

STEP 2: CASES EXPLORER
- Navigate to: "Cases" tab (http://localhost:3000/cases).
- Point to: Header showing 62 persisted recovery cases.
- Demonstrate: Type "case_api" into Search -> Table filters instantly to case_api_001 and case_api_002.
- Filter: Select "Subscription" in Workflow dropdown -> Filters to subscription cases. Clear filters.

STEP 3: SINGLE CASE RECOVERY & REAL-TIME STREAMING
- Click: Open "case_api_001" (One-Time Bank Timeout, ₹2,500.00, Status: DETECTED).
- Point to: Honest placeholder in "What Happened?": "Pending diagnosis" / "Awaiting policy evaluation".
- Click: "Process with LangGraph" -> Live Progress Modal opens.
- Watch: Real-time SSE stream pulses each node (Ingestion -> Scrubbing -> Diagnosis -> Scoring -> Policy -> Dispatch -> Verification).
- Outcome: Case status transitions to "RETRY_SCHEDULED" with 10 chronological audit events.

STEP 4: POLICY OVERRIDE SHOWCASE
- Click: Back to Cases -> Open "synth_v1.0_42_059" (High Value Subscription, ₹31,415.20).
- Point to: Policy Panel -> Explain that Gemini recommended SUBSCRIPTION_RETRY, but Policy rule POL-02 triggered because amount exceeds ₹15,000 ceiling.
- Outcome: Forced to HUMAN_ESCALATION with zero automated debit.

STEP 5: BENCHMARK REPRODUCIBILITY
- Navigate to: "Benchmark" tab (http://localhost:3000/evaluation).
- Point to: 3-way comparison matrix (No Action vs Retry Only vs AI Orchestrator).
- Demonstrate: Click "Run with settings" -> Change seed to 7, count to 80 -> Click "Run with settings".
- Watch: Dynamic banner, subtitle updates to 80 cases, and recovery funnel recalculates dynamically.
- Reset: Click "Re-run benchmark" to return to canonical seed=42 benchmark.
```

---

## 6. "What Happens When I Click..." Trace Guide

### 1. Dashboard "Refresh" Button
- **User Action**: Clicks "Refresh" in Dashboard header.
- **Frontend Handler**: [`Dashboard.tsx:handleRefreshAll()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/Dashboard.tsx#L39-L50) sets `isRefreshing = true`.
- **API Requests**: Executes `Promise.all([api.getBatchMetrics(), api.getCases({ limit: 5 })])`.
- **Backend Handlers**: `GET /api/v1/metrics/batch` and `GET /api/v1/cases?limit=5`.
- **Backend Service**: [`EvaluationRepository.get_latest_run()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/repositories/evaluation_repository.py) and [`CaseRepository.get_all(limit=5)`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/repositories/case_repository.py).
- **Database Mutation**: None (Read-only query).
- **UI Update**: `metrics` state updates, `isRefreshing` becomes `false`, dismissible green toast renders with timestamp.

### 2. Cases Page Search Input & Filters
- **User Action**: Types into search bar or selects "Bank Timeout" dropdown.
- **Frontend Handler**: [`CaseTable.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/CaseTable.tsx#L19-L39) updates `searchTerm` or `selectedCategory` state.
- **API Requests**: None (Zero network call).
- **Client Processing**: `useMemo` filters the in-memory `cases` array.
- **UI Update**: Table re-renders with matching subset; counter displays `"Showing X of 62 cases"`.

### 3. Case Row Click
- **User Action**: Clicks a table row on the Cases page.
- **Frontend Handler**: [`App.tsx:handleSelectCase(id)`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/App.tsx) sets `selectedCaseId` and changes `activeTab` to `'case-view'`.
- **API Request**: [`useCase.ts:fetchCase()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/hooks/useCase.ts#L15-L34) calls `GET /api/v1/cases/{id}`.
- **Backend Handler**: [`backend/app/routers/cases.py:get_case()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/cases.py#L148-L182).
- **Backend Service**: `CaseRepository.get_by_id()` and `AuditRepository.get_by_case_id()`.
- **UI Update**: Case detail view renders with populated status badge, "What Happened?" panel, and audit history.

### 4. "Process with LangGraph" Button
- **User Action**: Clicks "Process with LangGraph" on Case Detail page.
- **Frontend Handler**: [`useCase.ts:processCaseStream()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/hooks/useCase.ts#L55-L140) sets `processing = true` and opens SSE modal.
- **API Request**: `GET /api/v1/cases/{id}/process/stream` (`text/event-stream`).
- **Backend Service**: [`WorkflowNodes`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/orchestrator/nodes.py) executes 9-node LangGraph pipeline sequentially.
- **Database Mutation**: Updates `recovery_cases` with new status, execution record, and verification outcome; inserts 10 `audit_log` records.
- **UI Update**: Active step dot pulses sky-blue; completed dots turn emerald; modal shows completion status and refreshes audit trail.

### 5. Benchmark "Run with settings"
- **User Action**: Inputs `seed=7, count=80` and clicks "Run with settings".
- **Frontend Handler**: [`Evaluation.tsx:handleRunCustomBenchmark()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/Evaluation.tsx#L23-L34).
- **API Request**: `POST /api/v1/batch/run` with body `{"seed": 7, "count": 80, "dataset_version": "v1.0"}`.
- **Backend Service**: [`BatchEvaluationRunner.run_benchmark()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/eval/runner.py) executes 80 cases across 3 strategies.
- **Database Mutation**: Inserts new record into `evaluation_runs` and 240 rows into `evaluation_case_results`.
- **UI Update**: Header updates to `"80 recovery cases · Seed 7"`, recovery funnel recalculates, and notification banner appears.

### 6. Razorpay Webhook Ingestion
- **Incoming Event**: Gateway delivers `POST /api/v1/webhooks/razorpay` with `X-Razorpay-Signature`.
- **Backend Router**: [`backend/app/routers/webhooks.py:handle_razorpay_webhook()`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/webhooks.py).
- **Security Check**: `RazorpayService.verify_webhook_signature()` verifies HMAC-SHA256 signature.
- **Idempotency Check**: Verifies `event_id` is not in cache (if duplicate, returns 200 `"duplicate_ignored"`).
- **Database Mutation**: Transitions `recovery_cases` to `VERIFIED_RECOVERED`, updates `verified_recovered_amount`, inserts `CASE_RECOVERED` and `WEBHOOK_RECEIVED` audit records.
- **UI Update**: On next case query, case displays `VERIFIED_RECOVERED` badge with full recovery amount.

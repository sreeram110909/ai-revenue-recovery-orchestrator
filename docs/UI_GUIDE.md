# Frontend Design & User Interface Guide

> **Document Type**: Code-Grounded User Interface & Frontend Design Guide  
> **Repository**: [`sreeram110909/ai-revenue-recovery-orchestrator`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator)  
> **Buildathon Track**: Razorpay AI Buildathon — Track 03 (AI Revenue Recovery)  
> **Maturity Level**: Production-Inspired Student Buildathon Prototype  
> **Primary Source of Truth**: Frontend Source Files (`src/pages/`, `src/components/`, `src/hooks/`, `src/services/`)

---

## 1. Frontend Architecture

### Technology Stack & Component Structure
- **Framework**: React 19 (`react: ^19.0.1`, `react-dom: ^19.0.1`) with TypeScript (`~5.8.2`) and Vite 6 (`vite: ^6.2.3`).
- **Styling Engine**: Modern slate-themed design system using Tailwind CSS 4 (`@tailwindcss/vite: ^4.1.14`, `tailwindcss: ^4.1.14`), `clsx`, and `tailwind-merge`.
- **Badge Primitive**: Custom Class Variance Authority (`class-variance-authority: ^0.7.1`) implementation in [`src/components/ui/badge.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/ui/badge.tsx).
- **Icons**: Lucide React (`lucide-react: ^0.546.0`).

### Architecture Diagram
```
src/
├── App.tsx                     # Top-level tab navigation & global layout
├── services/
│   └── api.ts                  # Centralized Fetch API client with ApiError handling
├── hooks/
│   ├── useMetrics.ts           # Benchmark runs & batch metrics fetching
│   ├── useCases.ts             # Paginated recovery cases list querying
│   └── useCase.ts              # Single case retrieval & SSE workflow streaming
├── components/
│   ├── ui/badge.tsx            # CVA badge component primitive
│   ├── StatusBadge.tsx         # Domain-aware 6-variant status badge
│   ├── CaseTable.tsx           # Searchable, filterable in-memory data grid
│   ├── DecisionTimeline.tsx    # 7-step LangGraph visual state machine
│   ├── PolicyPanel.tsx         # Policy evaluation breakdown & rule inspection
│   └── StrategyScoreTable.tsx  # Ranked strategy signals & score breakdown
└── pages/
    ├── Dashboard.tsx           # Executive recovery metrics & baseline lift
    ├── Cases.tsx               # Persisted recovery cases explorer
    ├── CaseView.tsx            # Case detail, SSE streaming modal & audit trail
    └── Evaluation.tsx          # 3-way benchmark runner & funnel breakdown
```

### Loading, Error, and Empty State Patterns
1. **Loading State**: Uses spinning Lucide icons (`<RefreshCw className="animate-spin" />`) with dedicated skeleton text (`"Loading recovery metrics..."`, `"Loading case details..."`).
2. **Error State**: Displays isolated slate-900/40 rounded error cards with descriptive error messages, error boundary isolation, and explicit **"Retry Connection"** action buttons.
3. **Empty State**: Tables and search grids render dedicated empty containers (`"No matching recovery cases found"`) with quick-action clear-filter buttons.

---

## 2. Dashboard Walkthrough

The Dashboard ([`src/pages/Dashboard.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/Dashboard.tsx)) provides executive-level visibility into financial recovery performance.

```
┌────────────────────────────────────────────────────────────────────────┐
│ TOP BANNER: Environment Status (FastAPI Backend + SQLite/Postgres)     │
├────────────────────────────────────────────────────────────────────────┤
│ HERO METRICS CARDS:                                                    │
│ 1. Verified Recovered Revenue (₹1,12,529.40) [Server: orchMetrics]     │
│ 2. Revenue Recovery Rate (21.6%)             [Server: orchMetrics]     │
│ 3. Case Recovery Rate (53.3% - 32/60 cases)  [Client Derivation]       │
│ 4. Net Revenue Uplift (+₹60,763.94 / +117.4%)[Server: comparison]      │
├────────────────────────────────────────────────────────────────────────┤
│ OPERATIONAL CARDS:                                                     │
│ - Revenue at Risk (₹5,21,769.70)             - Recovery Attempts (52)  │
│ - Successful Dispatches (44 / 73.3%)         - Human Escalations (16)  │
│ - Policy Violations (0 - 100% Authorized)                              │
├────────────────────────────────────────────────────────────────────────┤
│ 3-WAY BENCHMARK COMPARISON TABLE (No Action vs Retry Only vs AI Orch)  │
├────────────────────────────────────────────────────────────────────────┤
│ RECOVERY FUNNEL & OUTCOME DISTRIBUTION PANELS                          │
├────────────────────────────────────────────────────────────────────────┤
│ RECENT CASES PREVIEW (Top 5 persisted cases with quick-open drawer)   │
└────────────────────────────────────────────────────────────────────────┘
```

### Metrics Inventory & Data Origin (Server vs. Client-Side)

| UI Metric Card | Displayed Value (Canonical `seed=42`) | Data Origin | Source Expression in Code |
| :--- | :--- | :---: | :--- |
| **Verified Recovered Revenue** | `₹1,12,529.40` | **Server** | `orchMetrics.verified_recovered_revenue` |
| **Revenue Recovery Rate** | `21.6%` | **Server** | `orchMetrics.revenue_recovery_rate * 100` |
| **Case Recovery Rate** | `53.3%` | **Server** | `orchMetrics.case_recovery_rate * 100` |
| **Recovered Cases Count** | `32 / 60 cases` | **Client** | `Math.round(case_recovery_rate * totalCases)` |
| **Net Revenue Uplift** | `+₹60,763.94` (`+117.4%`) | **Server** | `comparison.orchestrator_absolute_lift`, `relative_lift_pct` |
| **Revenue at Risk** | `₹5,21,769.70` | **Server** | `orchMetrics.total_revenue_at_risk` |
| **Recovery Attempts** | `52` | **Server** | `orchMetrics.recovery_attempts` |
| **Successful Dispatches** | `44` (`73.3%`) | **Client** | `orchMetrics.successful_actions`, `(actions / total) * 100` |
| **Human Escalations** | `16` (`26.7%`) | **Client** | `orchMetrics.human_escalations`, `(escalations / total) * 100`|
| **Policy Violations** | `0 (100% Authorized)` | **Server** | `orchMetrics.policy_violations` |
| **Other / Closed Cases** | `12 cases` (`20.0%`) | **Client** | `totalCases - recoveredCount - humanEscalations` |

### Refresh Action & Notification Toast
Clicking the header **"Refresh"** button executes `handleRefreshAll()`, which calls `refetchMetrics()` and `refetchCases()` concurrently in `Promise.all`. While fetching, the refresh icon spins. Upon completion, a green banner appears: `"Dashboard refreshed at 03:31:22 PM (Metrics & recent cases synchronized)."`, which auto-dismisses on close.

---

## 3. Cases Page Walkthrough

The Cases Explorer ([`src/pages/Cases.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/Cases.tsx)) provides a searchable table of all persisted failure cases.

### Search and Filtering (`CLIENT-SIDE`)
As implemented in [`src/components/CaseTable.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/CaseTable.tsx#L24-L39), filtering operates in-memory over the fetched 62 cases using a React `useMemo` pipeline:
- **Free-Text Search**: Matches against `id`, `customer_id`, `failure_code`, or `masked_customer_email`.
- **Workflow Filter**: Dropdown filtering by `ONE_TIME_PAYMENT` or `SUBSCRIPTION_RECURRING`.
- **Issue Filter**: Dropdown filtering by `BANK_TIMEOUT_NETWORK`, `EXPIRED_INSTRUMENT`, `INSUFFICIENT_FUNDS`, `MANDATE_EXPIRED_INVALID`, `RISK_SECURITY_BLOCK`, or `AUTHENTICATION_OTP_FAILURE`.
- **Status Filter**: Dropdown filtering by `DETECTED`, `DIAGNOSED`, `POLICY_EVALUATED`, `ACTION_COMPLETED`, `VERIFIED_RECOVERED`, `ESCALATED`, `STOPPED`, etc.

### Table Columns
1. **Case ID & Workflow**: Displays case ID with workflow subtitle tag.
2. **Customer**: Shows customer ID, segment pill (`STANDARD`, `VIP`), and masked email.
3. **Issue & Root Cause**: Displays failure code and category description.
4. **Amount at Risk**: Formatted INR currency.
5. **Attempts**: Progress pill (e.g. `1/3` attempts used).
6. **Status**: Rendered using [`StatusBadge`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/StatusBadge.tsx).
7. **Action**: View details arrow triggering `onSelectCase(c.id)`.

---

## 4. Case Detail Walkthrough

The Case Detail page ([`src/pages/CaseView.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/CaseView.tsx)) provides deep inspection into a single transaction's recovery journey.

### 1. "What Happened?" Executive Summary Panel
Provides a three-step narrative summary of the failure:
- **1. Payment Failed**: Displays failure code, category, and attempt counts.
- **2. AI Suggested**: Displays AI recommendation. On unprocessed cases (`DETECTED`), renders an honest placeholder: `<span className="text-slate-500 italic">Pending diagnosis</span>` (resolving the prior hardcoded fallback bug).
- **3. Policy Decision**: Displays Policy outcome. On unprocessed cases, renders: `<span className="text-slate-500 italic">Awaiting policy evaluation</span>`.

### 2. The 7-Step Decision Flow ([`DecisionTimeline.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/DecisionTimeline.tsx))
Visualizes the LangGraph state machine with color-coded node dots:
- `bg-emerald-500` (Completed)
- `bg-sky-400 ring-4 ring-sky-500/30 animate-pulse` (In Progress during real-time streaming)
- `bg-slate-800` (Pending)

| Step Key | Title | Description when Completed |
| :--- | :--- | :--- |
| `detect_and_load` | **1. Ingestion & Detection** | Failure code and categorized category details. |
| `extract_evidence` | **2. Evidence Scrubbing** | Sanitized metadata with PII redaction confirmation. |
| `diagnose` | **3. Gemini Diagnosis** | Diagnostic narrative and root-cause classification. |
| `score_strategy` | **4. Strategy Scoring** | Recommended strategy selected from candidate score matrix. |
| `evaluate_policy` | **5. Policy Engine Evaluation** | Rule check outcome (`ALLOW`, `DOWNGRADE`, `ESCALATE`, `STOP`). |
| `execute_action` | **6. Action Dispatch** | Execution status (`Payment Link Created`, `Retry Scheduled`, etc.). |
| `verify_outcome` | **7. Gateway Verification** | Verified settlement amount or pending status. |

### 3. Policy & Strategy Deep Dives
- **Policy Engine Panel ([`PolicyPanel.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/PolicyPanel.tsx))**: Inspects every evaluated rule (`POL-01` through `POL-06`), pass/fail badges, and rule evaluation rationales.
- **Strategy Ranking Table ([`StrategyScoreTable.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/StrategyScoreTable.tsx))**: Inspects signal contribution scores (Base, Category Weight, Attempt Adjustment, Amount Tier, Diagnosis Boost).
- **Raw Audit Trail**: Chronological event table displaying timestamp, actor, event type, previous/new status, and details JSON.

---

## 5. Real-Time Server-Sent Events (SSE) Streaming

### Synchronous vs. Streaming Endpoints
- **Synchronous (`POST /api/v1/cases/{id}/process`)**: Runs the entire LangGraph workflow synchronously on the backend, returning the full resolved case and audit logs in a single HTTP response.
- **Streaming (`GET /api/v1/cases/{id}/process/stream`)**: Executes the workflow node-by-node, yielding individual SSE frames over an active HTTP text stream (`text/event-stream`).

### SSE Event Payload Schema
Each frame emitted by the backend matches the following JSON structure:
```json
{
  "type": "step_progress",
  "step_index": 3,
  "total_steps": 7,
  "step_key": "diagnose",
  "step_title": "Gemini Diagnosis",
  "status": "in_progress",
  "message": "Analyzing failure context with Gemini...",
  "case_status": "DETECTED",
  "payload": { "failure_category": "BANK_TIMEOUT_NETWORK" }
}
```

### Client-Side Lifecycle & Safeguards in [`useCase.ts`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/hooks/useCase.ts#L55-L140)
1. **Active Step Animation**: Updates `activeStepKey` and `completedStepKeys` in real-time, pulsing the active step in `DecisionTimeline`.
2. **15-Second Fallback Reconciliation Timeout**: If network latency interrupts the SSE connection, an automatic 15-second safety timer falls back to fetching `GET /api/v1/cases/{id}`, resolving the modal cleanly without leaving the UI hung.
3. **Duplicate Trigger Guard**: A boolean `processing` lock prevents firing multiple concurrent process requests on the same case.
4. **Observed Timing**: In live browser QA sweeps, a full 10-event streaming run completed in **811.6ms**, with each discrete step updating at ~84ms intervals.

---

## 6. Evaluation Page Walkthrough

The Benchmark page ([`src/pages/Evaluation.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/Evaluation.tsx)) provides proof of measured financial uplift.

```
┌────────────────────────────────────────────────────────────────────────┐
│ HEADER: Benchmark Title · Total Cases · Seed · Synthetic Provenance    │
├────────────────────────────────────────────────────────────────────────┤
│ CONTROLS: "Settings" (Seed & Count input) | "Re-run benchmark" button  │
├────────────────────────────────────────────────────────────────────────┤
│ 3-WAY COMPARATIVE MATRIX:                                              │
│ - NO_ACTION Baseline          (₹0.00 recovered, 0.0% rate)             │
│ - RETRY_ONLY Baseline         (₹51,765.46 recovered, 9.9% rate)        │
│ - AI REVENUE RECOVERY ORCH.   (₹1,12,529.40 recovered, 21.6% rate)     │
│ - NET UPLIFT                  (+₹60,763.94 / +117.4% revenue lift)     │
├────────────────────────────────────────────────────────────────────────┤
│ RECOVERY FUNNEL (Dynamic bars: Evaluated → Dispatched → Recovered)     │
├────────────────────────────────────────────────────────────────────────┤
│ METADATA ACCORDION & 180-ROW PER-CASE BREAKDOWN ACCORDION              │
└────────────────────────────────────────────────────────────────────────┘
```

### Action Controls
- **"Re-run benchmark"**: Triggers `POST /api/v1/batch/run` with default canonical parameters (`seed=42, count=60`).
- **"Run with settings"**: Opens a sliding config drawer allowing evaluators to specify custom integer seeds (e.g. `seed=7`) and sample counts (e.g. `count=80`), dynamically updating all headers, metrics, and funnel bars.

---

## 7. Status Badge System

The `StatusBadge` component ([`src/components/StatusBadge.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/StatusBadge.tsx)) maps every backend domain enum to one of 6 curated Class Variance Authority variants:

| Variant | Dot Color | Badge Class Styles | Supported Status Values |
| :--- | :--- | :--- | :--- |
| **`emerald`** | `bg-emerald-500` | Border emerald-500/30, bg-emerald-500/10, text-emerald-400 | `VERIFIED_RECOVERED`, `ALLOW`, `PAID`, `CAPTURED`, `SUCCESS` |
| **`amber`** | `bg-amber-500` | Border amber-500/30, bg-amber-500/10, text-amber-400 | `ESCALATED`, `ESCALATE`, `HUMAN_ESCALATION` |
| **`rose`** | `bg-rose-500` | Border rose-500/30, bg-rose-500/10, text-rose-400 | `BLOCK`, `STOPPED`, `STOP`, `FAILED`, `CLOSED_UNRECOVERABLE` |
| **`indigo`** | `bg-indigo-400` | Border indigo-500/30, bg-indigo-500/10, text-indigo-300 | `DOWNGRADE`, `UPDATE_PAYMENT_METHOD`, `RETRY_SCHEDULED` |
| **`sky`** | `bg-sky-400` | Border sky-500/30, bg-sky-500/10, text-sky-300 | `ACTION_IN_PROGRESS`, `DETECTED`, `DIAGNOSED`, `POLICY_EVALUATED`, `CREATED` |
| **`slate`** | `bg-slate-400` | Border slate-700, bg-slate-800, text-slate-300 | Unmapped / Fallback status strings |

---

## 8. Error States & Reconnect Recovery

1. **Backend Down on Initial Load**:
   - The UI displays an isolated error card with message `"Network error connecting to backend: Server unreachable"`.
   - The header displays a red environment indicator: `"Backend Offline"`.
2. **Retry Connection**:
   - Clicking **"Retry Connection"** re-triggers the hook's `fetch()` call.
   - When the backend resumes (e.g. Uvicorn restarts), the page seamlessly transitions from the error state back to live data without requiring a browser page reload.

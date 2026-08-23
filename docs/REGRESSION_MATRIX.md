# Frontend Feature Inventory & Regression Matrix

**Document Purpose**: Comprehensive feature-by-feature verification matrix ensuring zero regression across visual redesigns, token standardizations, and component refactors.  
**Validation Date**: 2026-08-23  
**Status**: 100% Verified & Preserved

---

## 1. Feature-by-Feature Regression Matrix

| Feature / UI Control | Page / Component | Endpoint Invoked | Expected Outcome | Before State | After State | Tested Live | Verification Proof / Status |
|---|---|---|---|:---:|:---:|:---:|---|
| **API Health Connection Poll** | `DashboardShell` | `GET /health` | Polls every 15s; renders green dot + "API Connected" | ✓ | ✓ | ✓ | Responds `200 OK` (`"status":"healthy"`) |
| **Tab Navigation (Dashboard/Cases/Eval)** | `DashboardShell` | Client-Side Routing | Switches active tab view cleanly | ✓ | ✓ | ✓ | Client state transitions verified |
| **Razorpay Test Mode Badge** | `DashboardShell` | Static | Displays `Razorpay Test Mode` indicator | ✓ | ✓ | ✓ | Present in shell header |
| **Dashboard Metrics Refresh** | `Dashboard` | `GET /api/v1/metrics/batch` | Refetches live 3-way evaluation metrics | ✓ | ✓ | ✓ | Tested via refresh button & API poll |
| **Dashboard Recent Cases Fetch** | `Dashboard` | `GET /api/v1/cases?limit=5` | Fetches 5 most recent persisted cases | ✓ | ✓ | ✓ | Returns exact 5 recent cases |
| **Hero Recovery KPI Summary** | `Dashboard` | `GET /api/v1/metrics/batch` | Renders ₹1,12,529.40, 21.6% rate, 53.3% case rate, +117.4% lift | ✓ | ✓ | ✓ | 100% data-matched to backend response |
| **Secondary Operational Metrics (5 Stats)** | `Dashboard` | `GET /api/v1/metrics/batch` | Renders Revenue at Risk, Attempts, Dispatches, Escalations, Violations (0) | ✓ | ✓ | ✓ | 100% data-matched to backend response |
| **3-Way Baseline Comparison Table** | `Dashboard` | `GET /api/v1/metrics/batch` | Displays No Action vs Retry Only vs Orchestrator | ✓ | ✓ | ✓ | All 3 baselines match raw API |
| **Recovery Outcomes Breakdown (Data-Driven)** | `Dashboard` | `GET /api/v1/metrics/batch` | Dynamically computed from `orchMetrics` (53.3% recovered, 26.7% escalated, 20.0% other) | ✓ | ✓ (Fixed) | ✓ | Pure data computation (no hardcoded strings) |
| **Recovery Funnel (Data-Driven)** | `Dashboard` | `GET /api/v1/metrics/batch` | Dynamically computed from `orchMetrics` (60 cases $\to$ 44 dispatches $\to$ 32 recoveries) | ✓ | ✓ (Fixed) | ✓ | Pure data computation (no hardcoded strings) |
| **Recent Cases Row Click Navigation** | `Dashboard` | Client-Side Navigation | Opens clicked case in `CaseView` | ✓ | ✓ | ✓ | Verified navigates to selected case ID |
| **Cases Full List Fetch** | `Cases` | `GET /api/v1/cases?limit=100` | Fetches up to 100 cases for table rendering | ✓ | ✓ | ✓ | Returns persisted case array |
| **Cases Search Filter** | `CaseTable` | Client-Side Filter | Searches case ID, customer ID, failure code, email | ✓ | ✓ | ✓ | Filters live list instantly |
| **Cases Workflow Dropdown Filter** | `CaseTable` | Client-Side Filter | Filters All / One-Time / Subscription | ✓ | ✓ | ✓ | Filters live list instantly |
| **Cases Issue Dropdown Filter** | `CaseTable` | Client-Side Filter | Filters All / Bank Timeout / Expired / Insufficient Funds / Invalid Mandate / Security / Auth | ✓ | ✓ | ✓ | Filters live list instantly |
| **Cases Status Dropdown Filter** | `CaseTable` | Client-Side Filter | Filters All / Verified / Escalated / Stopped / Retry Scheduled / Diagnosed / Detected | ✓ | ✓ | ✓ | Filters live list instantly |
| **Cases Table Row Click Navigation** | `CaseTable` | Client-Side Navigation | Navigates to `CaseView` with selected ID | ✓ | ✓ | ✓ | Row click navigates to Case Detail |
| **Case Detail Fetch** | `CaseView` | `GET /api/v1/cases/{id}` | Fetches case fields and complete audit trail | ✓ | ✓ | ✓ | Returns `case` + `audit_trail` (7+ entries) |
| **Demo Case Switcher `<select>`** | `CaseView` | `GET /api/v1/cases/{newId}` | Switches active case in place | ✓ | ✓ | ✓ | Dropdown selector switches case |
| **Process with LangGraph (Execute)** | `CaseView` | `POST /api/v1/cases/{id}/process` | Runs stateful recovery workflow; updates state and audit trail | ✓ | ✓ | ✓ | Returns `200 OK` + immediate green banner |
| **LangGraph Button Loading State** | `CaseView` | Client-Side State | Renders spinning icon + `Processing...` | ✓ | ✓ | ✓ | Visual state transitions verified |
| **LangGraph Button Completed State** | `CaseView` | Client-Side State | Renders disabled `Completed` checkmark when terminal | ✓ | ✓ | ✓ | Disables on terminal statuses |
| **"What Happened?" Plain-English Cards** | `CaseView` | In-Memory Case Data | Summarizes Issue detected / AI suggested / Policy decision | ✓ | ✓ | ✓ | Renders 3 clean cards |
| **Action & Verification Label Branching** | `CaseView` | In-Memory Case Data | Preserves all 6+ policy and gateway branches | ✓ | ✓ | ✓ | Tested across SMART_RETRY, PAYMENT_LINK, ESCALATE, STOP |
| **Technical Details Expand/Collapse** | `CaseView` | Client-Side State | Reveals `StrategyScoreTable`, `PolicyPanel`, `DecisionTimeline` | ✓ | ✓ | ✓ | Collapsible drawer toggles smoothly |
| **Activity & Audit Trail Expand/Collapse** | `CaseView` | Client-Side State | Reveals chronological append-only events | ✓ | ✓ | ✓ | Collapsible drawer toggles smoothly |
| **Benchmark Standard Run** | `Evaluation` | `POST /api/v1/batch/run` | Evaluates 60 cases (seed 42) across 3 baselines | ✓ | ✓ | ✓ | Returns `200 OK` + immediate green banner |
| **Benchmark Custom Config Toggle** | `Evaluation` | Client-Side State | Reveals seed & dataset size inputs | ✓ | ✓ | ✓ | Drawer toggles smoothly |
| **Benchmark Custom Run** | `Evaluation` | `POST /api/v1/batch/run` | Runs batch evaluation with user seed/count | ✓ | ✓ | ✓ | Tested custom execution with seed 99 |
| **Benchmark Metadata Expand/Collapse** | `Evaluation` | Client-Side State | Displays batch ID, dataset version, seed, checksum | ✓ | ✓ | ✓ | Metadata drawer toggles smoothly |
| **Case-Level Results Table (180 rows)** | `Evaluation` | In-Memory Batch Data | Displays individual case-level baseline outcomes | ✓ | ✓ | ✓ | Renders all 180 case results |

---

## 2. Safety Check Verification Summary

| Check | Protocol Requirement | Verified Result | Status |
|---|---|---|---|
| **1. Backend Health** | `GET /health` returns 200 with service health info | `{"status":"healthy","database":"sqlite (local dev fallback)"}` | **PASS** |
| **2. Core Endpoints** | All 7 core endpoints return 200 OK | `/health`, `/cases`, `/cases/{id}`, `/cases/{id}/process`, `/metrics/batch`, `/batch/run`, `/webhooks/razorpay` | **PASS** |
| **3. Backend Pytest** | 100% passing tests in `backend/tests/` | **119 / 119 Passed** (0 failures) | **PASS** |
| **4. Frontend Build** | `npm run build` generates production bundle cleanly | **Built in 1.42s** (0 errors) | **PASS** |
| **5. TypeScript Typecheck**| `npm run lint` (`tsc --noEmit`) passes with 0 errors | **0 Errors** | **PASS** |
| **6. Frontend Unit Tests** | `npm test` validation runner passes | **24 / 24 Passed** (0 failures) | **PASS** |
| **7. Design Tokens** | Consistent Inter typography + standard slate/emerald tokens | Applied via `index.html` & `src/index.css` | **PASS** |
| **8. Data Binding Fix** | Dashboard outcomes & funnel dynamically derived from live `orchMetrics` | Verified with live `GET /api/v1/metrics/batch` | **PASS** |

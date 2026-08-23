# Failures, Incidents, and Engineering Lessons

> **Document Type**: Code-Grounded Post-Mortem and Incident Analysis  
> **Repository**: [`sreeram110909/ai-revenue-recovery-orchestrator`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator)  
> **Buildathon Track**: Razorpay AI Buildathon — Track 03 (AI Revenue Recovery)  
> **Maturity Level**: Production-Inspired Student Buildathon Prototype  
> **Primary Source of Truth**: Git Commit History, Pytest Suites, and Regression Logs

---

## 1. Idempotency Incident: Audit Log Duplication

### Classification: `Product Bug` (Not a Test Bug)
*This was a genuine product-level data integrity defect. In any real-world merchant integration with webhooks or server restarts, repeated processing triggers would have caused unbounded audit trail growth and inflated audit event counts.*

### Problem & Observed Symptoms
During end-to-end testing of the primary demo case (`case_api_001`), querying `GET /api/v1/cases/case_api_001` revealed **331 audit events** in its audit trail. A single clean execution of the recovery pipeline is designed to emit exactly **10 to 12 audit events**. 

Inspection of the audit database revealed repeated bursts of identical `CASE_INGESTED` events logged at timestamps like `7:26:19 PM`, `7:27:06 PM`, and `7:27:24 PM`, all with identical amounts (₹2,500.00) and failure codes (`BANK_TIMEOUT`).

### Root Cause Analysis (Twofold Ingestion Defect)
1. **Unconditional Router Logging ([`backend/app/routers/cases.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/cases.py#L95-L105))**:
   The `POST /api/v1/cases/ingest` endpoint blindly inserted a new `CASE_INGESTED` audit record into the `audit_log` table on every invocation, even when the case record already existed in `recovery_cases`.
2. **Unconditional Node Logging ([`backend/app/orchestrator/nodes.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/orchestrator/nodes.py#L75-L87))**:
   When the LangGraph workflow ran, Node 1 (`detect_and_load`) independently invoked `audit_service.log_event("CASE_INGESTED")` without verifying whether the case had already been ingested in a prior run.

### The Fix (`Commit 161b806`)
- **Router Guard**: Added an existence check before writing ingestion audit logs in `ingest_cases`.
- **Node Guard**: Updated `WorkflowNodes.detect_and_load` to inspect the case's existing audit history via `audit_service.repository.get_by_case_id(case.id)`:
  ```python
  already_ingested = False
  if self.audit_service and self.audit_service.repository:
      existing_audit = self.audit_service.repository.get_by_case_id(case.id)
      already_ingested = any(a.event_type == "CASE_INGESTED" for a in existing_audit)

  if not already_ingested:
      self.audit_service.log_event(case_id=case.id, event_type="CASE_INGESTED", ...)
  ```

### Verification & Metrics
- **Before**: 331 audit entries for `case_api_001`.
- **After**: Exactly 10 audit entries for a complete workflow pass.
- **Regression Guard**: Added [`backend/tests/test_audit_idempotency.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/tests/test_audit_idempotency.py) and verified that re-running `detect_and_load` multiple times adds 0 duplicate audit rows.

---

## 2. Data Contamination Incident: `synth_v1.0_42_010`

### Classification: `Test / Verification Process Issue` (Not a Product Bug)
*The product code worked as intended; the issue was caused by an unsafe manual QA test procedure that fired test payloads at a seeded canonical demo case rather than an isolated disposable test fixture.*

### Problem & Observed Symptoms
When reviewing the 60 canonical benchmark cases on the Cases page, case `synth_v1.0_42_010` (a recurring subscription failure with an original amount of **₹3,817.29**) displayed a mutated `verified_recovered_amount` of **₹2,500.00** and status `VERIFIED_RECOVERED`.

### Root Cause Analysis
During a manual webhook signature verification test, an engineer posted a sample Razorpay `payment_link.paid` webhook payload containing `{"amount": 250000, "notes": {"case_id": "synth_v1.0_42_010"}}`.

The webhook handler ([`backend/app/routers/webhooks.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/webhooks.py)) executed correctly:
1. It cryptographically verified the `X-Razorpay-Signature`.
2. It extracted `case_id: synth_v1.0_42_010`.
3. It parsed the settled amount from the webhook payload (`₹2,500.00`) and updated the case record.

Because real payment webhooks report the actual settled amount from the gateway, the router was functioning properly. However, using a seeded canonical dataset case contaminated the benchmark dataset.

### The Fix (`Commit fc04480`)
1. **Clean Database Reset**: Purged the contaminated database and restored canonical seed=42 values from [`data/evaluations/datasets/recovery_dataset_v1_seed42.json`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/data/evaluations/datasets/recovery_dataset_v1_seed42.json).
2. **QA Test Isolation Protocol**: Created [`docs/TESTING_NOTES.md`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/docs/TESTING_NOTES.md) and updated [`docs/KNOWN_LIMITATIONS.md`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/docs/KNOWN_LIMITATIONS.md) establishing a strict rule: **All manual or automated test scripts must target disposable test case IDs (e.g. `qa_test_case_*`), never seeded demo cases (`case_api_*` or `synth_v1.0_42_*`)**.

---

## 3. Fresh-Clone Startup Incident: Empty Cases Page

### Classification: `Environment / Reproducibility Issue`
*On a fresh machine or clean git clone, the database initialized empty tables, breaking the frontend browsing experience.*

### Problem & Observed Symptoms
When cloning the repository fresh or deleting `revenue_recovery.db`:
1. `POST /api/v1/batch/run` worked correctly and returned canonical benchmark metrics (₹112,529.40 recovered).
2. However, navigating to `http://localhost:3000/cases` showed 0 cases, and `GET /api/v1/cases/synth_v1.0_42_010` returned `404 Not Found`.

### Root Cause Analysis
The batch evaluation runner evaluated the 60 canonical cases in-memory via `generate_synthetic_dataset(seed=42, count=60)`, but never inserted those cases into the SQL `recovery_cases` table. The browsable demo database only existed on developer machines where an uncommitted setup script had previously been run.

### The Fix (`Commit b8c135a`)
1. **Created [`backend/app/services/seed_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/seed_service.py)**:
   Implements `seed_initial_cases_if_needed(session)` to seed the 2 named demo cases (`case_api_001`, `case_api_002`) and the 60 canonical cases (`synth_v1.0_42_001` through `060`).
2. **FastAPI Lifespan Hook ([`backend/app/main.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/main.py#L46-L58))**:
   Automatically runs on startup.
3. **State Preservation Invariant**:
   If a case already exists in the database (e.g. `case_api_001` was progressed to `RETRY_SCHEDULED`), `seed_service` **skips it**, ensuring hot-reloads (`uvicorn --reload`) or server restarts never wipe active user test progress.

---

## 4. Misleading AI Fallback Incident: Fake Initial Strategy

### Classification: `Product / UI Honesty Bug`
*Displaying plausible-looking AI recommendations before diagnosis has actually executed misleads evaluators and users.*

### Problem & Observed Symptoms
In [`src/pages/CaseView.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/pages/CaseView.tsx), the "What Happened?" summary panel rendered:
```tsx
{caseData.recommended_strategy || 'SMART_RETRY'}
{policyOutcome || 'ALLOW'}
```
When viewing an unprocessed case (status `DETECTED`), the UI displayed **"SMART_RETRY"** and **"ALLOW"** as if AI diagnosis and Policy validation had already occurred. For cases like `case_api_002` (Expired Card) or mandate failures, `SMART_RETRY` was not even a valid strategy.

### Root Cause Analysis
Default JavaScript truthy fallbacks (`|| 'SMART_RETRY'`) were used to prevent rendering empty strings in UI cards before the diagnosis agent had run.

### The Fix (`Commit 83bcd77`)
Replaced aggressive fallbacks with honest pending placeholders:
- AI Recommendation: `{caseData.recommended_strategy ? formatText(caseData.recommended_strategy) : <span className="text-slate-500 italic">Pending diagnosis</span>}`
- Policy Outcome: `{policyOutcome ? formatText(policyOutcome) : <span className="text-slate-500 italic">Awaiting policy evaluation</span>}`
- Updated [`src/components/DecisionTimeline.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/DecisionTimeline.tsx) and [`src/components/StrategyScoreTable.tsx`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/components/StrategyScoreTable.tsx) with identical honest pending states.

---

## 5. Other Real Development Issues

### Issue A: SQLite File-Descriptor Leak on File Deletion
- **Problem**: Running verification scripts that unlinked `revenue_recovery.db` on disk while Uvicorn was running caused immediate subsequent API calls to fail with `500 Internal Server Error`.
- **Observed Symptom**: `urllib.error.HTTPError: HTTP Error 500: Internal Server Error`.
- **Actual Root Cause**: The active Uvicorn worker held open SQLite connection handles to the deleted file inode.
- **Fix**: Updated restart verification scripts to restart the FastAPI application lifespan cleanly and touched `backend/app/main.py` to force worker pool reload.
- **Classification**: `Environment / Developer Tooling Issue`.

### Issue B: Verification Script Response Shape KeyError
- **Problem**: Python test scripts executing `POST /api/v1/cases/{id}/process` crashed with `KeyError: 'current_status'`.
- **Observed Symptom**: Script crash during automated QA.
- **Actual Root Cause**: The endpoint returns `{"status": "success", "final_status": "...", "case": {...}}`. The script assumed `current_status` was a top-level JSON key rather than nested under `case` or aliased as `final_status`.
- **Fix**: Adjusted test scripts to read `res.json()['final_status']` and `res.json()['case']['current_status']`.
- **Classification**: `Test-Verification Bug`.

### Issue C: Evaluation Page Hardcoded Recovery Funnel Strings
- **Problem**: Running a custom benchmark with `seed=7, count=80` updated the summary table, but the Recovery Funnel and Header subtitle still read `"60 cases evaluated"`, `"44 successful dispatches"`, `"32 verified recoveries"`, and hardcoded `73.3%` / `53.3%` bar widths.
- **Observed Symptom**: UI displayed mismatched counts across panels.
- **Actual Root Cause**: In `src/pages/Evaluation.tsx`, static JSX strings from the initial design mockup were never wired to `orchMetrics`.
- **Fix (`Commit 0da6036`)**: Replaced all hardcoded values with dynamic computations from `orchMetrics.total_cases`, `orchMetrics.successful_actions`, `orchMetrics.verified_recovered_revenue`, and `metrics.metadata`.
- **Classification**: `Product / Data-Binding Bug`.

---

## 6. Bug Fix History Table

| Incident / Feature | Root Cause | Engineering Fix | Regression Guard | Commit Hash |
| :--- | :--- | :--- | :--- | :---: |
| **Audit Log Duplication** | Unconditional logging in `ingest_cases` and `detect_and_load`. | Added audit history existence checks before logging `CASE_INGESTED`. | `test_audit_idempotency.py` | `161b806` |
| **Test Data Contamination** | Manual test webhook targeted canonical case `synth_v1.0_42_010`. | Reset database cleanly; created QA test isolation protocol in `TESTING_NOTES.md`. | QA Test Fixture Protocol | `fc04480` |
| **Fresh Clone 404 on Cases** | In-memory evaluation never populated `recovery_cases` SQL table. | Created `seed_service.py` to seed 62 canonical cases on FastAPI startup. | `test_seed_service.py` | `b8c135a` |
| **Misleading AI Fallback** | `|| 'SMART_RETRY'` rendered fake AI recommendations on raw cases. | Replaced with honest italicized `"Pending diagnosis"` placeholders. | `frontendValidation.test.ts` | `83bcd77` |
| **Evaluation Funnel Data Binding**| Hardcoded JSX strings in Recovery Funnel and Subtitle. | Dynamically bound all text, counts, and bar widths to `orchMetrics`. | `frontendValidation.test.ts` | `0da6036` |
| **Real-Time SSE Streaming** | Single blocking POST request waited for entire workflow completion. | Added `GET /process/stream` SSE endpoint emitting 10 step updates over ~811ms. | Browser QA / SSE Integration | `6e59b5c` |
| **Dashboard Async Refresh** | Refresh button lacked loading feedback and error notification. | Added spinning icon animation and dismissible toast notification. | Browser QA Task 8 | `c45623e` |
| **StatusBadge CVA Migration** | Custom ad-hoc badge styles were brittle across pages. | Migrated to shadcn Badge primitive with 6 CVA variants. | `StatusBadge.tsx` | `f9ece9e` |

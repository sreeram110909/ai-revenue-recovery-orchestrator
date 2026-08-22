# Feature & Endpoint Validation Matrix

This document provides a comprehensive mapping of every user-visible interactive control, frontend file, API endpoint, HTTP method, payload, expected response, and runtime test status.

---

| Feature Area | UI Control / Action | Frontend File | API Endpoint | Method | Request Payload | Expected Response | Observed Status | Test Result |
|---|---|---|---|---|---|---|---|---|
| **System Health** | Global Status Tag | `DashboardShell.tsx` | `/health` | `GET` | *None* | `{"status": "healthy", "service": "...", "version": "1.0.0"}` | `200 OK` | **PASS** |
| **Executive KPIs** | Page Load / Refresh | `Dashboard.tsx` / `useMetrics.ts` | `/api/v1/metrics/batch` | `GET` | *None* | `BatchRunSummary` with `comparison_summary` and 3-way baseline metrics | `200 OK` | **PASS** |
| **Recent Cases** | Dashboard Recent List | `Dashboard.tsx` / `useCases.ts` | `/api/v1/cases?limit=5` | `GET` | `limit=5` | `CaseListResponse` with top 5 cases | `200 OK` | **PASS** |
| **Case Explorer** | Case Table Load / Refresh | `Cases.tsx` / `CaseTable.tsx` | `/api/v1/cases?limit=100` | `GET` | `limit=100` | `CaseListResponse` with all persisted cases | `200 OK` | **PASS** |
| **Search Filter** | Text Filter Input | `CaseTable.tsx` | *None (Client-Side)* | `—` | *Debounced query* | Filters cases matching ID, customer, or code | `Active` | **PASS** |
| **Workflow Filter** | Dropdown Selector | `CaseTable.tsx` | *None (Client-Side)* | `—` | `ONE_TIME` / `SUBSCRIPTION` | Filters cases by case_type | `Active` | **PASS** |
| **Issue Filter** | Dropdown Selector | `CaseTable.tsx` | *None (Client-Side)* | `—` | `BANK_TIMEOUT`, `EXPIRED_...` | Filters cases by failure_category | `Active` | **PASS** |
| **Status Filter** | Dropdown Selector | `CaseTable.tsx` | *None (Client-Side)* | `—` | `VERIFIED_RECOVERED`, `...` | Filters cases by current_status | `Active` | **PASS** |
| **Case Detail View** | Case Selection / Route | `CaseView.tsx` / `useCase.ts` | `/api/v1/cases/{case_id}` | `GET` | `case_id=case_api_001` | `CaseDetailResponse` (Case fields + audit trail array) | `200 OK` | **PASS** |
| **Case Switcher** | Dropdown Selector | `CaseView.tsx` | `/api/v1/cases/{case_id}` | `GET` | `case_id=case_api_002` | Fetches selected case detail | `200 OK` | **PASS** |
| **LangGraph Execution** | "Process with LangGraph" Button | `CaseView.tsx` | `/api/v1/cases/{case_id}/process` | `POST` | *None* | `ProcessCaseResponse` (updated state + audit event array) | `200 OK` | **PASS** |
| **Technical Details** | "View decision details" Toggle | `CaseView.tsx` | *None (Client-Side)* | `—` | *Toggle state* | Expands LangGraph Decision Timeline, Policy & Strategy panels | `Active` | **PASS** |
| **Full Audit Log** | "View full audit log" Toggle | `CaseView.tsx` | *None (Client-Side)* | `—` | *Toggle state* | Expands raw append-only audit trail table | `Active` | **PASS** |
| **Benchmark Summary** | Evaluation Page Load | `Evaluation.tsx` / `useMetrics.ts` | `/api/v1/metrics/batch` | `GET` | *None* | `BatchRunSummary` with 60 evaluation results | `200 OK` | **PASS** |
| **Run Benchmark** | "Re-run benchmark" Button | `Evaluation.tsx` / `useMetrics.ts` | `/api/v1/batch/run` | `POST` | `{"seed": 42, "count": 60, "dataset_version": "v1.0"}` | `BatchRunSummary` with refreshed batch ID and metrics | `200 OK` | **PASS** |
| **Configure Benchmark**| Custom Benchmark Execution | `Evaluation.tsx` | `/api/v1/batch/run` | `POST` | `{"seed": N, "count": N, "dataset_version": "v1.0"}` | `BatchRunSummary` with customized seed and case count | `200 OK` | **PASS** |
| **Case-Level Results** | "View case-level results" Toggle | `Evaluation.tsx` | *None (Client-Side)* | `—` | *Toggle state* | Expands 180-row case evaluation comparison table | `Active` | **PASS** |
| **Gateway Webhook** | Webhook Endpoint Validation | Backend Route | `/api/v1/webhooks/razorpay` | `POST` | Signed webhook test payload + Signature Header | `{"status": "success"}` | `200 OK` | **PASS** (Validated using signed test events) |

---

## Endpoint Inventory Summary
- **Total API Routes Registered in FastAPI**: `8`
- **Total API Routes Utilized by Frontend**: `6`
- **Backend-Only Core Routes**: `2` (`/api/v1/cases/ingest`, `/api/v1/webhooks/razorpay`)
- **Direct Browser External Calls (Razorpay / Gemini)**: `0` (Zero client-side credential exposure)

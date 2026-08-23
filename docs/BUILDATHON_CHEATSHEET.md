# Razorpay AI Buildathon — 2-Minute Judge Cheatsheet

> **Project**: AI Revenue Recovery Orchestrator (Track 03: AI Revenue Recovery)  
> **Repository**: [`sreeram110909/ai-revenue-recovery-orchestrator`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator)  
> **Maturity**: Production-Inspired Student Buildathon Prototype  
> **Live Benchmark Provenance**: Measured fresh on canonical 60-case dataset (`seed=42`)

---

## 1. Problem (3 Sentences)
Digital merchants lose 5–15% of gross revenue to failed one-time payments and subscription auto-debit drops. Traditional recovery relies on blunt, blind cron-based retries that trigger card network velocity limits, increase customer friction, and exhaust retry caps on expired cards. Support teams are left with manual, fragmented operational queues and zero auditability.

---

## 2. Solution (3 Sentences)
A bounded, policy-governed revenue recovery engine that combines LLM root-cause diagnosis with deterministic strategy scoring and fail-closed merchant policy guardrails. AI proposes candidate strategies based on scrubbed error context, but a 100% deterministic Policy Engine holds unilateral veto power over financial execution. Recovery is only booked after independent gateway verification settles the payment.

---

## 3. Architecture Flow
```
[ Failed Payment ] ──► [ PII Scrubbing ] ──► [ Gemini Diagnosis ] ──► [ Strategy Scorer ]
                                                                             │
                                                                             ▼
[ Append-Only Audit ] ◄── [ Gateway Settlement ] ◄── [ Action Dispatch ] ◄── [ Policy Engine ]
   (Immutable Log)       (Independent Verification)  (Razorpay Test Mode)   (Strict Veto Gate)
```

---

## 4. AI Role (What AI Does)
Google Gemini 2.5 Flash acts strictly as a **Diagnostic Reasoning Assistant** ([`backend/app/agents/diagnosis.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/agents/diagnosis.py)). It ingests sanitized, PII-redacted gateway error strings and payment metadata, normalizes messy issuer messages into one of 7 canonical failure categories, and proposes an ordered list of candidate strategies with a diagnostic rationale. If Gemini is unavailable, times out, or returns unapproved strategies, the system automatically falls back to deterministic rule mappings.

---

## 5. Policy Role ("AI Proposes, Policy Decides")
The Policy Engine ([`backend/app/policies/engine.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/policies/engine.py)) is 100% deterministic and holds absolute authority over execution. It enforces hard merchant guardrails: a ₹15,000 maximum automated value ceiling (`POL-02`), a 3-attempt lifetime cap (`POL-04`), a mandatory 4-hour retry cooldown (`POL-05`), non-retryable category blocks (`POL-03`), and recurring mandate integrity rules (`POL-06`). If the policy vetoes an action, financial execution is forbidden.

---

## 6. Razorpay Role
- **Action Execution ([`backend/app/services/execution_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/execution_service.py))**: When a `PAYMENT_LINK` is authorized, calls Razorpay's `POST /v1/payment_links` API in Test Mode.
- **Independent Reconciliation ([`backend/app/services/verification_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/verification_service.py))**: Queries `GET /v1/payments/:id` or `GET /v1/payment_links/:id` to verify settlement.
- **Webhook Ingestion ([`backend/app/routers/webhooks.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/webhooks.py))**: Ingests `payment_link.paid` and `payment.captured` webhooks with cryptographic HMAC-SHA256 signature verification and event-level deduplication.

---

## 7. Benchmark (What It Measures vs. Does Not Measure)
- **Measures (`Business & System Metrics`)**: Verified recovered revenue (₹), revenue recovery rate (%), case recovery rate (%), recovery attempts, dispatches, human escalations, and policy violations against `NO_ACTION` and `RETRY_ONLY` baselines.
- **Does NOT Measure (`Explicit Limitation`)**: Does not measure standalone LLM token accuracy, BLEU score, or prompt F1-score as a distinct benchmark metric.

---

## 8. Key Numbers (Measured Fresh: `seed=42, count=60`)

| Metric | NO_ACTION Baseline | RETRY_ONLY Baseline | AI REVENUE RECOVERY ORCHESTRATOR | Net Uplift vs. Retry Only |
| :--- | :---: | :---: | :---: | :---: |
| **Evaluated Cases** | `60` | `60` | **`60`** | — |
| **Total Revenue at Risk** | `₹5,21,769.70` | `₹5,21,769.70` | **`₹5,21,769.70`** | — |
| **Verified Recovered Revenue** | `₹0.00` | `₹51,765.46` | **`₹1,12,529.40`** | **+₹60,763.94** |
| **Revenue Recovery Rate** | `0.0%` | `9.9%` | **`21.6%`** | **+117.4% lift** |
| **Case Recovery Rate** | `0.0%` (0/60) | `33.3%` (20/60) | **`53.3%` (32/60)** | **+60.0% case lift** |
| **Recovery Attempts** | `0` | `26` | **`52`** | — |
| **Successful Dispatches** | `0` | `20` | **`44`** | — |
| **Human Escalations** | `0` | `0` | **`16`** | — |
| **Policy Violations** | `0` | `0` | **`0` (100% Authorized)**| — |

---

## 9. Strongest Demo Moment (Policy Overriding AI)
- **Case**: `synth_v1.0_42_059` (Subscription failure, Amount: **₹31,415.20**).
- **AI Recommendation**: Gemini diagnoses `MANDATE_DEBIT_FAILED` and recommends `SUBSCRIPTION_RETRY`.
- **Policy Intervention**: Policy rule `POL-02-AMOUNT-CEILING` detects that ₹31,415.20 exceeds the ₹15,000 limit.
- **Outcome**: The Policy Engine overrules the model, forcing **`HUMAN_ESCALATION`** and blocking automated debit.

---

## 10. Strongest Failure Story (Engineering Rigor)
During early integration testing, demo case `case_api_001` accumulated **331 audit events** instead of ~10. Investigation revealed that the ingestion router and LangGraph Node 1 were logging `CASE_INGESTED` unconditionally on every server restart. We implemented idempotent database checks in both layers (`161b806`), added regression tests, and reduced the audit trail to a clean, canonical 10 events per workflow pass.

---

## 11. Biggest Honest Limitation
The system operates as a **prototype in Razorpay Test Mode and synthetic benchmark evaluation**; it does not execute live production financial clearing or autonomous messaging over WhatsApp/SMS.

---

## 12. Likely Judge Questions & Grounded Answers

1. **Why this problem?**  
   *Answer*: Failed payments are a multi-billion dollar leak where crude retry scripts harass users and trigger card network blocks.  
   *Grounded in*: [`backend/app/schemas/enums.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/schemas/enums.py), [`backend/app/models/case_model.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/models/case_model.py).

2. **Why use AI instead of deterministic rules?**  
   *Answer*: Gateway error messages across acquiring banks are messy and unstructured. Gemini normalizes messy error descriptions into structured root-cause categories.  
   *Grounded in*: [`backend/app/agents/diagnosis.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/agents/diagnosis.py).

3. **Why not let the LLM decide and execute directly?**  
   *Answer*: In finance, models hallucinate and fail open. We enforce "AI proposes, policy decides" to ensure hard limits (₹15,000 cap, 3 retries) can never be bypassed.  
   *Grounded in*: [`backend/app/policies/engine.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/policies/engine.py).

4. **Why LangGraph?**  
   *Answer*: It provides a stateful, cyclical graph with explicit conditional routers and memory checkpointing, cleanly separating reasoning from execution.  
   *Grounded in*: [`backend/app/orchestrator/builder.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/orchestrator/builder.py).

5. **Why Server-Sent Events (SSE) instead of WebSockets?**  
   *Answer*: Recovery workflow streaming is strictly unidirectional (backend $\to$ frontend). SSE is lightweight, operates over standard HTTP, and avoids WebSocket connection overhead.  
   *Grounded in*: [`backend/app/routers/cases.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/cases.py), [`src/hooks/useCase.ts`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/src/hooks/useCase.ts).

6. **How do you prevent duplicate recovery actions?**  
   *Answer*: `ExecutionService` checks case status and attaches unique action IDs (`act_<uuid12>`), rejecting execution if an action has already succeeded.  
   *Grounded in*: [`backend/app/services/execution_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/execution_service.py).

7. **How do you handle duplicate webhooks?**  
   *Answer*: The webhook handler caches processed `event_id` keys in-memory and returns `duplicate_ignored` with 200 OK.  
   *Grounded in*: [`backend/app/routers/webhooks.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/routers/webhooks.py).

8. **What happens if Gemini is down or times out?**  
   *Answer*: `DiagnosisAgent` intercepts the failure and invokes `_fallback_diagnosis()`, using hardcoded failure-category mappings so the pipeline never breaks.  
   *Grounded in*: [`backend/app/agents/diagnosis.py#L298-L336`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/agents/diagnosis.py#L298-L336).

9. **How do you know revenue was actually recovered?**  
   *Answer*: We never mark revenue recovered upon action dispatch. Only when `VerificationService` queries Razorpay and receives `status="captured"` / `"paid"` is money booked.  
   *Grounded in*: [`backend/app/services/verification_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/verification_service.py).

10. **What does the benchmark measure and NOT measure?**  
    *Answer*: It measures recovered revenue uplift and policy compliance across 60 cases. It does not measure standalone LLM token/F1 accuracy.  
    *Grounded in*: [`backend/app/eval/runner.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/eval/runner.py), [`docs/ARCHITECTURE.md#L360-L370`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/docs/ARCHITECTURE.md).

11. **Why use synthetic evaluation data?**  
    *Answer*: It provides a reproducible, zero-leakage benchmark that tests edge cases (expired mandates, high amounts) without consuming live merchant quota.  
    *Grounded in*: [`backend/app/eval/synthetic_dataset.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/eval/synthetic_dataset.py).

12. **Why SQLite for local development?**  
    *Answer*: SQLite allows zero-dependency evaluation for judges while SQLAlchemy ensures 100% drop-in compatibility with PostgreSQL.  
    *Grounded in*: [`backend/app/database.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/database.py).

13. **How do you prevent customer PII from leaking to the model?**  
    *Answer*: `extract_evidence()` redacts customer emails and phones and enforces zero raw credentials before passing context to Gemini.  
    *Grounded in*: [`backend/app/agents/evidence.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/agents/evidence.py).

14. **How does startup seeding work on a clean clone?**  
    *Answer*: FastAPI lifespan calls `seed_service.py`, idempotently seeding 62 cases while preserving active user test mutations across server reloads.  
    *Grounded in*: [`backend/app/services/seed_service.py`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/backend/app/services/seed_service.py).

15. **What was your biggest technical lesson?**  
    *Answer*: In multi-agent systems, idempotency cannot be an afterthought—it must be enforced at every node boundary to prevent audit and execution storms.  
    *Grounded in*: [`docs/FAILURES_AND_LESSONS.md`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/docs/FAILURES_AND_LESSONS.md).

---

## 13. 30-Second Elevator Pitch (Non-Technical)
> "When online payments fail, merchants typically lose the sale or blindly hammer the customer's card until the bank blocks it. We built an AI Revenue Recovery Orchestrator that diagnoses why the payment failed—like an expired mandate versus a transient bank timeout—and automatically takes the right recovery action. Crucially, hard financial guardrails ensure the AI can never exceed budget limits or harass customers, recovering over 117% more revenue than traditional retry mechanisms."

---

## 14. 2-Minute Technical Pitch (Product + Architecture)
> "In payment recovery, unconstrained AI is a financial liability, while static retry rules leave money on the table. We designed an orchestrator based on the principle that **AI proposes, but deterministic policy decides**.
> 
> Our architecture uses LangGraph to coordinate a 9-node state machine. First, evidence is scrubbed of all PII. Google Gemini 2.5 Flash interprets messy bank failure strings to classify root cause. Next, a deterministic scoring engine ranks candidate recovery actions. Before any gateway call occurs, our Policy Engine enforces hard guardrails—evaluating retry caps, cooldown windows, and a ₹15,000 automated ceiling. 
> 
> If approved, the action is dispatched via Razorpay Test Mode APIs. Finally, our verification service independently confirms settlement before booking recovered revenue to an immutable audit trail. In our 60-case canonical benchmark, this architecture delivers a **53.3% case recovery rate** and **+₹60,763.94 in net recovered revenue** with **zero policy violations**."

# Benchmark Dataset & Reproducibility Specification

**Canonical Dataset File**: [`data/evaluations/datasets/recovery_dataset_v1_seed42.json`](file:///Users/sreerambanoth/Documents/ai-revenue-recovery-orchestrator/data/evaluations/datasets/recovery_dataset_v1_seed42.json)  
**Dataset Version**: `v1.0`  
**Random Seed**: `42` (Fixed, Deterministic)  
**Total Case Count**: `60`  
**Policy Version**: `v1.0`  
**Strategy Scoring Version**: `v1.0`  
**System Code Version**: `1.0.0`  
**Generation Timestamp**: `2026-08-22T00:00:00Z`  
**SHA-256 Checksum**: `741535b89fd6a558335268d8174eb5a9c6b2e4295fdadd4f0dd457d31724ae5c`

---

## 1. Overview & Purpose

The **AI Revenue Recovery Orchestrator Benchmark Dataset** is a canonical, immutable, synthetic evaluation dataset designed to rigorously test, score, and compare payment recovery strategies under controlled, realistic fintech conditions.

### Why a Synthetic Dataset?
1. **Zero PII Exposure**: Real merchant payment failure logs contain sensitive cardholder data, customer emails, phone numbers, and financial details. The synthetic dataset masks all identifiers (`user_001***@gmail.com`, `+91 98*** **111`).
2. **Heterogeneous Failure Distributions**: Real merchant traffic is often skewed towards a single dominant failure mode. The synthetic dataset guarantees balanced coverage across transient network timeouts, expired instruments, insufficient funds, expired recurring mandates, fraud/security blocks, and authentication failures.
3. **Controlled Ground Truth**: Every case includes deterministic ground-truth metadata (`is_retryable_failure`, `is_high_value`, `is_mandate_invalid`, `expected_policy_outcome`, `expected_ideal_strategy`) against which AI diagnosis accuracy and policy enforcement can be objectively evaluated.
4. **Offline Evaluation Guarantee**: The dataset enables repeatable, offline comparative evaluation without incurring real payment gateway transaction charges or consuming third-party API quotas.

---

## 2. Dataset Generation Methodology

The dataset is generated deterministically by `backend/app/eval/synthetic_dataset.py` using Python's standard `random.Random(seed=42)` pseudo-random number generator anchored to a fixed reference benchmark timestamp (`2026-08-22T00:00:00Z`).

### Failure Scenario Templates (Heterogeneous Coverage)

| Scenario Template | Workflow Type | Failure Category | Amount Range (₹) | Mandate Status | Expected Policy Outcome | Expected Strategy |
|---|---|---|---|---|---|---|
| **Bank Network Timeout** | `ONE_TIME_PAYMENT` | `BANK_TIMEOUT_NETWORK` | ₹500 – ₹3,500 | N/A | `ALLOW` | `SMART_RETRY` |
| **Transient Insufficient Funds** | `ONE_TIME_PAYMENT` | `INSUFFICIENT_FUNDS` | ₹1,000 – ₹5,000 | N/A | `ALLOW` | `SMART_RETRY` |
| **Expired Card Instrument** | `ONE_TIME_PAYMENT` | `EXPIRED_INSTRUMENT` | ₹800 – ₹4,000 | N/A | `ALLOW` (Downgraded) | `PAYMENT_LINK` |
| **Risk / Security Block** | `ONE_TIME_PAYMENT` | `RISK_SECURITY_BLOCK` | ₹2,000 – ₹8,000 | N/A | `BLOCK` | `HUMAN_ESCALATION` |
| **High-Value VIP Failure** | `ONE_TIME_PAYMENT` | `BANK_TIMEOUT_NETWORK` | ₹25,000 – ₹75,000| N/A | `ESCALATE` | `HUMAN_ESCALATION` |
| **Auth 3DS Failure** | `ONE_TIME_PAYMENT` | `AUTHENTICATION_FAILED` | ₹1,500 – ₹6,000 | N/A | `ALLOW` (Downgraded) | `PAYMENT_LINK` |
| **Recurring Mandate Timeout** | `SUBSCRIPTION_RECURRING`| `BANK_TIMEOUT_NETWORK` | ₹1,200 – ₹4,500 | `ACTIVE` | `ALLOW` | `SUBSCRIPTION_RETRY` |
| **Subscription Expired Mandate**| `SUBSCRIPTION_RECURRING`| `MANDATE_EXPIRED_INVALID`| ₹1,500 – ₹6,000 | `EXPIRED` | `ALLOW` (Downgraded) | `UPDATE_PAYMENT_METHOD`|
| **Subscription High-Value Failure**| `SUBSCRIPTION_RECURRING`| `INSUFFICIENT_FUNDS` | ₹20,000 – ₹50,000| `ACTIVE` | `ESCALATE` | `HUMAN_ESCALATION` |

---

## 3. Strict Multi-Baseline Isolation

All three evaluated recovery strategies consume **an independent, isolated deep copy** of the exact same 60-case dataset. State mutations during the execution of one strategy never bleed into or affect the initial state seen by another strategy.

```
                      Canonical Dataset (60 Cases)
                      [recovery_dataset_v1_seed42.json]
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
  [NO_ACTION Baseline]      [RETRY_ONLY Baseline]      [AI ORCHESTRATOR]
  - 60 isolated cases        - 60 isolated cases        - 60 isolated cases
  - 0 recovery attempts      - Fixed retry heuristics   - Diagnosis -> Policy -> Execution
  - ₹0.00 recovered          - ₹51,765.46 recovered     - ₹112,529.40 recovered
```

---

## 4. Benchmark Source of Truth Metrics

| Metric | NO_ACTION Baseline | RETRY_ONLY Baseline | AI REVENUE RECOVERY ORCHESTRATOR | Uplift vs Retry Only |
|---|---|---|---|---|
| **Evaluated Cases** | `60` | `60` | `60` | — |
| **Total Revenue at Risk** | `₹5,21,769.70` | `₹5,21,769.70` | `₹5,21,769.70` | — |
| **Verified Recovered Revenue** | `₹0.00` | `₹51,765.46` | **₹1,12,529.40** | **+₹60,763.94** |
| **Revenue Recovery Rate** | `0.0%` | `9.9%` | **21.6%** | **+117.4% lift** |
| **Case Recovery Rate** | `0.0%` | `33.3%` (20/60) | **53.3%** (32/60) | **+60.0% case lift** |
| **Recovery Attempts** | `0` | `26` | **52** | — |
| **Successful Dispatches** | `0` | `20` | **44** | — |
| **Human Escalations** | `0` | `0` | **16** | — |
| **Policy Violations** | `0` | `0` | **0** (100% Policy-Authorized)| — |

---

## 5. Verification & Integrity Checklist

To verify dataset integrity and reproducibility independently:

1. **Verify SHA-256 Checksum**:
   ```bash
   shasum -a 256 data/evaluations/datasets/recovery_dataset_v1_seed42.json
   # Expected output: 741535b89fd6a558335268d8174eb5a9c6b2e4295fdadd4f0dd457d31724ae5c
   ```

2. **Verify Bitwise Generator Output**:
   ```bash
   .venv/bin/python3 -c "
   import json, hashlib
   with open('data/evaluations/datasets/recovery_dataset_v1_seed42.json', 'rb') as f:
       assert hashlib.sha256(f.read()).hexdigest() == '741535b89fd6a558335268d8174eb5a9c6b2e4295fdadd4f0dd457d31724ae5c'
   print('Dataset checksum verified!')
   "
   ```

3. **Run Full Benchmark Evaluation**:
   ```bash
   .venv/bin/python3 -c "
   from backend.app.eval.runner import EvaluationRunner
   runner = EvaluationRunner()
   summary = runner.run_evaluation(seed=42, count=60)
   print('Orchestrator Recovered:', summary.metrics['AI_REVENUE_RECOVERY_ORCHESTRATOR'].verified_recovered_revenue)
   assert summary.metrics['AI_REVENUE_RECOVERY_ORCHESTRATOR'].verified_recovered_revenue == 112529.4
   print('Benchmark reproduction verified!')
   "
   ```

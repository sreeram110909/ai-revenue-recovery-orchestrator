# Batch Evaluation Report: `batch_20260821_194559_04efb3`

## 1. Run Metadata

- **Batch ID**: `batch_20260821_194559_04efb3`
- **Timestamp**: `2026-08-21T19:46:00.198099`
- **Dataset Version**: `v1.0`
- **Random Seed**: `42` (100% Deterministic Reproducibility)
- **Total Cases Evaluated**: `60`
- **Policy Version**: `1.0.0-demo`
- **Code Version**: `1.0.0`

---

## 2. Baseline Comparison Table

| Metric | NO_ACTION | RETRY_ONLY | AI_REVENUE_RECOVERY_ORCHESTRATOR |
|---|---|---|---|
| **Total Cases** | 60 | 60 | 60 |
| **Total Revenue at Risk** | ₹521,769.70 | ₹521,769.70 | ₹521,769.70 |
| **Recovery Attempts** | 0 | 44 | 52 |
| **Successful Actions** | 0 | 44 | 44 |
| **Verified Recovered Revenue** | **₹0.00** | **₹51,765.46** | **₹112,529.40** |
| **Revenue Recovery Rate** | 0.0% | 9.9% | **21.6%** |
| **Case Recovery Rate** | 0.0% | 33.3% | **53.3%** |
| **Policy Blocks** | 0 | 8 | 0 |
| **Human Escalations** | 0 | 8 | 16 |
| **Stopped Cases** | 0 | 0 | 0 |
| **Failed Actions** | 0 | 0 | 0 |
| **Policy Violations** | **0** | **0** | **0** |

---

## 3. Comparison Insights

- **Absolute Revenue Lift**: ₹60,763.94 over RETRY_ONLY baseline.
- **Percentage Revenue Lift**: +117.4% over RETRY_ONLY baseline.
- **Policy Safety**: Zero policy violations observed across all evaluated cases.
- **Financial Settlement Accounting**: Only verified gateway outcomes contributed to recovered revenue.

---

## 4. Truth Provenance

- Dataset Inputs: `SYNTHETIC_DATA_RESULT`
- Gateway Verifications: `MOCKED_TEST_RESULT`
- Live API Calls: `0` (Zero live external API calls during benchmark execution)
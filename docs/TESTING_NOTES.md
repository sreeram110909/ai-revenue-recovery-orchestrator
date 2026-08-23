# QA & Manual Testing Protocol: Test Case Isolation

This document defines testing safety rules and isolation protocols for developers, QA engineers, and automated testing agents.

---

## 1. Golden Rule: Disposable Test Case IDs for QA Testing

> **Never target canonical seeded cases (`case_api_*`, `synth_v1.0_42_*`) with manual or simulated write operations (webhooks, state modifications, or ad-hoc test charges).**

### Rationale
Seeded cases represent the baseline canonical demonstration state and benchmark evaluation dataset. Firing arbitrary test payloads (e.g. `payment.captured` webhooks with arbitrary amounts) against seeded cases permanently alters their recorded state, audit logs, and verified recovery numbers, leading to data contamination and reporting mismatches.

---

## 2. Protocol for Live & Manual Endpoint Testing

When testing write endpoints such as `POST /api/v1/webhooks/razorpay`, `POST /api/v1/cases/{id}/process`, or `POST /api/v1/cases/ingest`:

1. **Create a Dedicated Disposable Test Case**:
   - Ingest a temporary case with an explicit test prefix, e.g.:
     `qa_disposable_test_001` or `qa_webhook_test_YYYYMMDD`
2. **Match Payload Amounts Exactly**:
   - Ensure the test webhook event payload's `amount` matches the disposable case's `amount * 100` in paise (e.g. ₹2,500.00 $\to$ `250000` paise).
3. **Clean Up After Testing**:
   - Disposable cases can be queried for verification during the test run, or cleaned up via database reset without contaminating the 60 canonical benchmark cases.

---

## 3. Automated Test Isolation

- Automated unit and integration tests located in `backend/tests/` automatically run in isolated SQLite in-memory or ephemeral session fixtures (`client` fixture in `conftest.py`).
- Automated tests do NOT mutate the persistent development `revenue_recovery.db` SQLite file.

---

## 4. Resetting Development Database

If development data ever requires a clean reset to canonical baseline:
```bash
# Rebuild database from canonical seed=42 dataset
PYTHONPATH=backend python3 -c "
import json, os
from app.database import create_db_engine, create_tables, get_session_factory
from app.models.case_model import RecoveryCaseModel
from app.models.audit_model import AuditLogModel
from app.schemas.enums import CaseStatus, TruthProvenance

if os.path.exists('revenue_recovery.db'):
    os.remove('revenue_recovery.db')

engine = create_db_engine()
create_tables(engine)
session = get_session_factory(engine)()

with open('data/evaluations/datasets/recovery_dataset_v1_seed42.json') as f:
    dataset = json.load(f)

for c in dataset['cases']:
    session.add(RecoveryCaseModel(
        id=c['id'], case_type=c['case_type'], customer_id=c['customer_id'],
        masked_customer_email=c['masked_customer_email'], masked_customer_phone=c['masked_customer_phone'],
        customer_segment=c.get('customer_segment', 'STANDARD'), amount=c['amount'], currency=c['currency'],
        gateway_reference_id=c['gateway_reference_id'], failure_code=c['failure_code'],
        failure_description=c['failure_description'], failure_category=c['failure_category'],
        attempts_count=c.get('attempts_count', 0), max_attempts_allowed=c.get('max_attempts_allowed', 3),
        subscription_details=c.get('subscription_details'), current_status=CaseStatus.DETECTED.value,
        provenance=TruthProvenance.SYNTHETIC_DATA_RESULT.value, verified_recovered_amount=0.0
    ))
session.flush()

for c in dataset['cases']:
    session.add(AuditLogModel(
        case_id=c['id'], event_type='CASE_INGESTED', actor='INGESTION_API',
        previous_status=None, new_status=CaseStatus.DETECTED.value, policy_outcome=None, strategy=None,
        details={'amount': c['amount'], 'currency': c['currency'], 'failure_code': c['failure_code'], 'failure_category': c['failure_category']},
        provenance=TruthProvenance.SYNTHETIC_DATA_RESULT.value
    ))

session.commit()
session.close()
"
```

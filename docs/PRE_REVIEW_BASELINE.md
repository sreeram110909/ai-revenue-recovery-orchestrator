# Pre-Review Baseline Snapshot

**Capture Date**: 2026-08-23T01:14:00+05:30  
**Repository**: `https://github.com/sreeram110909/ai-revenue-recovery-orchestrator`  
**Purpose**: Baseline snapshot before comprehensive repository audit and submission polish.

---

## 1. Git & Version Control Baseline

- **Current Branch**: `main`
- **Current Commit SHA**: `25807b694c9c74768821657501ab8344cef3d195`
- **Commit Count**: `1` (`feat: AI Revenue Recovery Orchestrator - Initial Release`)
- **Remote URL**: `https://github.com/sreeram110909/ai-revenue-recovery-orchestrator.git`
- **Working Tree State**: Clean (0 uncommitted changes)

---

## 2. Runtime Environment Baseline

- **Python Version**: `3.11.15`
- **Node.js Version**: `v24.12.0`
- **npm Version**: `11.6.2`
- **Operating System**: macOS (Darwin ARM64)

---

## 3. Configuration & Dependency Files Baseline

### `package.json` (Observed Scaffold)
- **Name**: `"react-example"` (leftover scaffold name)
- **Version**: `"0.0.0"`
- **Unused Dependencies Observed**:
  - `@google/genai` (unused client-side; all LLM calls are server-side)
  - `express`, `@types/express` (backend is FastAPI in Python)
  - `dotenv` (unused client-side; Vite handles env vars via import.meta.env)
  - `motion` (unused client-side)
  - Duplicate `vite` in dependencies and devDependencies

### `requirements.txt`
- Contains: `fastapi`, `uvicorn`, `pydantic`, `langgraph`, `langchain-core`, `google-genai`, `razorpay`, `sqlalchemy`, `psycopg`, `alembic`, `pytest`, `httpx`, `python-dotenv`, `structlog`, `tenacity`.

---

## 4. Test & Verification Baseline

| Test Suite | Command | Result | Duration | Notes |
|---|---|---|---|---|
| **Backend Pytest** | `.venv/bin/pytest backend/tests/ -v` | **119 Passed**, 0 Failed | 5.50s | 1 Starlette deprecation warning (`httpx` import) |
| **Frontend Test Suite** | `npm test` | **24 Passed**, 0 Failed | 430ms | Covers policy engine, invariants, security scans |
| **TypeScript Typecheck** | `npm run lint` (`tsc --noEmit`) | **0 Errors** | 1.1s | Clean type safety |
| **Vite Production Build** | `npm run build` | **Success** | 968ms | Clean ESM bundle output |

---

## 5. Benchmark Artifacts Baseline

- **Canonical Dataset**: `data/evaluations/datasets/recovery_dataset_v1_seed42.json`
- **SHA-256 Checksum**: `741535b89fd6a558335268d8174eb5a9c6b2e4295fdadd4f0dd457d31724ae5c`
- **Historical Batch Runs**: Persisted under `data/evaluations/` (JSON & MD artifacts)
- **Baseline Measured Results**:
  - `NO_ACTION`: ₹0.00 recovered (0.0%)
  - `RETRY_ONLY`: ₹51,765.46 recovered (9.9% revenue recovery, 33.3% case rate)
  - `AI_REVENUE_RECOVERY_ORCHESTRATOR`: ₹112,529.40 recovered (21.6% revenue recovery, 53.3% case rate)
  - `Net Uplift vs Retry Only`: +₹60,763.94 (+117.4% lift)
  - `Policy Violations`: 0

---

## 6. Identified Issues to Address

1. `package.json` scaffold name `"react-example"` and metadata.
2. Unused client-side dependencies (`@google/genai`, `express`, `dotenv`, `motion`).
3. Over-enthusiastic marketing tone in `docs/EVALUATOR_REVIEW.md` $\to$ Replace with transparent `docs/KNOWN_LIMITATIONS.md`.
4. Missing `LICENSE` file (MIT, 2026 Sreeram Banoth).
5. `README.md` structure opening with runtime caveats rather than problem statement, architecture, and headline benchmark results.
6. Git history review and honest representation.

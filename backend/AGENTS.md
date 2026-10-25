# backend/ agent rules

Applies to any agent working in `backend/`, on top of the root `AGENTS.md`. Nearest file wins on conflict.

## Rules
- Implement the contract exactly (`docs/API_CONTRACT.md`): paths, status codes, field names, error shape. If the implementation must differ, change the contract first (ask Abhishek) in the same PR.
- Money: `Decimal` end to end, built from strings. Store amounts as `NUMERIC` or decimal strings plus an ISO 4217 currency; never float columns. Serialise money as decimal strings, rates as decimal fractions.
- Validate every request at the boundary and return the shared error shape; never leak stack traces or PII.
- Demo-path endpoints read seed data or cached results only: no live third-party calls (see `llm-guardrails` for model calls).
- Finance logic lives in small pure functions with a unit test using a known answer (skill: `finance-domain`).
- Expose OpenAPI at a stable URL so `make types` works. Log without secrets or personal data.
- Every new endpoint handler has a docstring and a contract entry; every new env var is in `.env.example` and the README Config section.

## Domain rules
- **Graph engine**: trust path products are `Decimal` end to end. Never use `float` for intermediate hop products, weights, or R scores. See `graph-trust-engine` skill.
- **Out-degree conservation**: `W_uv = C_u / |Out(u)|`. Every vouch mutation (add or remove) must recompute all sibling weights atomically in a single transaction. No partial updates.
- **Cycle absorption**: the graph traversal MUST maintain a visited-set **per path**, not per node globally. A shared global visited-set is a bug.
- **Slashing**: follow the `slashing-cascade` skill exactly. Never invent penalty fractions. Apply all k=0/k=1/k=2 slashes atomically.
- **ZK layer (demo mode)**: the Poseidon hash is STUBBED with sha256 + salt. Label every stub function and its callsites with `# ZK_STUB`. See `zk-identity-stub` skill.
- **Epistemic uncertainty**: `sigma2` is derived from data completeness. It starts at `1.0` for a cold-start node. It is NEVER negative. Do not impute missing fields; flag them and raise `sigma2`.
- **Score formula**: comes from `dual-axis-scoring` skill. Do not deviate without a `/decide` entry.
- **DEMO_MODE**: when `DEMO_MODE=true` env var is set, all external API calls (Account Aggregator, EVM RPC) are short-circuited to `data/` seed reads. No live API calls on the demo path.
- **Money**: `Decimal` end to end. Store amounts as integer minor units (paise for INR) in the DB; serialise as decimal strings with ISO 4217 code in the API. Never float columns.

## Stack notes
- **Framework & Runtime**: Python 3.11+, FastAPI (REST API), NetworkX (Web-of-Trust graph), Google OR-Tools CP-SAT (constrained loan optimization), Pydantic v2 (validation & schemas), SQLite + JSONL (tamper-evident audit ledger).
- **Run tests**: `pytest` or `pytest tests/` (full test suite: 99 tests passing). Run one test: `pytest tests/test_vouch_score_v2.py`.
- **Run server**: `python main.py serve --port 8000` or `uvicorn veritrust.api.app:app --port 8000`. OpenAPI interactive docs at `http://localhost:8000/docs`.
- **Folder layout**:
  - `src/veritrust/`: Core graph engine (`engine.py`), v2 scoring & heuristics (`scoring.py`), loan lifecycle (`lending.py`), cryptographic audit ledger (`ledger.py`), OR-Tools optimizer (`optimizer.py`), Monte Carlo stress tester (`stress_tester.py`), and FastAPI REST endpoints (`api/`).
  - `tests/`: Pytest unit tests for all domain logic and endpoints.
  - `localdocs/`: Specification documents and developer master v2 documentation.
  - `ml/`: Credit-default modeling, conformal prediction sets, and explainability.
- **Error shape helper**: API endpoints return standard `{ "detail": "<message>" }` or validation errors with HTTP status codes matching `docs/API_CONTRACT.md`.

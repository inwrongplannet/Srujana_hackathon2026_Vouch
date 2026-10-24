---
name: api-contract
description: Write and change endpoint shapes in docs/API_CONTRACT.md before implementation, keeping backend, frontend and seed data aligned
---
# api-contract

**Why this exists:** Contract-first is what lets frontend and backend work proceed in parallel; one disciplined format avoids silent drift
**Used by:** Abhishek
**Triggered by:** Before any new or changed endpoint; during `/kickoff`

## When to use
Adding, changing or removing an endpoint, or when the frontend and backend disagree on a shape.

## Steps
1. Read `docs/API_CONTRACT.md`, the relevant `docs/features/*.md`, and `scripts/seed.py` output in `data/`.
2. Write each endpoint with the file's template: **Method + path**, **Request** (params, body with field types), **Response** (success body and error shape), **Status** (`proposed` -> `agreed` -> `implemented`). Give a realistic example payload that matches the seed data.
3. Rules for shapes:
   - Money fields are decimal **strings** with an explicit `currency` (ISO 4217), never JSON numbers; rates are decimal fractions; dates are `YYYY-MM-DD`, timestamps are ISO 8601 UTC.
   - Errors share one shape (e.g. `{"error": {"code": "...", "message": "..."}}`) with proper HTTP status codes.
   - List endpoints state ordering and pagination (or "returns all, max N rows" for the demo).
   - Prefer additive changes. A breaking change needs the author of the dependent task notified, and a task added or updated via `/task`.
4. Only mark an endpoint `agreed` when Abhishek and the consumer of the endpoint both accept the shape. The backend then implements to the contract; if the implementation must diverge, change the contract first in the same PR.
5. After the backend exposes it, run `make types` so the frontend types come from the real OpenAPI, and check they match the contract. Make sure `scripts/seed.py` produces data in the contract's shape.

---
name: scaffold-zone
description: Scaffold backend/ or frontend/ on event day and wire it into the Makefile, CI and AGENTS.md
---
# scaffold-zone

**Why this exists:** Scaffolding is where the first hour disappears and where the repo conventions get lost; one checklist makes both zones plug into `make check` the same way
**Used by:** Whoever the scaffold task is assigned to
**Triggered by:** Event day, right after `/kickoff` picks the stack

## When to use
Creating the app in `backend/` or `frontend/` for the first time. Stack is the one recorded in `docs/DECISIONS.md` / `docs/ARCHITECTURE.md`; if none is recorded, stop and run `/kickoff` or `/decide` first.

## Steps
1. Create the app inside the zone folder only (e.g. `backend/`), replacing the placeholder `README.md` with real run instructions. Use the framework's standard generator and the boring defaults; keep it runnable in under 5 minutes from a fresh clone.
2. Add a zone `Makefile` with exactly these targets, because the root Makefile delegates to them and skips a zone without one:
   - `dev`: start the app with hot reload (foreground).
   - `test`: run tests; it must pass (add one trivial passing test).
   - `lint`: formatter check plus linter; it must pass.
   Use the zone's own tooling (e.g. ruff + pytest, or eslint + vitest). No extra targets are needed.
3. Backend only: expose OpenAPI at a stable URL (FastAPI `/openapi.json`) so `make types` works; set `OPENAPI_SRC` in `scripts/gen_types.sh` if the URL differs. Add a health endpoint and an error-response shape, and implement money as `Decimal` from day one.
4. Frontend only: put generated types at `frontend/src/types/api.d.ts` (the default `TYPES_OUT`), run `make types`, and read API base URL from an env var listed in `.env.example`.
5. Ignore build output and local DBs (already in `.gitignore`); extend it only if the stack needs more. Add any new env keys to `.env.example`.
6. Update `.github/workflows/check.yml`: add `actions/setup-node` / dependency installs for the stack, with caching, so `make check` passes in CI.
7. Fill the zone's own files, not the root: replace `TODO(scaffold)` under Stack notes in `<zone>/AGENTS.md` (framework and version, how to run one test and one lint, folder layout, error-shape or type-import helper) and rewrite `<zone>/README.md` from `docs/templates/zone-readme.md` (Run, Structure, Interfaces, Config, Testing, Status). Keep `<zone>/AGENTS.md` under 80 lines. No root `AGENTS.md` change is needed unless a root command or rule changed.
8. Log framework and key libraries with `/decide`. Run `make check` and open a PR (see `branch-and-commit`).

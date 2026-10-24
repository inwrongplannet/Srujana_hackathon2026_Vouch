# Decisions

> Edit only via `/decide`. Newest first.

**Why this file exists:** a running log of what we chose and why (especially new dependencies). Stops repeat debates and doubles as pitch material.

<!-- ENTRIES -->

2026-10-25: Added Google OR-Tools (CP-SAT / pywraplp) for loan restructuring and tenure optimization — fast, exact constraint satisfaction under rule-based affordability bounds.
2026-10-24: Chose Python + Pydantic + Decimal for backend money arithmetic — avoids IEEE-754 float drift on trust scores; aligns with AGENTS.md finance rule.
2026-10-24: Chose NetworkX DiGraph for the trust graph — well-tested, supports attributed edges for capacity weights; no new abstraction needed.
2026-10-24: Chose SQLite (via stdlib) as the flat-file store for the CLI session — zero-dependency, deterministic, portable for the demo path.
2026-10-24: Chose pydantic v2 for domain models — coerces raw inputs to Decimal at the boundary, reducing validation boilerplate.
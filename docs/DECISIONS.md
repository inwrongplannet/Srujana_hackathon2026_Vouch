# Decisions

> Edit only via `/decide`. Newest first.

**Why this file exists:** a running log of what we chose and why (especially new dependencies). Stops repeat debates and doubles as pitch material.

## Log

<!-- ENTRIES -->

### 2026-10-25: Credit datasets: a simulated world plus a hybrid anchored on real Home Credit applicants
- **Decision:** Two datasets with one schema. `veritrust.synth` simulates borrowers month by month (default emerges from cash flow; hidden truth known). `veritrust.anchor` takes real Home Credit applicants (real bureau grids, repayment history, missing values, label) and adds synthetic bank statements generated from each person's real columns, never from the label, calibrated on real Berka accounts.
- **Why:** F-04 asks for income stability, obligations, repayment history and cash-flow patterns together; no public dataset has all four with real outcomes. Real labels give credibility; the simulated truth is the only way to verify "absence of history is not inability to repay".
- **Alternatives considered:** Rule-based synthetic rows (makes conformal sets trivial); pasting rows from different datasets together (no shared person, so meaningless); generating distress from the label (label leakage, caught by our leakage test).
- **Consequences:** Real rows stay in git-ignored `data/external/`; Home Credit originates from a Kaggle competition, so its rules must be checked before use beyond this prototype. Anchored label (TARGET) and simulated label (90+ DPD) are different definitions and must not be pooled.
- **By:** Reehan

### 2026-10-25: Data-build dependencies pandas, pyarrow, pymysql (pending Abhishek)
- **Decision:** `backend/requirements-data.txt`: pandas>=3.0 (BSD-3), pyarrow>=25.0 (Apache-2.0), pymysql>=2.2 (MIT), used only by `veritrust.anchor` to read parquet and Berka.
- **Why:** The Home Credit mirror is parquet (about 900 MB) and Berka is served from CTU's MariaDB; stdlib cannot read either efficiently.
- **Alternatives considered:** stdlib CSV mirror (2.6 GB, unlicensed upload); DuckDB (another engine to learn).
- **Consequences:** Network needed only to download; never at demo time. The CLI, tests and `veritrust.synth` stay stdlib only. Needs Abhishek's approval before merge.
- **By:** Reehan

2026-10-24: Chose Python + Pydantic + Decimal for backend money arithmetic — avoids IEEE-754 float drift on trust scores; aligns with AGENTS.md finance rule.
2026-10-24: Chose NetworkX DiGraph for the trust graph — well-tested, supports attributed edges for capacity weights; no new abstraction needed.
2026-10-24: Chose SQLite (via stdlib) as the flat-file store for the CLI session — zero-dependency, deterministic, portable for the demo path.
2026-10-24: Chose pydantic v2 for domain models — coerces raw inputs to Decimal at the boundary, reducing validation boilerplate.
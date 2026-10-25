# Decisions

> Edit only via `/decide`. Newest first.

**Why this file exists:** a running log of what we chose and why (especially new dependencies). Stops repeat debates and doubles as pitch material.

## Log

<!-- ENTRIES -->

### 2026-10-25: Behaviour layer: conditions, random walks and absurdity in the simulated world
- **Decision:** `veritrust.synth.behaviour` adds, on its own random stream: regional events that hit many borrowers at once (a north-India heatwave, a Karnataka-Maharashtra flood, a national lockdown; all hypothetical), during which endorsers' help shrinks to 35-70% of normal; a persistent AR(1) random walk in income and a drift in discipline; a temporary scarcity dip in discipline after any shock; and rare rule-breaking events (windfalls, theft or fire, migration, present-bias splurges peaking at festivals, technical auto-debit bounces). Shock severity now sets how much of the buffer drains. Every borrower is labelled NORMAL, IDIOSYNCRATIC, COVARIATE or BOTH, and every event is logged in `life_events.csv`.
- **Why:** rules alone made the world too tidy, and the vouch's value should be tested where it matters: emergencies nobody controls. Informal risk-sharing absorbs individual shocks far better than shared ones (Townsend 1994), and financial stress lowers decision quality (Mullainathan and Shafir 2013), so both are modelled rather than assumed away.
- **Alternatives considered:** iid noise only (no persistence, so people never really change); a lockdown in every cohort's window (left almost nobody in normal conditions and pushed default to 18%).
- **Consequences:** default rises (more things go wrong) and severity now matters; the event dates, exposures and sizes are assumptions in `params.py`, not history.
- **By:** Reehan

### 2026-10-25: Shock-question data: bureau and vouch trajectories, a shock-study cohort, Prosper as the real anchor
- **Decision:** Extend the simulated world with monthly bureau-style scores (an illustrative 300-900 scorecard, never presented as a real bureau value) and the events behind every change, a time-stamped vouch graph scored with the Vouch scoring proposal's formula, planned pre-application shocks, post-application loan performance and reputation updates. Add a 15,000-borrower shock-study cohort (live credit, one shock each, `cohort=shock_study`, no sample weight) beside the 20,000-borrower main population (shocks oversampled, `sample_weight` back to an assumed 5% real incidence). Add real Prosper loans (credit score, endorsements, outcome) as source `real_prosper`, and a month-by-month delinquency trajectory from the real Home Credit grids with no score invented.
- **Why:** The question "the bureau score fell after a shock but the vouch held: does the vouch still predict repayment, and why?" needs before/after trajectories and enough shocked applicants: only about 9% of the main population carries live credit, so 3,000 bureau shocks would need about 170,000 main borrowers. Prosper is the only public dataset found with endorsements and an outcome for the same borrower; it supplies the real effect size (endorsed borrowers default 4.4 pp less within credit-score bands, in line with Freedman and Jin's 4.1 pp).
- **Alternatives considered:** Shocking 15% of the main population (most shocks are absorbed by savings and never reach the bureau, giving about 300 bureau shocks); a fabricated score for real rows (rejected: the Vouch documentation forbids fabricating a bureau score); LendingClub and Freddie Mac (no endorsements); Kiva (no endorsement field in the public snapshot).
- **Consequences:** The simulated effect is a mechanism (endorsers know reliability, withdraw from unreliable borrowers after a shock, and help reliable ones catch up a month after an EMI bounces), not a measured real-world effect. Real rows have no vouches. Prosper rows are US, 2005-2014, cheap-talk endorsements and git-ignored; check Prosper's data terms before use beyond this prototype.
- **By:** Reehan

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
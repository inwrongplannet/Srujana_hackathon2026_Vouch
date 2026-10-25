# Option A — Market-shock vouch dataset: what to build

**Status:** Active data generation specification & ML exploration blueprint.  
**Implementation Alignment:** The shock definitions, adverse event reason codes, and post-shock resilience metrics specified here are operationalized in production inside `backend/src/veritrust/stress_tester.py` (Monte Carlo stochastic stress tester), `counterfactual.py` (what-if sensitivity analysis), and `audit_explorer.py` (forensic rule evaluation and evidence trace).  
**Question this data must answer:** *When a borrower's bureau score drops sharply, but their vouch score stays high, does the vouch score carry real information that the bureau score lost — and why?*

Today's dataset cannot answer it at all (see §1). This document defines the minimum data that can.

---

## 1. Why the current dataset fails

| Gap | Present state | Consequence |
|---|---|---|
| No bureau score | no score column anywhere | "CIBIL tanked" is undefined |
| No score trajectory | one static 24-month aggregate + `dpd_grid` | no before/after, no drop date |
| No adverse-event record | aggregates only | "why it dropped" has no source |
| Vouches static | `vouches.csv` has no timestamp, status, weight, or outcome | "vouch stayed high" is unmeasurable |
| Vouch coverage | 10,803 rows, **simulated only**; 4,715/20,000 borrowers; 0/30,000 real | cannot train on real, cannot test on real |
| No vouch → loan link | no `application_id`, no settled outcome, no endorser reputation | reputation update `delta = lr·w·(y−p)` cannot run |
| No post-shock behaviour | outcomes are one 12-month label | cannot show the vouch was *right* |
| Association is weak | bad bureau ± vouch: 541 vs 1,436 borrowers, −2.2pp (p=0.245); stricter cut −5.8pp (p=0.052) | not demo-able |

---

## 2. Definitions the generator must make measurable

These are operational definitions, not prose. Every downstream metric depends on them.

**Shock event.** A borrower-month `t_s` where `bureau_score(t_s) - bureau_score(t_s - 3) <= -50` points, and at least one `bureau_events` row exists in `(t_s-3, t_s]`.
- Drop is measured on the score, not on DPD, so it survives a restructure.
- Signed reason codes must explain the drop (gate §7.4).

**Vouch held.** `vouch_score(t_s) >= pre_shock_vouch_score - 5` **and** `vouch_score(t_s) >= 50`.
- Both conditions: absolute floor stops "vouch held at 12/100" counting.
- `pre_shock_vouch_score` = value at `t_s - 3`.

**Why (mechanism).** Three testable statements, in this order:
1. bureau score is a function of *realised* repayment events, so a shock moves it;
2. vouch score is a function of *latent* reliability and community support capacity, which the shock does not directly change;
3. post-shock default depends on latent reliability and support, so `P(default | shock, vouch high) < P(default | shock, vouch low)` **conditional on pre-shock bureau score and shock severity**.

That is the entire product claim. If (3) does not hold after conditioning, the story is false and the demo must not claim it.

---

## 3. New tables

All new tables are **simulated-only** (`source='simulated'`). Real rows keep what they have; their bureau trajectory can be *derived* from the existing 24-cell `dpd_grid` in `bureau_tradelines.csv` without new data (§6).

Money stays **integer paise**. Months are `YYYY-MM`. Empty cell = missing, with a `*_status` reason code. Every table carries `source` and `borrower_id` for join safety.

### 3.1 `bureau_snapshots.csv` — monthly score trajectory
`rows ≈ 20,000 × 24 = 480,000`

| Column | Type | Meaning |
|---|---|---|
| `source`, `borrower_id` | str | join keys |
| `snapshot_month` | `YYYY-MM` | monthly, 24 consecutive months ending at `application_month` |
| `bureau_score` | int 300–900 | **synthetic score**, monotone in realised delinquency; never presented as a real CIBIL value |
| `score_band` | str | `POOR/FAIR/GOOD/VERY_GOOD/EXCELLENT` |
| `score_change_3m` | int | current − value 3 months earlier |
| `max_dpd_24m` | int | as of this snapshot |
| `months_30plus_24m` | int | as of this snapshot |
| `active_tradelines` | int | |
| `total_outstanding_minor` | int | |
| `utilisation` | decimal str (4 dp) | outstanding / sanctioned |
| `enquiries_6m` | int | |
| `new_tradelines_6m` | int | |
| `written_off` | int | |
| `snapshot_status` | str | `OBSERVED` \| `NO_FILE` \| `THIN_FILE` |
| `top_reason_codes` | pipe list | ≤3 codes from §3.2 driving this month's change |

### 3.2 `bureau_events.csv` — why the score moved
`rows ≈ 60,000 (≈3 per shocked borrower)`

| Column | Type | Meaning |
|---|---|---|
| `event_id`, `borrower_id` | str | |
| `event_month` | `YYYY-MM` | |
| `event_type` | enum | `DPD_30`, `DPD_60`, `DPD_90`, `UTILISATION_JUMP`, `NEW_ENQUIRY`, `WRITE_OFF`, `SETTLEMENT`, `LIMIT_CUT` |
| `magnitude_points` | int (±) | contribution to the score change |
| `linked_tradeline_id` | str, nullable | points at `bureau_tradelines.tradeline_id` |
| `reason_code` | str | one of the PDF's codes: `UTILISATION_SPIKE`, `OBLIGATION_INCREASE`, `BUREAU_DELINQUENCY`, `NEW_CREDIT_SEEKING`, `WRITE_OFF` |
| `evidence_ref` | str | row/segment id, no raw text |
| `verified` | 0/1 | |

This table is the only legitimate source for "why". Without it, explanations must say *purpose unverified*.

### 3.3 `vouch_events.csv` — time-indexed endorsements
`rows ≈ 45,000` (created/renewed/withdrawn/expired/disputed)

| Column | Type | Meaning |
|---|---|---|
| `vouch_event_id`, `borrower_id`, `voucher_id` | str | directed edge voucher → borrower |
| `action` | enum | `CREATED`, `RENEWED`, `WITHDRAWN`, `EXPIRED`, `DISPUTED`, `UPHELD`, `REVOKED` |
| `event_month` | `YYYY-MM` | |
| `relationship` | enum | `COLLEAGUE`, `FAMILY`, `COMMUNITY`, `TRADE`, `NEIGHBOUR` |
| `months_known` | int | |
| `commitment_minor` | int | exposure the voucher stakes (₹, never transferred) |
| `consented` | 0/1 | |
| `expires_month` | `YYYY-MM` | |

State at any month is derivable by replaying events (`CREATED` minus `WITHDRAWN/EXPIRED/REVOKED`). No mutable "current" row — replay is what makes "vouch was high *at the time of the shock*" auditable.

### 3.4 `vouch_scores.csv` — monthly graph output
`rows ≈ 480,000`

| Column | Type | Meaning |
|---|---|---|
| `source`, `borrower_id`, `snapshot_month` | | |
| `vouch_score` | int 0–100 | per `dual-axis-scoring` §6 formula |
| `vouch_status` | enum | `PROVISIONAL` \| `ESTABLISHED` \| `NO_RECORD` |
| `eligible_incoming` | int | count of active, consented, in-limit edges |
| `total_weight` | decimal str (6 dp) | `W = Σ w_xy`, Decimal only |
| `distinct_anchors` | int | anchors reachable |
| `max_contributor_share` | decimal str (4 dp) | largest single endorsement / W |
| `reciprocal_edges` | int | |
| `cluster_concentration` | decimal str (4 dp) | share of W from the densest cluster |
| `algorithm_version` | str | e.g. `vouch-v0.2` |

### 3.5 `vouch_outcomes.csv` — sanctions the reputation story
`rows ≈ 12,000 (one per vouch attached to a loan)`

| Column | Type | Meaning |
|---|---|---|
| `vouch_event_id`, `application_id`, `borrower_id`, `voucher_id` | | |
| `loan_status` | enum | `SETTLED`, `DEFAULTED`, `ONGOING`, `DISPUTED` |
| `settled_month` | `YYYY-MM` | |
| `y` | 0/1 | verified acceptable outcome |
| `p_expected` | decimal str (4 dp) | expected rate at endorsement time |
| `delta_reputation` | decimal str (6 dp) | `lr · w · (y − p) · reliability` |
| `dispute_status` | enum | `NONE`, `OPEN`, `UPHELD`, `REJECTED` |

`y=0` must never move reputation while `dispute_status='OPEN'` (PDF acceptance criterion 6).

### 3.6 `loan_performance.csv` — post-application months
`rows ≈ 20,000 × 12 = 240,000`

| Column | Type | Meaning |
|---|---|---|
| `application_id`, `borrower_id`, `month` | | month index 1..12 |
| `due_minor`, `paid_minor` | int | |
| `dpd_days` | int | |
| `status` | enum | `ON_TIME`, `LATE`, `MISSED`, `SETTLED`, `CHARGED_OFF` |
| `shock_active` | 0/1 | shock fell inside this month |
| `support_received_minor` | int | community/family inflow, from `perf_informal_support_minor` |

This is what lets us show *recovery*, not just a label.

### 3.7 `shock_events.csv` — the event table under analysis
`rows ≈ 3,000`

| Column | Type | Meaning |
|---|---|---|
| `shock_id`, `borrower_id` | | |
| `shock_month` | `YYYY-MM` | must be inside the 12-month performance window |
| `shock_type` | enum | `MEDICAL`, `JOB_LOSS`, `CROP`, `BUSINESS_DISRUPTION`, `FAMILY` |
| `severity` | 1–3 | |
| `insured` | 0/1 | |
| `bureau_drop_points` | int | negative |
| `pre_bureau_score`, `post_bureau_score` | int | |
| `pre_vouch_score`, `post_vouch_score` | int | |
| `vouch_held` | 0/1 | per §2 |
| `support_mobilised_minor` | int | |

---

## 4. The generator's causal structure

Order matters: each arrow must exist in code, or the demo claim is unearned.

```text
latent traits (already present): discipline, save_rate, inflator, stacker, macro_exposed, community
        │
        ├──► realised repayment (pre-application) ──► bureau_score        [bureau sees events]
        │
        ├──► community support capacity ──► vouch graph ──► vouch_score    [vouches see traits]
        │
        └──► shock (type, severity, insurance) ──► liquidity crunch
                     │
                     ├──► bureau_score drops (DPD events)      ← bureau loses information
                     ├──► vouch_score unchanged (no new info about latent traits)
                     └──► default risk rises by (severity − support − discipline)
```

Three properties the generator must guarantee, each with a test:

1. **Orthogonality of information.** `corr(bureau_score, vouch_score) < 0.5` at `t_s-3`. If they correlate highly, the vouch adds nothing and the model will show no increment.
2. **Shock endogeneity.** The shock must move the bureau score *without* moving latent discipline. Implement by making pre-shock repayment clean for shocked borrowers (no random DPD before `t_s`).
3. **Support heterogeneity.** Vouch-holders must have a *plausible* mechanism, not a magic label: vouchers must be able to mobilise `support_mobilised_minor` (drawn from `perf_informal_support_minor`, scaled by `total_weight`). This is what makes "why" answerable in prose that references evidence.

**Anti-artifact rule.** The vouch score must be computed from `vouch_events` **as of the application month**, using only pre-application data. It must never read `loan_performance`, `outcomes`, or the same borrower's outcome. Otherwise the increment is leakage and the whole result is worthless.

---

## 5. Sample size: what "enough" means

Two-sided two-proportion test, α=0.05, power=0.80, baseline post-shock default 20%.

| Effect to detect | n per arm | Shocked borrowers needed (50% vouch coverage) |
|---|---|---|
| 8 pp (20% → 12%) | 330 | 660 |
| 6 pp (20% → 14%) | 580 | 1,160 |
| **4 pp (20% → 16%)** | **1,450** | **2,900** |
| 2 pp | 5,800 | 11,600 |

**Target: 3,000 shocked borrowers** (15% of 20,000), ~1,500 per arm → detects 4 pp at 80% power, and leaves ≈250 defaults in the high-vouch cell.

Second requirement, for the *model* claim (vouch adds AUC beyond bureau):

| Need | Value | Why |
|---|---|---|
| Test rows for stable ΔAUC | ≥ 12,000 | 400 paired bootstraps on 4,000 rows gives a ±0.02 CI — too wide |
| Solution | keep 20k simulated, evaluate the increment with **5-fold CV over all simulated rows** | paired comparison, no split noise |

If either target is missed, the demo must say "underpowered" rather than quote a number.

---

## 6. What we can build on real rows

No new data. `bureau_tradelines.dpd_grid` already has 24 monthly cells (`000`/`030`/`060`/`090`/`XXX`/`---`). Reconstruct a **delinquency trajectory** (not a score) per real borrower:

- `bureau_snapshots_real.csv`: `borrower_id, snapshot_month, worst_dpd_active, months_30plus_rolling, active_tradelines, new_tradelines_6m`
- Label it `score_status = NO_SCORE_AVAILABLE` — never fabricate a score.
- Use it for: (a) a real-data "delinquency spike" feature, (b) a fairness check that thin-file borrowers are not penalised for an empty history.

Real rows still get **no vouches**. That is honest and must stay visible in the UI.

---

## 7. Validation gates — all must pass before any demo claim

| # | Gate | Pass criterion |
|---|---|---|
| 1 | Shock definition is real | ≥95% of shocked borrowers show `score_change_3m <= -50`, and every drop has ≥1 `bureau_events` row in the window |
| 2 | Information orthogonality | `|corr|` between `bureau_score` and `vouch_score` at `t_s-3` < 0.5 |
| 3 | Conditional association | After stratifying on pre-shock bureau score band **and** severity: default(high vouch) − default(low vouch) ≤ −4 pp, 95% CI excludes 0 |
| 4 | Dose–response | Default rate falls monotonically across vouch-score quartiles among shocked borrowers |
| 5 | Model increment | Bureau+shock model vs +vouch features: ΔAUC ≥ 0.02, paired-bootstrap CI excludes 0 (5-fold CV over all simulated rows) |
| 6 | Placebo / no artifact | Randomly permuting `vouch_score` across borrowers → |ΔAUC| < 0.005. If the increment survives shuffling, it is a bug |
| 7 | Leakage sweep | No feature derived from `loan_performance`, `vouch_outcomes`, `shock_events.vouch_held`, or same-borrower outcomes |
| 8 | Explanation grounding | ≥90% of generated reason codes cite an existing `bureau_events.reason_code` or a status field; zero free-text causes |
| 9 | Graph invariants | Out-degree conservation (`Σ W_uv = C_u`), per-path cycle absorption, `max_contributor_share < 0.35` |
| 10 | Determinism | Two runs byte-identical (`sha256` in `manifest.json`) |
| 11 | Calibration | Post-shock predicted vs observed default within ±2 pp per decile on simulated |
| 12 | Reputation safety | `y=0` with `dispute_status='OPEN'` produces `delta_reputation = 0` |

Tests live in `backend/tests/test_shock_data.py` (one test per gate). A gate that fails blocks the pitch slide, not just the build.

---

## 8. Feature contract for the ML stage

New feature groups, all **as-of `shock_month`** (or `application_month` for the base model):

| Group | Columns |
|---|---|
| Bureau state | `pre_bureau_score`, `bureau_drop_points`, `max_dpd_24m_at_t`, `utilisation_at_t`, `enquiries_6m_at_t` |
| Bureau change | `score_change_3m`, `new_tradelines_6m`, `event_count_3m`, `top_reason_code` (categorical) |
| Vouch state | `pre_vouch_score`, `vouch_score_at_t`, `vouch_held`, `eligible_incoming`, `total_weight`, `distinct_anchors` |
| Vouch quality | `max_contributor_share`, `reciprocal_edges`, `cluster_concentration`, `voucher_mean_on_time` |
| Shock | `shock_type` (categorical), `severity`, `insured` |

Banned from features: `vouch_held` when scoring the base model (it is the treatment), any `loan_performance` field, `delta_reputation`, `y`, `default_driver`.

Two models to report:
- **B0**: bureau + cash-flow only → simulates a conventional lender.
- **B1**: B0 + shock + vouch features → the Vouch claim.

The deliverable is the **paired** comparison on identical test rows, not two independent AUCs.

---

## 9. Files that change

| File | Change |
|---|---|
| `backend/src/veritrust/synth/generate.py` | emit shock events + post-application performance |
| `backend/src/veritrust/synth/bureau.py` *(new)* | monthly score trajectory + adverse events |
| `backend/src/veritrust/synth/vouch.py` *(new)* | vouch event graph, replayable state, score v0.2 |
| `backend/src/veritrust/synth/features.py` | as-of joins for both models |
| `backend/src/veritrust/combine.py` | add 7 tables to the bundle + manifest hashes |
| `backend/src/veritrust/synth/validate.py` | gates 1–12 |
| `backend/tests/test_shock_data.py` *(new)* | gate tests |
| `data/combined/README.md` | document new tables, definitions §2, power §5, limitations |
| `docs/DECISIONS.md` | decision entry: synthetic bureau score, shock prevalence, vouch coverage target |
| `backend/ml/data.py` | feature groups §8, banned list |

Existing 50,000 borrowers and all current tables stay stable — new tables are additive, so `ml/` keeps working while this lands.

---

## 10. Effort

| Step | Estimate |
|---|---|
| Spark: shocks + `loan_performance` + `shock_events` | 1.5 h |
| Bureau score trajectory + adverse events | 2.0 h |
| Vouch event graph + monthly score replay | 3.0 h |
| Vouch outcomes + reputation update | 1.0 h |
| As-of feature joins (leakage-safe) | 1.5 h |
| Validation gates 1–12 | 2.0 h |
| Regenerate 50k + verify hashes + docs | 1.0 h |
| **Total** | **~12 h** |

**Minimum viable slice (A1), ~5.5 h:** §3.1–3.4 + §3.7, skip `loan_performance` and `vouch_outcomes`; use the existing `default_12m` label as the post-shock outcome. Answers the association question and gates 1–5, 7, 9, 10. Cannot show recovery or reputation updates.

---

## 11. What we can and cannot claim afterwards

Can say:
- "In this synthetic mechanism, a bureau-score drop destroyed information that the vouch score still carried; conditional on pre-shock bureau band and shock severity, default was X pp lower for vouch-holders."
- "The model improves by ΔAUC on identical rows; the increment vanishes under a permutation placebo."
- "Every explanation cites a bureau event or a status field."

Cannot say:
- that the effect is causal in the real world;
- that the score is a probability of repayment;
- anything about real Indian borrowers — real rows have no vouches;
- that X pp is a validated lending result.

---

## 12. Open questions for you

1. **Score realism:** synthetic `bureau_score` 300–900, or a 1–100 "bureau strength index"? A fake CIBIL number risks the pitch looking fabricated; an index loses recognisability.
2. **Shock prevalence:** 15% of simulated borrowers (3,000) is enough for 4 pp power but is high versus reality. Accept, or lower it and accept a weaker claim?
3. **A1 vs full:** ship the 5.5 h slice now, or block on the 12 h version with recovery + reputation?
4. **Real-row trajectory:** spend the ~1 h to derive `bureau_snapshots_real` from `dpd_grid`? It is the only way to show a real-data before/after.

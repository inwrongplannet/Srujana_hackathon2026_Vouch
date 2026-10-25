# Combined credit-assessment dataset

Sixty-five thousand loan applicants and 113,937 real peer-to-peer loans in one set of tables for F-04:
- 30,000 real Home Credit applicants with synthetic bank statements.
- 35,000 simulated Indian borrowers whose hidden truth is known: a 20,000 population plus a 15,000 shock-study cohort.
- 113,937 real Prosper loans with credit scores, endorsements and outcomes.

It also answers one question end to end: *when a borrower's bureau score falls after a shock but their vouch score holds, does the vouch still predict repayment, and why?*

> Illustrative data, not financial advice. The `real_anchored` and `real_prosper` rows are real, anonymised records. This folder is git-ignored: only this README is committed. Never commit the CSVs, share them outside the team, or paste rows into a prompt.

## At a glance
| | `real_anchored` | `simulated` (main) | `simulated` (shock study) | `real_prosper` |
|---|---|---|---|---|
| Rows | 30,000 applicants | 20,000 applicants | 15,000 applicants | 113,937 loans |
| Default rate | 8.19% | 6.7% | 11.4% | 30.8% of 54,715 resolved |
| Label | Home Credit `TARGET` | 90+ days past due within 12 EMIs | same | charged off, defaulted or 120+ days past due (`bad`) |
| Use it to | train and calibrate | evaluate, stress-test, measure the vouch | answer the shock question | check endorsements on real outcomes |
| Monthly bureau and vouch trajectories | real delinquency trajectory, no score | yes | yes | score at listing, change since last loan |
| Vouches | none | yes | yes | real endorsements (no stake) |

Every row in every table carries `source`. Borrower ids never collide: `H` + Home Credit id, `B` + six digits for simulated rows (`B5xxxxx` for the shock study), `P` + six digits for Prosper loans.

## Recommended use
1. Fit models and calibrate conformal prediction on `real_anchored` rows only.
2. Evaluate, stress-test and check fairness on the simulated `main` cohort; weight by `sample_weight` when you report population rates.
3. Answer the shock question on the `shock_study` cohort (a designed sample, no weights) and check it against `prosper_loans.csv`.
4. Never pool labels from different sources in one fit: each source defines default differently.
5. Use only `features.csv` (or the observed tables) as model input. `answer_key.csv` and the hidden columns of `shock_events.csv` (`vouch_held`, `support_*`) must never reach a model.
6. Split by borrower, not by row.

## What is real and what is synthetic
| Part | `real_anchored` | `simulated` | `real_prosper` |
|---|---|---|---|
| Applicant, income, loan asked for | Real | Simulated | Real (US) |
| Bureau tradelines and 24-month payment grids | Real | Simulated | Not present |
| Month-by-month bureau state | Real delinquency trajectory (`bureau_trajectory`), no score | Illustrative 300-900 score with events (`bureau_snapshots`, `bureau_events`) | Score band at listing and change since the previous Prosper loan |
| Repayment history with the lender (`hc_*`) | Real | Not present | Prior Prosper loans and on-time payments |
| Default label | Real | Emerges from simulated cash flow | Real |
| Bank statements, GST, declared EMIs | Synthetic, from the person's real columns, never from the label | Simulated | Not present |
| Endorsements | None | Time-stamped vouch graph with stakes, renewals and withdrawals | Real recommendations and friend investments |
| Shocks | None recorded | Planned shocks (medical, job loss, crop, business, family) | Not recorded |

How the real Home Credit rows got their statements: income from the applicant's real income with Berka-calibrated volatility; EMIs from real annuities and instalments; a bounce only in months the person's real records show a late or short payment.

## Tables
| File | One row per | Rows |
|---|---|---|
| `applications.csv` | applicant | 65,000 |
| `features.csv` | applicant (the model row, as of the application month) | 65,000 |
| `outcomes.csv` | applicant | 65,000 |
| `answer_key.csv` | applicant (hidden truth; never a model input) | 65,000 |
| `monthly_cashflow.csv` | statement month | 428,490 |
| `bureau_tradelines.csv` | credit line | 224,389 |
| `gst_filings.csv` | GST month of a registered business | 69,732 |
| `vouches.csv` | vouch active at application (simulated) | 75,642 |
| `transactions.csv` | bank statement line (sample of 300 applicants per source) | 115,377 |
| `bureau_snapshots.csv` | simulated borrower-month (24 each) | 840,000 |
| `bureau_events.csv` | event that moved a simulated score | 91,797 |
| `vouch_events.csv` | endorsement event | 252,317 |
| `vouch_scores.csv` | simulated borrower-month (24 each) | 840,000 |
| `vouch_outcomes.csv` | endorsement active when the loan was taken | 71,235 |
| `loan_performance.csv` | month of the applied-for loan (12 each) | 420,000 |
| `shock_events.csv` | shocked simulated borrower | 18,062 |
| `bureau_trajectory.csv` | real borrower-month (24 each, applicants with a file) | 616,824 |
| `prosper_loans.csv` | Prosper loan | 113,937 |
| `manifest.json` | the folder | row counts, SHA-256 of every file, label definitions |

Units: money is integer minor units in every `*_minor` column (paise, or US cents in `prosper_loans.csv`, which carries `currency`). Real Home Credit amounts are rescaled by 0.17 so the median applicant earns about 25,000 INR a month. Ratios are 4-decimal strings. Months are `YYYY-MM`. An empty cell is missing, and the matching `*_status` column says why.

## The shock question
**Answer, in the simulated world: yes.** When the bureau score fell 50+ points after a shock and the vouch held, default was 12.1 points lower, holding the pre-shock score band and shock severity fixed (95% CI 10.2 to 14.0). The real Prosper data points the same way, on far fewer cases.

| Bureau-shocked borrowers (5,695) | Borrowers | Default | Help from endorsers (median) |
|---|---|---|---|
| Vouch held (score stayed within 5 points and at least 50) | 476 | 3.6% | ₹5,616; 72% got some |
| Had vouches, but they did not hold | 2,215 | 12.0% | ₹3,063; 63% got some |
| No vouches | 3,004 | 17.6% | none |

**Why the vouch holds when the bureau score falls.** These are the generator's causal rules, so every arrow can be inspected:
1. The bureau score moves only on recorded events: a missed EMI (`DPD_30`), new enquiries and new lines taken to bridge the gap, and higher utilisation. Every point lost cites a `bureau_events` row.
2. The vouch score moves only when endorsers act. They know the borrower's real reliability, which no bureau sees. After a shock, each endorser walks away with probability 0.55 × (1 − discipline)², so reliable borrowers keep their endorsers and unreliable ones lose them (`WITHDRAWN` events).
3. Endorsers also help, but only once trouble is visible: the month after an EMI bounces, the network covers dues and arrears with probability 1 − e^(−W). So the shock still reaches the bureau, and the network decides how fast the borrower recovers. `loan_performance.support_received_minor` records the help.

**In real data (Prosper, 54,715 resolved loans, aggregates in `prosper_check.json`):**
- Within the same credit-score band, endorsed borrowers default 4.4 points less, in line with Freedman and Jin's published 4.1.
- Where the score had already fallen 20+ points, endorsed borrowers defaulted at 21.5% (261 loans) against 30.5% (3,069).
- Where it fell 50+ points, the rates were 22.7% (66 loans) against 36.4% (1,231): suggestive, but too few loans to rely on.
- These endorsements carried no stake, so they are a lower bound for a staked vouch.

**What may not be claimed:** that the effect is causal in the real world, that the simulated 12 points is a real-world size, that a Vouch Score is a probability of repayment, or anything about real Indian borrowers (real rows have no vouches).

## Columns

### `applications.csv`
| Column | Meaning |
|---|---|
| `source`, `borrower_id` | Row origin and applicant id |
| `application_month` | Month the loan was applied for |
| `occupation` | Simulated: `salaried_formal`, `gig_platform`, `kirana_msme`, `smallholder_farmer`, `informal_daily_wage`. Real: Home Credit income type |
| `occupation_type` | Real only: Home Credit job title (missing for about 31%) |
| `state`, `urban` | Simulated: Indian state code. Real: no state; `urban` is 1 for the best-rated region |
| `age_band`, `dependents` | Age band; number of dependents (children for real rows) |
| `product`, `requested_amount_minor`, `tenure_months`, `rate_annual`, `new_emi_minor`, `currency` | The loan asked for. Real rows: no rate, tenure estimated as amount / EMI |
| `declared_income_minor`, `declared_income_status` | Monthly income stated on the form; `WITHHELD` when left blank |
| `declared_emi_minor`, `declared_emi_status` | Existing EMIs the applicant listed (can understate) |
| `occupation_tenure_months`, `occupation_tenure_status` | Months in the current occupation |
| `bank_statement_status` | `OBSERVED` (12 months shared), `PARTIAL` (3 or 6), `NOT_PROVIDED` |
| `legacy_decision`, `legacy_reason` | What a bureau-only lender would decide, and why |
| `cohort`, `sample_weight` | Simulated: `main` or `shock_study`; weight that undoes shock oversampling (main only) |
| `recommended_use` | `train_and_calibrate` or `evaluate_and_stress_test` |

### `features.csv` (the model row)
Built only from the observed tables as of the application month, never from `answer_key.csv` or any outcome.

| Group | Columns | Meaning |
|---|---|---|
| Application and source status | as in `applications.csv`, plus `bank_statement_months`, `bureau_status`, `gst_status`, `vouch_status`, `hc_history_status`, `completeness_tier` | Which evidence exists, with reason codes |
| Affordability | `income_basis`, `income_est_minor`, `existing_emi_est_minor`, `dti_est`, `amount_to_income` | DTI = (existing + new EMI) / income |
| Consistency | `declared_to_bank_income`, `undeclared_emi_to_income`, `bank_unreconciled_months`, `bank_last_month_spike` | Declared vs observed |
| Bank statement | `bank_income_median_minor`, `bank_income_cv`, `bank_zero_income_months`, `bank_worst3_to_median`, `bank_emi_recent_minor`, `bank_bounces`, `bank_bounces_3m`, `bank_low_balance_months`, `bank_loan_disbursals_6m`, `bank_surplus_median_minor` | Income level and stability, bounces, near-empty months |
| Bureau grid | `bureau_tradelines`, `bureau_active`, `bureau_history_months`, `bureau_max_dpd_24m`, `bureau_months_30plus_24m`, `bureau_reporting_gaps`, `bureau_new_6m`, `bureau_written_off`, `bureau_emi_minor`, `bureau_outstanding_to_sanctioned` | From the tradelines |
| Bureau score (simulated) | `bureau_score_status`, `bureau_score`, `bureau_score_band`, `bureau_score_change_3m`, `bureau_score_change_6m`, `bureau_worst_change_3m_6m`, `bureau_utilisation`, `bureau_enquiries_6m_at_app`, `bureau_events_3m`, `bureau_top_reason_code` | The month before applying |
| Vouch graph (simulated) | `vouch_score`, `vouch_score_status`, `vouch_score_change_6m`, `vouch_eligible_incoming`, `vouch_total_weight`, `vouch_distinct_anchors`, `vouch_max_contributor_share`, `vouch_reciprocal_edges`, `vouch_cluster_concentration`, `vouch_mean_reliability`, `vouch_withdrawn_6m`, `vouch_count`, `vouch_mean_voucher_on_time` | Replayed from `vouch_events` up to the month before applying |
| Reported shock (simulated) | `shock_reported_status`, `shock_reported_type`, `shock_reported_severity`, `shock_reported_insured` | What the applicant tells the lender (85% of shocked applicants report it); the reported purpose is not verified |
| Real only | `bureau_enquiries_12m`, `bureau_current_overdue_max`, `hc_*`, `owns_realty`, `region_rating` | Home Credit fields |
| Baseline and role | `legacy_decision`, `legacy_reason`, `recommended_use`, `cohort`, `sample_weight` | |

### `bureau_snapshots.csv` (simulated)
`snapshot_month`; `bureau_score` (illustrative 300-900 scorecard, `algorithm_version` `bureau-sim-v1`, never a real bureau value); `score_band` (`POOR` < 550, `FAIR` < 650, `GOOD` < 700, `VERY_GOOD` < 750, `EXCELLENT`); `score_change_3m`; `max_dpd_24m`; `months_30plus_24m`; `active_tradelines`; `total_outstanding_minor`; `utilisation`; `enquiries_6m`; `new_tradelines_6m`; `written_off`; `snapshot_status` (`OBSERVED`, `THIN_FILE` under 6 months of history, `NO_FILE`); `top_reason_codes` (up to three of `BUREAU_DELINQUENCY`, `WRITE_OFF`, `UTILISATION_SPIKE`, `NEW_CREDIT_SEEKING`, `OBLIGATION_INCREASE`). Scorecard points are in `backend/src/veritrust/synth/params.py` (`SCORE_*`).

### `bureau_events.csv` (simulated)
`event_id`, `event_month`, `event_type` (`DPD_30`, `DPD_60`, `DPD_90`, `WRITE_OFF`, `NEW_ENQUIRY`, `NEW_TRADELINE`, `UTILISATION_JUMP`), `magnitude_points`, `linked_tradeline_id`, `reason_code`, `evidence_ref`, `verified`. The only legitimate source for "why the score moved".

### `vouch_events.csv`, `vouch_scores.csv`, `vouch_outcomes.csv` (simulated)
- Events: `vouch_event_id`, `vouch_id`, `action` (`CREATED`, `RENEWED`, `WITHDRAWN`, `EXPIRED`), `event_month`, `expires_month`, `voucher_id` (`V...` endorsers; `R...` ring accounts), `recipient_id`, `relationship`, `months_known`, `voucher_kind` (`PERSON` or `INSTITUTION`), `commitment_points`, `voucher_budget_points`, `utilisation_at_stake`, `consented`. State at any month is a replay of the events. Stakes are reputation points, never money.
- Scores: per month, `vouch_score` = 100 × (1 − e^(−W/3)) with edge weight w = R/100 × h × e^(−U) × g (Vouch scoring proposal); `vouch_status` (`NO_RECORD`, `PROVISIONAL`, `ESTABLISHED`); `eligible_incoming`, `total_weight`, `distinct_anchors`, `max_contributor_share`, `reciprocal_edges` (a reciprocal edge keeps 10% of its quality: the ring penalty), `cluster_concentration`, `mean_voucher_reliability`.
- Outcomes: `loan_status` (`SETTLED`, `DEFAULTED`, `ONGOING`), `y`, `p_expected` (0.92), `edge_weight`, `delta_reputation` = 0.10 × w × (y − p), `dispute_status` (`NONE`, `OPEN`, `UPHELD`, `REJECTED`). Open or upheld disputes and ongoing loans never move reputation.

### `loan_performance.csv` and `shock_events.csv` (simulated)
- Performance: `application_id`, `month` 1..12, `calendar_month`, `due_minor`, `paid_minor`, `dpd_days`, `status` (`ON_TIME`, `LATE`, `MISSED`, `SETTLED`, `CHARGED_OFF`), `shock_active`, `support_received_minor`, `vouch_support_minor`.
- Shocks (answer-key grade): `shock_month`, `stratum`, `shock_type`, `severity` 1-3, `insured`, `expense_minor`, `income_factor`, `shock_months`, `drop_month`, `pre_bureau_score` (month before the shock), `post_bureau_score` (lowest within 3 months), `bureau_drop_points`, `bureau_shock` (drop of 50+ explained by an event), `bureau_score_at_application`, `pre_vouch_score`, `post_vouch_score`, `vouch_held` (post ≥ pre − 5 and ≥ 50), `support_mobilised_minor`, `support_before_application_minor`.

### `bureau_trajectory.csv` (real)
Derived month by month from the real 24-cell grids: `worst_dpd_reported`, `reporting_tradelines`, `not_reported_cells`, `months_30plus_rolling`, `new_tradelines_6m`, `delinquency_spike` (worst DPD rises to 30+ from below within 3 months), `score_status` always `NO_SCORE_AVAILABLE`. No score is invented.

### `prosper_loans.csv` (real)
`listing_month`, `term_months`, `loan_amount_minor` (US cents), `currency` `USD`, `credit_score_lower`/`upper`, `score_change_since_last_loan` and its status, `current_delinquencies`, `delinquencies_last_7y`, `bankcard_utilisation`, `debt_to_income`, `stated_monthly_income_minor`, `income_verifiable`, `employment_status`, `prior_prosper_loans`, `prior_on_time_payments`, `recommendations`, `friends_invested_count`, `friends_invested_minor`, `in_group`, `endorsed`, `loan_status`, `resolved`, `bad`. No Prosper keys or free text are kept.

### Other tables
`outcomes.csv` (`default_12m`, `default_month`, `max_dpd_12m`, `label_definition`), `monthly_cashflow.csv`, `transactions.csv`, `bureau_tradelines.csv` (`dpd_grid`: 24 cells oldest first, `000`/`030`/... days past due, `XXX` not reported, `---` not open), `gst_filings.csv`, `vouches.csv` and `answer_key.csv` keep the shapes described in `data/README.md`. The simulated answer key adds `perf_vouch_support_minor`, `support_capacity` and `shock_planned`.

## Missing values and reason codes
| Code | Meaning | Example |
|---|---|---|
| `OBSERVED` | Present | |
| `PARTIAL` | Shared, but incomplete | 3 of 12 statement months |
| `NO_RECORD` | Does not exist | Never borrowed, so no bureau file; no vouches |
| `NOT_PROVIDED` | Exists, but was not shared | Did not link a bank account; shock not reported |
| `NOT_APPLICABLE` | Does not apply | GST for a salaried person |
| `WITHHELD` | Left blank on purpose; missing not at random | Income blank when income is erratic |

| Gap | `real_anchored` | `simulated` main |
|---|---|---|
| No bureau file | 4,299 (14.3%) | 5,785 (28.9%) |
| Bank statement `NOT_PROVIDED` / `PARTIAL` | 9,606 / 6,081 | 7,812 / 3,650 |
| Income `WITHHELD` | 0 | 1,712 |
| Occupation tenure `NOT_PROVIDED` | 0 | 2,367 |
| No vouch at application | all | 9,012 (45.1%) |

## Key numbers
Default rate (applicants in brackets).

| Group | `real_anchored` | `simulated` main |
|---|---|---|
| Bureau file | 7.8% (25,701) | 6.7% (14,215) |
| No bureau file | 10.6% (4,299) | 6.6% (5,785) |
| Completeness tier 0 / 1 / 2 / 3 | 9.4% / 8.8% / 7.6% / 7.6% | 6.8% / 7.4% / 6.0% / 3.9% |
| Bureau-only policy approves / rejects | 7.4% / 9.6% | 4.7% / 9.4% |
| Real delinquency spike before applying | 10.5% (1,720) vs 7.6% without | |

| Occupation (`simulated` main) | Applicants | Default |
|---|---|---|
| `salaried_formal` | 4,781 | 2.5% |
| `kirana_msme` | 3,640 | 3.1% |
| `smallholder_farmer` | 2,972 | 6.1% |
| `informal_daily_wage` | 5,221 | 9.9% |
| `gig_platform` | 3,386 | 12.0% |

Simulated main cohort: bureau score quartiles 732 / 741 / 763; vouch score quartiles among vouched 24 / 37 / 50. Shocks: 18,062 (medical 7,907, job loss 4,994, family 3,411, business 1,267, crop 483), of which 5,695 became bureau shocks (median drop 76 points).

## Validation
From `backend/`: `python -m veritrust.synth.validate`, `python -m veritrust.synth.shock_validate`, `python -m veritrust.anchor.validate`, `python -m veritrust.anchor.prosper`. They fit throwaway logistic regressions only to test the data.

| Check | Result |
|---|---|
| Real: AUC on real features, then with synthetic statements added | 0.662 → 0.663 (+0.0005): no leakage |
| Simulated: AUC on observed features / on hidden truth | 0.830 / 0.859 (leak alarm at 0.90) |
| Simulated: bureau-only policy rejects everyone without a file | 5,785 rejected; 93.4% of them repaid (real: 4,299 rejected, 89.4% repaid) |
| Duplicate-row / hidden-loan / window-dressing detectors (real) | precision 1.00 / 0.38 / 0.27, recall 0.98 / 0.84 / 0.98 |

Shock-question gates (`shock_validation.json`):

| # | Gate | Result |
|---|---|---|
| 1 | Every bureau shock is a 50+ point drop explained by an event | PASS: 5,695 of 5,695 |
| 2 | Bureau and vouch scores carry different information before the shock (abs corr < 0.5) | PASS: r = −0.02 |
| 3 | Held vs not held, within pre-score band × severity: ≤ −4 points, CI excludes 0 | PASS: −12.1 (−14.0 to −10.2); −8.7 among vouched only |
| 4 | Default falls across vouch-score quartiles | PASS: 17.5% → 11.7% → 8.3% → 5.2% (no vouch 17.5%) |
| 5 | The vouch adds ≥ 0.02 AUC beyond bureau, cash flow and the reported shock (5-fold CV, paired) | **FAIL: +0.013** (CI +0.010 to +0.017); AUC 0.820 → 0.826 with the reported shock → 0.840 with the vouch. A real increment, but below the bar: do not claim 0.02 |
| 6 | Placebo: shuffling the vouch features adds nothing | PASS: −0.0015 |
| 7 | No banned column (vouch_held, outcomes, support, truth) in features or models | PASS |
| 8 | Reason codes cite a bureau event of that reason | PASS: 92.6% of 126,311 |
| 9 | No endorser over budget; utilisation in 0..1; ring-only borrowers score ≤ 10 | PASS: 0 over budget, ring-only max 6 (395 borrowers with ring edges) |
| 10 | Two runs are byte-identical | PASS (tests/test_shock_data.py) |
| 11 | Predicted vs observed default within ±2 points per decile, bureau-shocked borrowers | **FAIL**: up to +10.3 points under-predicted in the riskiest deciles. One model fitted on everyone is miscalibrated for this subgroup: recalibrate before quoting probabilities |
| 12 | Open or upheld disputes never move reputation | PASS: 0 violations |

## Known limitations
- The simulated vouch effect is a mechanism we wrote, calibrated to the direction of real evidence, not a measured real-world effect size. Prosper supports the direction on real loans; only a staked-vouch pilot could measure the size.
- The shock-study cohort is a designed sample (live credit, one shock each). Use it for within-cohort comparisons, not population rates. The main cohort's shock rate is oversampled; `sample_weight` assumes a 5% real six-month incidence of a score-denting shock (an assumption anchored on NSS and PLFS rates, see `docs/DECISIONS.md`).
- Real Home Credit applicants are not Indian; amounts are rescaled and application months are assigned by the builder. Prosper is US data from 2005 to 2014 with cheap-talk endorsements.
- Synthetic statements show that the pipeline works; they cannot prove that bank-statement data improves prediction.
- Berka (Czech, 1993 to 1998) sets volatility shapes only.

## Regenerate
From `backend/`, about 40 minutes including downloads (network and `requirements-data.txt`):

```bash
PYTHONPATH=src python -m veritrust.synth --n 20000 --study 15000 --out ../data/synth --transactions 300
PYTHONPATH=src python -m veritrust.synth.shock_validate --data ../data/synth
PYTHONPATH=src python -m veritrust.anchor.download
PYTHONPATH=src python -m veritrust.anchor.berka
PYTHONPATH=src python -m veritrust.anchor.build --n 30000
PYTHONPATH=src python -m veritrust.anchor.prosper
PYTHONPATH=src python -m veritrust.combine
```

Fixed seed 42. The Home Credit mirror revision and the Prosper file's SHA-256 are pinned in `backend/src/veritrust/anchor/download.py`.

## Sources and licences
| Source | Used for | Terms |
|---|---|---|
| Home Credit Default Risk (Kaggle, 2018), via a Hugging Face parquet mirror | Real applicants, bureau, repayment history, labels | Kaggle competition rules apply; the mirror's tag cannot relicense the original. Check before use beyond this prototype |
| Prosper loan data (113,937 loans, 2005-2014), public mirror | Real endorsements, scores and outcomes | Check Prosper's data terms before use beyond this prototype |
| Berka / PKDD'99, CTU relational repository | Volatility and buffers (aggregates in `berka_calibration.json`) | Public research data |
| Freedman and Jin (NBER w19820); Lin, Prabhala and Viswanathan (Management Science 2013); NSS 75th and 77th rounds; PLFS | Calibration of direction and incidence | Cited, no data copied |
| Simulation | All `simulated` rows | Generated by this repo; no real people |

Design and decisions: `docs/DECISIONS.md` (2026-10-25 entries). Code: `backend/src/veritrust/synth/`, `backend/src/veritrust/anchor/`, `backend/src/veritrust/combine.py`.

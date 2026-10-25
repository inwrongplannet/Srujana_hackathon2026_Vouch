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
| Default rate | 8.19% | 7.9% (5.3% weighted) | 23.3% | 30.8% of 54,715 resolved |
| Label | Home Credit `TARGET` | 90+ days past due within 12 EMIs | same | charged off, defaulted or 120+ days past due (`bad`) |
| Use it to | train and calibrate | evaluate, stress-test, measure the vouch | answer the shock question | check endorsements on real outcomes |
| Monthly bureau and vouch trajectories | real delinquency trajectory, no score | yes | yes | score at listing, change since last loan |
| Vouches | none | yes | yes | real endorsements (no stake) |

Every row in every table carries `source`. Borrower ids never collide: `H` + Home Credit id, `B` + six digits for simulated rows (`B5xxxxx` for the shock study), `P` + six digits for Prosper loans.

## Recommended use
1. Fit models and calibrate conformal prediction on `real_anchored` rows only.
2. Evaluate, stress-test and check fairness on the simulated `main` cohort; weight by `sample_weight` when you report population rates (it undoes both the shock oversampling and the forced pandemics).
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
| Shocks | None recorded | Planned shocks with sourced sizes: NSS hospital costs, PLFS job-loss spells, wedding costs, drought crop loss (business disruption is an assumption) | Not recorded |
| Life conditions | None recorded | A world drawn from published rates: pandemics, floods, heat, droughts, job loss, hospital stays, neighbourhood peers, plus labelled noise (`life_events`) | Not recorded |

How the real Home Credit rows got their statements: income from the applicant's real income with Berka-calibrated volatility; EMIs from real annuities and instalments; a bounce only in months the person's real records show a late or short payment.

## Tables
| File | One row per | Rows |
|---|---|---|
| `applications.csv` | applicant | 65,000 |
| `features.csv` | applicant (the model row, as of the application month) | 65,000 |
| `outcomes.csv` | applicant | 65,000 |
| `answer_key.csv` | applicant (hidden truth; never a model input) | 65,000 |
| `monthly_cashflow.csv` | statement month | 429,756 |
| `bureau_tradelines.csv` | credit line | 220,548 |
| `gst_filings.csv` | GST month of a registered business | 69,648 |
| `vouches.csv` | vouch active at application (simulated) | 75,657 |
| `transactions.csv` | bank statement line (sample of 300 applicants per source) | 110,773 |
| `bureau_snapshots.csv` | simulated borrower-month (24 each) | 840,000 |
| `bureau_events.csv` | event that moved a simulated score | 75,093 |
| `vouch_events.csv` | endorsement event | 252,397 |
| `vouch_scores.csv` | simulated borrower-month (24 each) | 840,000 |
| `vouch_outcomes.csv` | endorsement active when the loan was taken | 71,221 |
| `loan_performance.csv` | month of the applied-for loan (12 each) | 420,000 |
| `shock_events.csv` | shocked simulated borrower | 18,062 |
| `life_events.csv` | logged event in a simulated borrower's life | 131,959 |
| `bureau_trajectory.csv` | real borrower-month (24 each, applicants with a file) | 616,824 |
| `prosper_loans.csv` | Prosper loan | 113,937 |
| `manifest.json` | the folder | row counts, SHA-256 of every file, label definitions |

Units: money is integer minor units in every `*_minor` column (paise, or US cents in `prosper_loans.csv`, which carries `currency`). Real Home Credit amounts are rescaled by 0.17 so the median applicant earns about 25,000 INR a month. Ratios are 4-decimal strings. Months are `YYYY-MM`. An empty cell is missing, and the matching `*_status` column says why.

## The shock question
**Answer, in the simulated world: yes.** When the bureau score fell 50+ points after a shock and the vouch held, default was 20.5 points lower, holding the pre-shock score band and shock severity fixed (95% CI 14.6 to 26.7). The real Prosper data points the same way, on far fewer cases.

| Bureau-shocked borrowers (2,289) | Borrowers | Default | Help from endorsers (median, among those helped) |
|---|---|---|---|
| Vouch held (score stayed within 5 points and at least 50) | 191 | 21.5% | ₹18,612; 74% got some |
| Had vouches, but they did not hold | 886 | 34.7% | ₹14,425; 64% got some |
| No vouches at the shock | 1,212 | 47.9% | 2% got some (from vouches made later) |

Defaults are high here because these are the hardest cases: live credit, a shock that already cost 50+ bureau points, and job-loss spells as long as PLFS re-employment rates imply.

**Why the vouch holds when the bureau score falls.** These are the generator's causal rules, so every arrow can be inspected:
1. The bureau score moves only on recorded events: a missed EMI (`DPD_30`), new enquiries and new lines taken to bridge the gap, and higher utilisation. Every point lost cites a `bureau_events` row.
2. The vouch score moves only when endorsers act. They know the borrower's real reliability, which no bureau sees. After a shock, each endorser walks away with probability 0.55 × (1 − discipline)², so reliable borrowers keep their endorsers and unreliable ones lose them (`WITHDRAWN` events).
3. Endorsers also help, but only once trouble is visible: the month after an EMI bounces, the network covers dues and arrears with probability 1 − e^(−W). So the shock still reaches the bureau, and the network decides how fast the borrower recovers. `loan_performance.support_received_minor` records the help. Endorsers are people too: a disaster that hits the borrower hits each endorser at the same exposure rate, and a hit endorser cannot help that month, so a pandemic (38% of workers lost work in the lockdown) cuts help far more than a local flood (15%).
4. Everything else that happens comes from published rates (next section): pandemics, floods, heat and droughts per world; job loss, re-employment and hospital stays per person; family help when cash runs short; and neighbours whose missed EMIs pull on each other. Deliberate noise (an income walk, drifting discipline, unexplained one-off costs, theft, failed auto-debits) breaks patterns without claiming anything. Every event is in `life_events.csv`.

**Normal times and emergencies.** Every simulated borrower is labelled by what they lived through in the 6 months before applying and during the loan (`answer_key.conditions`): `NORMAL`, `IDIOSYNCRATIC` (a personal emergency: illness, job loss, family, crop, business), `COVARIATE` (a regional disaster that hit many people at once) or `BOTH`. Default, all 35,000 simulated borrowers:

| Conditions | Borrowers | Default | Established vouch | No vouch | Gap |
|---|---|---|---|---|---|
| `NORMAL` | 13,009 | 3.6% | 2.4% | 4.3% | 1.9 points |
| `IDIOSYNCRATIC` | 17,205 | 22.0% | 16.6% | 25.7% | 9.1 points |
| `COVARIATE` | 2,178 | 4.7% | 3.4% | 6.1% | 2.7 points |
| `BOTH` | 2,608 | 28.0% | 20.0% | 33.4% | 13.5 points |

The vouch matters most when things go wrong. It matters least where the shock is shared and mild (floods, droughts, the months after a lockdown), because the endorsers are hit too. Not a gate: these groups are not matched on anything else. The 15,000 shock-study borrowers all carry a planned shock, which is why `IDIOSYNCRATIC` is the largest group.

**In real data (Prosper, 54,715 resolved loans, aggregates in `prosper_check.json`):**
- Within the same credit-score band, endorsed borrowers default 4.4 points less, in line with Freedman and Jin's published 4.1.
- Where the score had already fallen 20+ points, endorsed borrowers defaulted at 21.5% (261 loans) against 30.5% (3,069).
- Where it fell 50+ points, the rates were 22.7% (66 loans) against 36.4% (1,231): suggestive, but too few loans to rely on.
- These endorsements carried no stake, so they are a lower bound for a staked vouch.

**What may not be claimed:** that the effect is causal in the real world, that the simulated 20 points is a real-world size, that a Vouch Score is a probability of repayment, or anything about real Indian borrowers (real rows have no vouches).

## The world, and where every number comes from
Every parameter in `backend/src/veritrust/synth/params.py` carries a label: SOURCED (cited with table or page), DERIVED (arithmetic shown), DESIGN (how much we simulate, undone by weights), CALIBRATED (fitted to a named published outcome), ASSUMPTION (no source found, said so) or NOISE (randomness that claims nothing). The main ones:

| What | Value | Label and source |
|---|---|---|
| Worlds | 40 alternate histories of Jul 2022 to Jul 2026; peers never cross worlds | DESIGN |
| Pandemic (COVID-scale) | 0.142% a month; forced into 30% of worlds, weighted back to the real 6.7% chance over the timeline | SOURCED: Marani et al. 2021, PNAS (one in 59 years) |
| Pandemic worker paths | 57% unaffected, 28% lose work and recover after a 2-month lockdown, 10% out for 8 months, 5% lose work later | SOURCED: State of Working India 2021, Table 3.2 |
| Pandemic earnings change, 6 months after | casual −13%, self-employed −18%, salaried −5%; farming exempt from the lockdown | SOURCED: SWI 2021, Table 4.4; MHA orders |
| Lockdown household income | zero for those who lost work | SOURCED: SWI 2021, p.25 (poorest 20% lost all income) |
| Moratorium | EMIs deferrable for 6 months on 41% of loans open at onset | SOURCED (secondary): RBI Trend and Progress 2019-20 |
| Floods | a state floods in a monsoon month with p = 0.043, reaching 15% of its people, who lose 15.2 of 30 days' income | DERIVED from CWC flood statistics and the Kerala 2018 PDNA |
| Heat | outdoor workers −23.5% in Apr-Jun, made up in the other months (base income is a yearly mean) | DERIVED from ILO 2019, Table 6.2 |
| Drought | 17.9% of years; kharif farm revenue −7% irrigated, −14.3% unirrigated | SOURCED (secondary): IITM; Economic Survey 2017-18 |
| Irrigated share of farmers | 50% | ASSUMPTION |
| Job loss | salaried 0.51%, casual 1.69%, self-employed 0.45% a month; back in work 7.4% a month | DERIVED from PLFS panel flows (Bhattacharya 2021, Table 4) |
| Borrower selection on job loss | x 0.25 | CALIBRATED to Crisil's 2.5% microfinance PAR30 (Dec 2019) |
| Income kept in a job loss | 44% (other earners carry on) | DERIVED: PLFS earner share 0.37 x household size 4.8 (NFHS-3, secondary) |
| Hospital stays | 2.6% rural, 3.4% urban a year; out-of-pocket ₹15,937 / ₹22,031 a case | SOURCED: NSS 75th round, Report 586 |
| Family help when short | 32.8% | SOURCED: Global Findex 2021, India (fin24) |
| Peer pull | a neighbour group of 5; 0.37 extra chance a month of skipping an EMI when every peer is behind | CALIBRATED to Breza 2012: repayment 10-15 points lower |
| Endorser exposure | same as the borrower's for the event; no separate help-shrink coefficient | DERIVED; only 9.2% of informal help is from inside the village (Mobarak and Rosenzweig 2013) |
| Theft | 3.9e-5 a month | SOURCED: NCRB Crime in India 2022 |
| Noise | log-income walk (rho 0.95), discipline drift, unexplained costs 1% a month, failed debits 0.4% a month, harvest scatter | NOISE |

Removed because no source supports them: the scarcity dip, present bias, splurges, windfalls and migration shocks, the savings drain on a shock, and the dated hypothetical heatwave, flood and lockdown. Not found anywhere: a coefficient for how much help shrinks in a shared disaster, windfall frequency, income volatility by occupation, crop-loss rates, annual migration flows.

## Does the world look like the real one?
`python -m veritrust.synth.validate_world` compares the main population against published outcomes it was not tuned to, apart from the one calibration target. Months are whole months, so real PAR30 is two or more unpaid EMIs and PAR90 four or more.

| Check | Target | Simulated | Result |
|---|---|---|---|
| PAR30 in normal worlds, loans a bureau-only lender approves (the calibration target) | 2.5% (Crisil, Dec 2019) | 3.3% | PASS (within 1.5-3.5%) |
| PAR30, 6-12 months into a pandemic, all applicants | 11-15% (Crisil Dec 2020; CRIF Apr-Jun 2021) | 9.9% | MISS, close |
| PAR90, same period | 3.3-4.4% (CRIF 2021) | 3.0% | MISS, close |
| PAR30, same period, approved loans only | 11-15% | 8.0% | MISS |
| Late EMIs in a flood month and the next, against the normal rate | 2x or more (Kerala 2018: 44% vs 3%) | 1.3x | MISS |
| Late EMIs 3-4 months after a flood, against the peak | back within 1-2 months (Northern Arc pools) | 91% of the peak | MISS |
| Weighted share of borrowers living through a pandemic | 6.7% (the real chance) | 6.8% | PASS |
| Peer effect: default with every peer behind minus every peer current | 10-15 points (Breza 2012) | 10.9 points | PASS |

What the misses mean: the pandemic lands close to its targets but slightly mild, and mildest for approved loans; a flood here costs only lost workdays, while real floods also destroy stock and homes, for which we found no per-household figure. Default in pandemic worlds is 12.2% against 6.1% in normal ones.

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
| `cohort`, `sample_weight`, `world_weight` | Simulated: `main` or `shock_study`; `sample_weight` (main only) undoes the shock oversampling and the forced pandemics; `world_weight` is the pandemic part alone |
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
| Public news (simulated) | `regional_events_6m`, `pandemic_months_at_app` | Disasters reported in the borrower's state in the 6 months before applying; months since a pandemic began (empty if none) |
| Baseline and role | `legacy_decision`, `legacy_reason`, `recommended_use`, `cohort`, `sample_weight`, `world_weight` | Weights, not model inputs |

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
`outcomes.csv` (`default_12m`, `default_month`, `max_dpd_12m`, `label_definition`), `monthly_cashflow.csv`, `transactions.csv`, `bureau_tradelines.csv` (`dpd_grid`: 24 cells oldest first, `000`/`030`/... days past due, `XXX` not reported, `---` not open), `gst_filings.csv`, `vouches.csv` and `answer_key.csv` keep the shapes described in `data/README.md`. The simulated answer key adds `perf_vouch_support_minor`, `support_capacity`, `shock_planned`, `world_id`, `world_pandemic_onset`, `pandemic_path`, `irrigated` (farmers), `months_out_of_work`, `discipline_end`, `discipline_change`, `covariate_events`, `noise_events` and `conditions`. `macro_exposed` is 1 when the borrower lived through a covariate event.

### `life_events.csv` (simulated)
`borrower_id`, `month`, `category` (`COVARIATE`, `IDIOSYNCRATIC`, `NOISE`), `event` (`PANDEMIC_LOCKDOWN`, `PANDEMIC_JOB_LOSS`, `MORATORIUM_DEFERRAL`, `FLOOD`, `DROUGHT`; `JOB_LOSS`, `HOSPITAL` and the planned shock types; `THEFT`, `UNEXPLAINED_COST`, `DEBIT_GLITCH`), `phase` (`history` or `loan`). Answer-key grade: never a model input. Events come from each borrower's world and own draws at the rates in the table above; none is dated history.

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
| No bureau file | 4,299 (14.3%) | 5,812 (29.1%) |
| Bank statement `NOT_PROVIDED` / `PARTIAL` | 9,606 / 6,081 | 7,799 / 3,581 |
| Income `WITHHELD` | 0 | 1,753 |
| Occupation tenure `NOT_PROVIDED` | 0 | 2,347 |
| No vouch at application | all | 9,012 (45.1%) |

## Key numbers
Default rate (applicants in brackets).

| Group | `real_anchored` | `simulated` main |
|---|---|---|
| Bureau file | 7.8% (25,701) | 7.7% (14,188) |
| No bureau file | 10.6% (4,299) | 8.4% (5,812) |
| Completeness tier 0 / 1 / 2 / 3 | 9.4% / 8.8% / 7.6% / 7.6% | 9.6% / 7.9% / 7.7% / 3.9% |
| Bureau-only policy approves / rejects | 7.4% / 9.6% | 5.7% / 10.9% |
| Normal world / pandemic world | | 6.1% (13,960) / 12.2% (6,040) |
| Real delinquency spike before applying | 10.5% (1,720) vs 7.6% without | |

| Occupation (`simulated` main) | Applicants | Default |
|---|---|---|
| `smallholder_farmer` | 2,972 | 1.8% |
| `kirana_msme` | 3,640 | 4.5% |
| `salaried_formal` | 4,781 | 5.3% |
| `gig_platform` | 3,386 | 11.5% |
| `informal_daily_wage` | 5,221 | 13.8% |

Simulated main cohort: bureau score quartiles 732 / 742 / 764; vouch score quartiles among vouched 24 / 37 / 50; 14.0% spent at least a month out of work. Shocks: 18,062 (medical 7,882, job loss 5,011, family 3,415, business 1,260, crop 494), of which 2,289 became bureau shocks (median drop 70 points). Unweighted main default is 7.9%; weighted to a 5% shock incidence and the real pandemic chance it is 5.3%.

## Validation
From `backend/`: `python -m veritrust.synth.validate`, `python -m veritrust.synth.validate_world`, `python -m veritrust.synth.shock_validate`, `python -m veritrust.anchor.validate`, `python -m veritrust.anchor.prosper`. They fit throwaway logistic regressions only to test the data.

| Check | Result |
|---|---|
| Real: AUC on real features, then with synthetic statements added | 0.662 → 0.663 (+0.0005): no leakage |
| Simulated: AUC on observed features / on hidden truth | 0.857 / 0.772 (leak alarm at 0.90). The hidden-truth model uses stable traits only, while much of what decides default is now luck drawn later (job loss, a pandemic), whose traces the observed features can see |
| Simulated: bureau-only policy rejects everyone without a file | 5,812 rejected; 91.6% of them repaid (real: 4,299 rejected, 89.4% repaid) |
| Duplicate-row / hidden-loan / window-dressing detectors (real) | precision 1.00 / 0.38 / 0.27, recall 0.98 / 0.84 / 0.98 |

Shock-question gates (`shock_validation.json`):

| # | Gate | Result |
|---|---|---|
| 1 | Every bureau shock is a 50+ point drop explained by an event | PASS: 2,289 of 2,289 |
| 2 | Bureau and vouch scores carry different information before the shock (abs corr < 0.5) | PASS: r = 0.00 |
| 3 | Held vs not held, within pre-score band × severity: ≤ −4 points, CI excludes 0 | PASS: −20.5 (−26.7 to −14.6); −12.8 among vouched only |
| 4 | Default falls across vouch-score quartiles | PASS: 42.8% → 36.9% → 27.3% → 24.3% (no vouch 47.5%) |
| 5 | The vouch adds ≥ 0.02 AUC beyond bureau, cash flow and the reported shock (5-fold CV, paired) | **FAIL: +0.004** (CI +0.002 to +0.005); AUC 0.847 → 0.875 with the reported shock → 0.878 with the vouch. Once the shock itself is reported, most of the signal is in it; the vouch still separates who recovers (gates 3 and 4) but adds little ranking power: do not claim 0.02 |
| 6 | Placebo: shuffling the vouch features adds nothing | PASS: −0.0021 |
| 7 | No banned column (vouch_held, outcomes, support, truth) in features or models | PASS |
| 8 | Reason codes cite a bureau event of that reason | PASS: 91.7% of 89,983 |
| 9 | No endorser over budget; utilisation in 0..1; ring-only borrowers score ≤ 10 | PASS: 0 over budget, ring-only max 6 (364 ring-only rows) |
| 10 | Two runs are byte-identical | PASS (tests/test_shock_data.py) |
| 11 | Predicted vs observed default within ±2 points per decile, bureau-shocked borrowers | **FAIL**: up to +13.8 points under-predicted in the riskiest deciles. One model fitted on everyone is miscalibrated for this subgroup: recalibrate before quoting probabilities |
| 12 | Open or upheld disputes never move reputation | PASS: 0 violations |

## Known limitations
- The simulated vouch effect is a mechanism we wrote, calibrated to the direction of real evidence, not a measured real-world effect size. Prosper supports the direction on real loans; only a staked-vouch pilot could measure the size.
- The shock-study cohort is a designed sample (live credit, one shock each). Use it for within-cohort comparisons, not population rates. The main cohort's shock rate is oversampled; `sample_weight` assumes a 5% real six-month incidence of a score-denting shock (an assumption anchored on NSS and PLFS rates, see `docs/DECISIONS.md`).
- Real Home Credit applicants are not Indian; amounts are rescaled and application months are assigned by the builder. Prosper is US data from 2005 to 2014 with cheap-talk endorsements.
- Synthetic statements show that the pipeline works; they cannot prove that bank-statement data improves prediction.
- Berka (Czech, 1993 to 1998) sets volatility shapes only.
- The world's rates come from published sources, but two values are calibrated (borrower selection on job loss, the peer pull), a few are assumptions (irrigated share, business disruption, school fees) and the noise is invented on purpose. National rates are applied to every state; PLFS job-loss flows are for urban men.
- The pandemic and flood checks miss their targets (see above): use pandemic worlds for direction, not for loss forecasts.

## Regenerate
From `backend/`, about 40 minutes including downloads (network and `requirements-data.txt`):

```bash
PYTHONPATH=src python -m veritrust.synth --n 20000 --study 15000 --out ../data/synth --transactions 300
PYTHONPATH=src python -m veritrust.synth.validate_world --data ../data/synth
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
| Freedman and Jin (NBER w19820); Lin, Prabhala and Viswanathan (Management Science 2013) | Direction of the endorsement effect | Cited, no data copied |
| Marani et al. 2021 (PNAS); Azim Premji University, State of Working India 2021; MHA lockdown orders; RBI Trend and Progress 2019-20; Crisil (Apr 2021) and CRIF High Mark (Dec 2021) microfinance reports | Pandemic hazard, worker paths, earnings, moratorium; outcome targets | Cited, no data copied |
| CWC State-wise Flood Damage Statistics; Kerala PDNA 2019; RBI Bulletin 2020; World Bank blog on Northern Arc pools; ILO 2019 Working on a Warmer Planet; IITM rainfall series; Economic Survey 2017-18 | Floods, heat, drought; flood outcome targets | Cited, no data copied |
| PLFS panel (Bhattacharya 2021, arXiv:2110.05482); NSS 75th round Report 586; Global Findex 2021; NCRB Crime in India 2022; Bloch, Rao and Desai 2004; Tripathi, Shravan and Jayadev 2026; NFHS-3 | Job loss, hospital stays and costs, family help, theft, weddings, household earners | Cited, no data copied |
| Breza 2012; Mobarak and Rosenzweig 2013 | Peer effect target; local share of informal help | Cited, no data copied |
| Simulation | All `simulated` rows | Generated by this repo; no real people |

Design and decisions: `docs/DECISIONS.md` (2026-10-25 entries). Code: `backend/src/veritrust/synth/`, `backend/src/veritrust/anchor/`, `backend/src/veritrust/combine.py`.

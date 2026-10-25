# data/

**Why this exists:** small sample and seed datasets, committed so every teammate and the demo see identical data. Keep files small; no secrets or real personal data.

## Committed
| File | What it is |
|---|---|
| `accounts.json`, `transactions.csv` | Legacy demo seed from `scripts/seed.py` (`make seed`) |

## Generated, never committed (git-ignored)
| Folder | Built by | What it is |
|---|---|---|
| `synth/` | `python -m veritrust.synth` | **Simulated world.** Fully synthetic borrowers whose months are simulated; default emerges from cash flow. The hidden truth is known, so "no history" vs "cannot pay" can be checked. |
| `anchored/` | `python -m veritrust.anchor.build` | **Hybrid.** Real Home Credit applicants (real bureau grids, repayment history, missing values and default label) plus synthetic bank statements generated from each person's real columns. |
| `prosper/` | `python -m veritrust.anchor.prosper` | **Real endorsements.** 113,937 real Prosper loans (US, 2005-2014) with credit score, score change, endorsements and outcome, plus `prosper_check.json`. Real anonymised rows: never commit. |
| `combined/` | `python -m veritrust.combine` | **One dataset.** All three stacked into the same tables, every row tagged `source` (`real_anchored`, `simulated` or `real_prosper`), outcomes tagged `label_definition`, and the answer keys merged into `answer_key.csv`. Fit and calibrate per source; never pool the labels. |
| `external/` | `python -m veritrust.anchor.download` | Raw public sources: Home Credit mirror (pinned revision), Berka and Prosper (pinned SHA-256). Real anonymised rows: never commit, never paste into prompts. |

Commands and requirements: `backend/README.md` (Credit datasets).

## Shared schema (both datasets)
Money is integer paise (`*_minor`) with `currency` INR. Ratios are 4-dp decimal strings. An empty cell is missing and always sits next to a reason code.

| Table | One row per | Key columns |
|---|---|---|
| `applications` | applicant | occupation, age band, loan asked for (amount, tenure, EMI), declared income and EMIs, source statuses, `legacy_decision` (what a bureau-only lender would do) |
| `monthly_cashflow` | statement month | credits, debits, EMI debits, bounces, bounce charges, loan disbursals, opening and closing balance |
| `transactions` | statement line (sample only) | date, narration (NEFT/UPI/NACH/ATM style, fictional names), type `CREDIT`/`DEBIT`/`RETURN`, amount, running balance |
| `bureau_tradelines` | credit line | lender type, opened, sanctioned, EMI, status, outstanding, `dpd_grid` (24 months, oldest first) |
| `gst_filings` | GST month (registered businesses) | `FILED` with turnover, or `MISSED` |
| `vouches` | vouch active at application (simulated only) | relationship, months known, voucher's reliability |
| `outcomes` | applicant | `default_12m` label |
| `features` | applicant | the model row, built only from the tables above as of the application month; `cohort` and `sample_weight` |
| `truth` (simulated) / `injections` (anchored) | applicant | the answer key; never a model input |
| `bureau_snapshots` | borrower-month, 24 per borrower (simulated) | illustrative 300-900 bureau-style score, band, 3-month change, DPD, utilisation, enquiries, top reason codes; `NO_FILE` or `THIN_FILE` status |
| `bureau_events` | event that moved the score (simulated) | `DPD_30/60/90`, `WRITE_OFF`, `NEW_ENQUIRY`, `NEW_TRADELINE`, `UTILISATION_JUMP`, points, reason code, linked tradeline |
| `vouch_events` | endorsement event (simulated) | `CREATED`, `RENEWED`, `WITHDRAWN`, `EXPIRED`; voucher, recipient, stake in reputation points, utilisation |
| `vouch_scores` | borrower-month, 24 per borrower (simulated) | Vouch Score 0-100 replayed from the events; `NO_RECORD`, `PROVISIONAL` or `ESTABLISHED` |
| `vouch_outcomes` | endorsement active when the loan was taken (simulated) | loan status, `y`, expected rate, reputation change, dispute status |
| `loan_performance` | month of the applied-for loan, 12 per borrower (simulated) | due, paid, DPD, status, shock active, support received |
| `life_events` | logged event (simulated) | month, category (`IDIOSYNCRATIC`, `COVARIATE`, `ABSURD`), event (e.g. `FLOOD_KA_MH`, `WINDFALL`, `TECHNICAL_BOUNCE`), phase (history or loan); answer-key grade, never a model input |
| `shock_events` | shocked borrower (simulated) | type, severity, insured, bureau drop, pre/post bureau and vouch scores, `vouch_held`, support mobilised (answer-key grade: never a model input) |
| `bureau_trajectory` | borrower-month (anchored) | real worst DPD, reporting lines, rolling 30+ months, new lines, delinquency spike; `NO_SCORE_AVAILABLE` |
| `prosper_loans` | loan (Prosper) | credit score band, score change since last loan, delinquencies, endorsements, outcome (`bad`) |

Simulated rows come in two cohorts (`cohort` column): `main` (20,000, a population; shocks oversampled and reweighted by `sample_weight`) and `shock_study` (15,000 borrowers with live credit, one planned shock each; a designed sample with no weight).

### Reason codes for gaps
| Code | Meaning | Example |
|---|---|---|
| `OBSERVED` | present | |
| `PARTIAL` | shared, but incomplete | 3 of 12 statement months |
| `NO_RECORD` | does not exist | never borrowed, so no bureau file |
| `NOT_PROVIDED` | exists, not shared | did not link a bank account |
| `NOT_APPLICABLE` | does not apply | GST for a salaried person; tenure for a pensioner |
| `WITHHELD` | left blank on purpose; missing not at random | income field blank when income is erratic |

Bureau grid cells: `000`, `030`, `060`, ... days past due; `XXX` not reported that month; `---` account not open.

### Labels
- Simulated: `default_12m` = 90+ days past due (3 unpaid EMIs, the RBI NPA threshold) within the first 12 EMIs.
- Anchored: Home Credit `TARGET` = payment difficulties on the loan's early instalments. Different definition; do not pool the two.

## What is real and what is synthetic (anchored)
- Real: applicant fields, loan asked for, bureau tradelines and grids, instalment-level repayment history (`hc_*` features), refused applications, missing values, label.
- Synthetic, from real columns and never from the label: bank statements (income from real income, EMIs from real annuities and instalments, bounces in the months real records show late or short payment), statement sharing, GST, the declared-EMI field, and flagged injections.
- Calibrated on real Berka accounts: income volatility, balance buffers, zero-income months (`backend/src/veritrust/anchor/berka_calibration.json`, aggregates only).
- Not carried: `EXT_SOURCE_*` (opaque scores) and protected attributes.

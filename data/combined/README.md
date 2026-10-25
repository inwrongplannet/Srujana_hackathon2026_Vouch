# Combined credit-assessment dataset

Fifty thousand loan applicants in one set of tables for F-04: 30,000 real Home Credit applicants with synthetic bank statements, and 20,000 simulated Indian borrowers whose hidden truth is known.

> Illustrative data, not financial advice. The `real_anchored` rows are real, anonymised Home Credit applicants. This folder is git-ignored: only this README is committed. Never commit the CSVs, share them outside the team, or paste rows into a prompt.

## At a glance
| | `real_anchored` | `simulated` | All |
|---|---|---|---|
| Applicants | 30,000 | 20,000 | 50,000 |
| Default rate | 8.19% | 6.98% | |
| Label | Home Credit `TARGET` | 90+ days past due within 12 EMIs | |
| Use it to | train and calibrate | evaluate and stress-test | |
| Application months | 2024-07 to 2025-06 | 2024-07 to 2025-06 | |
| Bank statement months | 199,215 | 118,803 | 318,018 |
| Bureau tradelines | 141,666 | 32,269 | 173,935 |
| Statement lines (sample of 300 applicants each) | 60,933 | 55,742 | 116,675 |

Every row in every table carries `source` (`real_anchored` or `simulated`). Borrower ids never collide: `H` + Home Credit id for real rows, `B` + six digits for simulated rows.

## Recommended use
1. Fit models and calibrate conformal prediction on `real_anchored` rows only.
2. Evaluate, stress-test and check fairness on `simulated` rows, where the truth is known.
3. Never pool the two labels in one fit: they define default differently (see Labels). The `recommended_use` column on `applications` and `features` says which role a row plays.
4. Use only `features.csv` (or the observed tables) as model input. `answer_key.csv` is the hidden truth and must never reach a model.
5. Split by borrower, not by row: `monthly_cashflow`, `bureau_tradelines` and `transactions` have many rows per borrower.

## What is real and what is synthetic
| Part | `real_anchored` | `simulated` |
|---|---|---|
| Applicant, income, employment, loan asked for | Real (Home Credit) | Simulated |
| Bureau tradelines and 24-month payment grids | Real | Simulated |
| Repayment history with the lender (`hc_*`) | Real | Not present |
| Missing values (no bureau file, no history, tenure) | Real | Simulated with causes |
| Default label | Real | Emerges from simulated cash flow |
| Bank statements | Synthetic, generated from the person's real columns, never from the label | Simulated |
| GST filings, declared EMIs, statement sharing | Synthetic | Simulated |
| Planted test cases (hidden loan, window dressing, round-tripping, duplicate rows) | Injected, listed in `answer_key.csv` | Simulated, listed in `answer_key.csv` |
| Vouches | None | Simulated |

How the real rows got their statements:
- Income comes from the applicant's real income, with month-to-month volatility drawn from real Berka bank accounts of the same income style (salary-like transfers, pension, or cash).
- EMI debits come from the applicant's real bureau annuities and real instalments, in the months each loan was actually open.
- A bounce appears in a month only if that person's real records show a late or short payment that month.
- Balance buffers and zero-income months are also drawn from real Berka accounts.

Not carried at all: Home Credit's `EXT_SOURCE_1..3` (opaque external scores) and protected attributes (gender, family status, education).

## Tables
| File | One row per | Rows |
|---|---|---|
| `applications.csv` | applicant | 50,000 |
| `features.csv` | applicant (the model row) | 50,000 |
| `outcomes.csv` | applicant | 50,000 |
| `answer_key.csv` | applicant (hidden truth; never a model input) | 50,000 |
| `monthly_cashflow.csv` | statement month | 318,018 |
| `bureau_tradelines.csv` | credit line | 173,935 |
| `gst_filings.csv` | GST month of a registered business | 56,748 |
| `vouches.csv` | community vouch (simulated only) | 10,803 |
| `transactions.csv` | bank statement line (sample) | 116,675 |
| `manifest.json` | the folder | row counts, SHA-256 of every file, label definitions |

Units everywhere:
- Money is integer paise (INR minor units) in every `*_minor` column. Divide by 100 for rupees. Real Home Credit amounts are rescaled by 0.17, so the median applicant earns about 25,000 INR a month; every ratio is unchanged.
- Ratios are decimal strings with 4 places.
- Months are `YYYY-MM`; dates are `YYYY-MM-DD`.
- An empty cell is missing, and the matching `*_status` column says why.

## Columns

### `applications.csv`
| Column | Meaning |
|---|---|
| `source`, `borrower_id` | Row origin and applicant id |
| `application_month` | Month the loan was applied for |
| `occupation` | Simulated: `salaried_formal`, `gig_platform`, `kirana_msme`, `smallholder_farmer`, `informal_daily_wage`. Real: Home Credit income type (`working`, `commercial_associate`, `pensioner`, `state_servant`, ...) |
| `occupation_type` | Real only: Home Credit job title (missing for about 31%) |
| `state`, `urban` | Simulated: Indian state code. Real: no state; `urban` is 1 for the best-rated region |
| `age_band`, `dependents` | Age band; number of dependents (children for real rows) |
| `product` | Loan applied for (`personal_loan`, `working_capital`, `agri_term`, `micro_loan`; real: `cash_loans`, `revolving_loans`) |
| `requested_amount_minor`, `tenure_months`, `rate_annual`, `new_emi_minor` | The loan asked for. Real rows: no rate, tenure estimated as amount / EMI |
| `currency` | Always `INR` |
| `declared_income_minor`, `declared_income_status` | Monthly income stated on the form; `WITHHELD` when left blank |
| `declared_emi_minor`, `declared_emi_status` | Existing EMIs the applicant listed (can understate) |
| `occupation_tenure_months`, `occupation_tenure_status` | Months in the current occupation |
| `bank_statement_status` | `OBSERVED` (12 months shared), `PARTIAL` (3 or 6), `NOT_PROVIDED` |
| `legacy_decision`, `legacy_reason` | What a bureau-only lender would decide, and why (`NO_BUREAU_HISTORY`, `BUREAU_DELINQUENCY`, `INCOME_NOT_STATED`, `DTI_ABOVE_CAP`) |
| `recommended_use` | `train_and_calibrate` or `evaluate_and_stress_test` |

### `features.csv` (the model row)
Built only from the observed tables, never from `answer_key.csv`. The same code builds a demo persona's row.

| Group | Columns | Meaning |
|---|---|---|
| Application | `application_month`, `occupation`, `occupation_type`, `state`, `urban`, `age_band`, `dependents`, `product`, `requested_amount_minor`, `tenure_months`, `rate_annual`, `new_emi_minor`, `declared_income_minor`, `declared_income_status`, `declared_emi_minor`, `occupation_tenure_months`, `occupation_tenure_status` | As in `applications.csv` |
| Source status | `bank_statement_status`, `bank_statement_months`, `bureau_status`, `gst_status`, `vouch_status`, `hc_history_status` | Which evidence exists, with reason codes |
| Completeness | `completeness_tier` | Independent verified sources (bank statement of 6+ months, bureau file of 6+ months, GST), 0 to 3 |
| Affordability | `income_basis`, `income_est_minor`, `existing_emi_est_minor`, `dti_est`, `amount_to_income` | Income estimate (`BANK`, `DECLARED`, the lower of both, or `NONE`); existing EMIs (largest of declared, bank and bureau); DTI = (existing + new EMI) / income |
| Consistency | `declared_to_bank_income`, `undeclared_emi_to_income`, `bank_unreconciled_months`, `bank_last_month_spike` | Declared vs observed income; EMIs in the statement but not on the form; months whose balance does not reconcile; last month's credits vs the median |
| Bank statement | `bank_income_median_minor`, `bank_income_cv`, `bank_zero_income_months`, `bank_worst3_to_median`, `bank_emi_recent_minor`, `bank_bounces`, `bank_bounces_3m`, `bank_low_balance_months`, `bank_loan_disbursals_6m`, `bank_surplus_median_minor` | Income level and stability, worst months, recent EMI debits, bounced auto-debits, near-empty months, new loans credited, monthly surplus before EMIs |
| Bureau | `bureau_tradelines`, `bureau_active`, `bureau_history_months`, `bureau_max_dpd_24m`, `bureau_months_30plus_24m`, `bureau_reporting_gaps`, `bureau_new_6m`, `bureau_written_off`, `bureau_emi_minor`, `bureau_outstanding_to_sanctioned` | Credit lines, history length, worst days past due, months 30+ overdue, unreported months, new lines in 6 months, write-offs, EMIs, utilisation |
| Bureau (real only) | `bureau_enquiries_12m`, `bureau_current_overdue_max` | Bureau enquiries in the last year; current days overdue |
| Lender history (real only) | `hc_prev_applications`, `hc_prev_refused`, `hc_instalments_12m`, `hc_late_share_12m`, `hc_short_share_12m`, `hc_max_days_late_12m`, `hc_late_share_all` | Real instalment-level repayment record with Home Credit |
| Assets (real only) | `owns_realty`, `region_rating` | Owns property; Home Credit region rating 1 to 3 |
| GST | `gst_turnover_median_minor`, `gst_missed_filings`, `gst_to_bank_credits` | Filed turnover, missed months, GST turnover vs bank credits |
| Vouches (simulated only) | `vouch_count`, `vouch_mean_voucher_on_time` | Number of vouches; vouchers' own on-time record |
| Baseline | `legacy_decision`, `legacy_reason` | Bureau-only decision, for comparison |
| Role | `recommended_use` | See Recommended use |

### `outcomes.csv`
| Column | Meaning |
|---|---|
| `default_12m` | 1 = default (definition in `label_definition`) |
| `default_month`, `max_dpd_12m` | Simulated only: first month 90+ days past due; worst days past due |
| `label_definition` | The label's definition for this row's source |

### `monthly_cashflow.csv`
| Column | Meaning |
|---|---|
| `month` | Statement month |
| `credits_minor`, `debits_minor` | All money in and out |
| `emi_debits_minor` | Loan instalments paid (auto-debit and manual overdue payments) |
| `emi_bounces`, `bounce_charges_minor` | Auto-debits returned for insufficient funds, and the charges |
| `disbursal_credits_minor`, `disbursal_count` | New loans credited to the account |
| `opening_balance_minor`, `closing_balance_minor` | Balances. Opening + credits - debits differs from closing only when the statement has duplicated rows |

### `transactions.csv`
| Column | Meaning |
|---|---|
| `txn_id`, `date`, `narration` | Line id, date and Indian-statement-style narration (`NEFT CR SAL`, `UPI DR`, `NACH DR`, `NACH RTN`, `ATM WDL`). All names are fictional |
| `txn_type` | `CREDIT`, `DEBIT`, or `RETURN` (a bounced auto-debit; does not move the balance) |
| `amount_minor`, `balance_minor` | Amount and running balance (never negative) |

Reading these lines back with the extractor in `backend/src/veritrust/synth/transactions.py` reproduces `monthly_cashflow.csv` to the paisa (tested).

### `bureau_tradelines.csv`
| Column | Meaning |
|---|---|
| `tradeline_id`, `lender_type`, `loan_kind` | Credit line and lender type (`BANK`, `NBFC`, `MFI`, `FINTECH`) |
| `opened_month`, `sanctioned_minor`, `tenure_months` | When it opened, its size and term |
| `status`, `outstanding_minor`, `emi_minor` | `ACTIVE`, `CLOSED` or `WRITTEN_OFF`; balance owed; instalment |
| `dpd_grid` | 24 monthly cells, oldest first, separated by `\|`: `000`, `030`, `060`, ... days past due; `XXX` not reported; `---` not open |
| `emi_basis`, `current_overdue_days` | Real only: whether the EMI was reported or estimated from debt and term; days overdue now |

### `gst_filings.csv` and `vouches.csv`
| Column | Meaning |
|---|---|
| `month`, `status`, `turnover_minor` | GST month, `FILED` or `MISSED`, turnover filed |
| `vouch_id`, `relationship`, `months_known`, `voucher_on_time_share` | Who vouched, for how long they have known the applicant, and the voucher's own repayment record |

### `answer_key.csv` (never a model input)
| Source | Columns | Meaning |
|---|---|---|
| `simulated` | `base_income_minor`, `true_income_median_12m_minor`, `income_cv`, `expense_ratio`, `discipline`, `save_rate`, `deposit_share`, `margin` | Hidden traits behind each borrower |
| `simulated` | `stacker`, `inflator`, `window_dresser`, `round_tripper`, `duplicate_import`, `macro_exposed`, `community` | Hidden behaviours and exposures (1/0) |
| `simulated` | `existing_emi_true_minor`, `undeclared_emi_minor`, `unreported_open_loans`, `true_dti_with_new` | True debt load, including what was hidden |
| `simulated` | `perf_shocks`, `perf_lumpy_costs`, `perf_informal_support_minor`, `perf_new_digital_loans`, `default_driver` | What happened after approval; why a default happened (`STRUCTURAL`, `SHOCK`, `STACKING`, `LIQUIDITY`) |
| `real_anchored` | `style`, `statement_months`, `income_cv`, `deposit_share` | How the synthetic statement was generated |
| `real_anchored` | `hidden_loan_emi_minor`, `forgot_loan_emi_minor`, `window_dressing`, `round_trip`, `duplicate_import`, `true_existing_emi_minor` | Planted test cases and the true EMI load |

## Missing values and reason codes
| Code | Meaning | Example |
|---|---|---|
| `OBSERVED` | Present | |
| `PARTIAL` | Shared, but incomplete | 3 of 12 statement months |
| `NO_RECORD` | Does not exist | Never borrowed, so no bureau file |
| `NOT_PROVIDED` | Exists, but was not shared | Did not link a bank account |
| `NOT_APPLICABLE` | Does not apply | GST for a salaried person; occupation tenure for a pensioner |
| `WITHHELD` | Left blank on purpose; missing not at random | Income blank when income is erratic |

| Gap | `real_anchored` | `simulated` |
|---|---|---|
| No bureau file (`NO_RECORD`) | 4,299 (14.3%) | 5,785 (28.9%) |
| No lender history (`hc_history_status` `NO_RECORD`) | 1,567 (5.2%) | not present |
| Bank statement `NOT_PROVIDED` / `PARTIAL` | 9,606 / 6,081 | 7,825 / 3,646 |
| Income `WITHHELD` | 0 | 1,714 |
| Occupation tenure `NOT_APPLICABLE` / `NOT_PROVIDED` | 5,377 / 0 | 0 / 2,345 |
| No vouches | all | 15,285 |

## Labels
| Source | `default_12m = 1` means | Rate |
|---|---|---|
| `real_anchored` | Home Credit `TARGET`: payment difficulties on the loan's early instalments | 8.19% |
| `simulated` | 90+ days past due (three unpaid EMIs, the RBI NPA threshold) within the first 12 EMIs; it emerges from simulated cash flow, never from a rule | 6.98% |

## Key numbers
Default rate by group (applicants in brackets).

| Group | `real_anchored` | `simulated` |
|---|---|---|
| Bureau file | 7.8% (25,701) | 7.0% (14,215) |
| No bureau file | 10.6% (4,299) | 7.0% (5,785) |
| Completeness tier 0 / 1 / 2 / 3 | 9.4% / 8.8% / 7.6% / 7.6% | 7.2% / 7.9% / 6.1% / 3.7% |
| Bureau-only policy approves / rejects | 7.4% / 9.6% | 5.0% / 9.7% |

| Occupation (`simulated`) | Applicants | Default |
|---|---|---|
| `salaried_formal` | 4,781 | 2.1% |
| `kirana_msme` | 3,640 | 3.1% |
| `smallholder_farmer` | 2,972 | 5.8% |
| `gig_platform` | 3,386 | 11.5% |
| `informal_daily_wage` | 5,221 | 12.0% |

| Occupation (`real_anchored`) | Applicants | Default |
|---|---|---|
| `working` | 15,599 | 9.9% |
| `commercial_associate` | 6,885 | 7.3% |
| `pensioner` | 5,377 | 5.7% |
| `state_servant` | 2,134 | 5.2% |

## Validation
Each check runs from `backend/` with `python -m veritrust.synth.validate` or `python -m veritrust.anchor.validate`. They use a throwaway logistic regression only to test the data; no model is saved.

| Check | Result | What it shows |
|---|---|---|
| AUC, real features only | 0.662 | Baseline difficulty of the real data |
| AUC, real plus synthetic statement features | 0.663 (+0.0005) | The synthetic statements carry no hidden label: no leakage |
| AUC on simulated observed features | 0.829 | Realistic difficulty (leak alarm at 0.90) |
| AUC on simulated hidden truth (oracle) | 0.920 | Even perfect knowledge cannot predict future shocks: real, irreducible uncertainty |
| Simulated: at the same true risk, default with no bureau file vs a file | 0.0% vs 0.1%, 0.1% vs 0.7%, 0.8% vs 1.5%, 3.3% vs 5.0%, 24.7% vs 30.7% (risk quintiles 1 to 5) | Absence of history is not inability to repay |
| Real: bureau-only policy rejects everyone without a file | 4,299 rejected; 89.4% of them repaid | The cost of treating absence as risk |
| Simulated: same policy | 5,785 rejected; 93.0% of them repaid | Same, where the truth is known |
| Real Berka loans: negative-balance penalties in the 12 months before the loan | 32.9% of 76 bad loans vs 0.5% of 606 good loans | Distress is visible in statements before default |
| Duplicate-row detector (`bank_unreconciled_months > 0`) | precision 1.00, recall 0.98 | |
| Hidden-loan detector (`undeclared_emi_to_income > 0.01`) | precision 0.38, recall 0.84 | Recently closed loans also trigger it; needs review, not auto-reject |
| Window-dressing detector (`bank_last_month_spike > 1.8`) | precision 0.27, recall 0.98 | Erratic cash incomes also spike |
| Determinism | Two runs are byte-identical | |

In the real data, applicants without a bureau file do default more (10.6% vs 7.8%). That is selection, not proof: lenders could not screen them before. So the model should widen its uncertainty for them, not reject them.

## Known limitations
- The real applicants come from Home Credit's book (not India). Amounts are rescaled to INR magnitudes and ratios are preserved, but the population is not Indian. The simulated rows are India-shaped.
- Real application months are assigned by the builder: Home Credit publishes no dates. Use the simulated rows for drift tests. Their later cohorts meet a simulated rainfall deficit (Maharashtra, Karnataka and Telangana, harvest of 2025-10 and 2025-11) and a simulated cut in platform incentives (2025-03 to 2025-08). Both events are hypothetical.
- Synthetic statements show that the pipeline works. They cannot prove that bank-statement data improves prediction; only a real Account Aggregator partner dataset can.
- Real bureau EMIs are often missing in the source; some are estimated from debt and term (`emi_basis`).
- Berka is Czech data from 1993 to 1998. It sets the volatility shapes only, never the amounts.

## Regenerate
From `backend/`, about 15 minutes including downloads (needs network and `requirements-data.txt`):

```bash
PYTHONPATH=src python -m veritrust.synth --n 20000 --out ../data/synth --transactions 300
PYTHONPATH=src python -m veritrust.anchor.download
PYTHONPATH=src python -m veritrust.anchor.berka
PYTHONPATH=src python -m veritrust.anchor.build --n 30000
PYTHONPATH=src python -m veritrust.combine
```

Fixed seed 42. The Home Credit mirror revision is pinned in `backend/src/veritrust/anchor/download.py`, so a rebuild matches `manifest.json`.

## Sources and licences
| Source | Used for | Terms |
|---|---|---|
| Home Credit Default Risk (Kaggle competition, 2018), via a Hugging Face parquet mirror | Real applicants, bureau, repayment history, labels | Kaggle competition rules apply. The mirror's Apache-2.0 tag cannot relicense the original. Check the rules before any use beyond this prototype |
| Berka / PKDD'99 financial dataset, CTU relational repository | Volatility, buffers and the early-warning check (aggregates only, in `berka_calibration.json`) | Public research data |
| Simulation | All `simulated` rows | Generated by this repo; no real people |

Design and decisions: `docs/DECISIONS.md` (2026-10-25 entries). Generator code: `backend/src/veritrust/synth/`, `backend/src/veritrust/anchor/`, `backend/src/veritrust/combine.py`.

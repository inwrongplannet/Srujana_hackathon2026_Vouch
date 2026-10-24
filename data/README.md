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
| `external/` | `python -m veritrust.anchor.download` | Raw public sources: Home Credit mirror (pinned revision) and Berka. Real anonymised rows: never commit, never paste into prompts. |

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
| `vouches` | vouch (simulated world only) | relationship, months known, voucher's own on-time share |
| `outcomes` | applicant | `default_12m` label |
| `features` | applicant | the model row, built only from the tables above |
| `truth` (simulated) / `injections` (anchored) | applicant | the answer key; never a model input |

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

---
name: dual-axis-scoring
description: Exact formulas for mu_composite, sigma2_epistem, and Score_final (LCB) — the dual-axis underwriting output
---
# dual-axis-scoring

**Why this exists:** The dual-axis output is the core differentiator of the system. Collapsing mu and sigma2 into one number, or inventing parameter values, destroys the demo story.
**Used by:** Reehan, Abhijit
**Triggered by:** Any code computing a credit score, uncertainty band, or loan limit; any UI rendering a score

---

## When to use
Any implementation of the underwriting synthesizer, the `/assess` endpoint, the `/simulate` endpoint, or the dual-axis gauge component.

---

## The two axes (never collapse to one number)

| Axis | Symbol | Meaning | Range |
|---|---|---|---|
| Expected repayment capacity | `mu_composite` | Weighted blend of graph trust and cash-flow score | `[0, ∞)` in practice `[0, ~100]` |
| Epistemic uncertainty | `sigma2_epistem` | Confidence in the assessment; high = thin data | `[0.0, 1.0]` |

**UI rule:** Both axes must be visible separately in the judge demo. Do not hide sigma2 behind mu.

---

## Formulas (copy exactly; log parameter changes in DECISIONS.md)

### Step 1 — Cash-flow score
```
S_cashflow = f(income_stability, DSCR, tx_volatility, completeness)

Where:
  income_stability  = stddev(monthly_income) / mean(monthly_income)   (lower = more stable)
  DSCR              = net_operating_income / debt_service              (>= 1.25 is healthy)
  tx_volatility     = stddev(monthly_net_cashflow) / mean(abs(monthly_net_cashflow))
  completeness      = fraction of expected fields that are non-null    (0.0 to 1.0)

S_cashflow = (w1 * DSCR_norm + w2 * (1 - income_instability_norm) + w3 * (1 - volatility_norm)) * completeness
```
Use `w1=0.5, w2=0.3, w3=0.2` as defaults. All normalisation maps the metric to `[0, 1]` using the seed data's min/max range. Log in DECISIONS.md if weights change.

### Step 2 — Graph score
```
R_graph(T) = output of the graph-trust-engine skill
           = sum of Trust(P) over all simple paths P from anchors to T
```

### Step 3 — mu_composite
```
mu_composite = (alpha * R_graph + (1 - alpha) * S_cashflow)
             * exp(beta * (N_settled + |In(T)|))

Parameters (defaults):
  alpha   = 0.6    (weight of graph trust vs cash-flow)
  beta    = 0.1    (reputation multiplier for settled loans + incoming vouches)
  N_settled = number of loan contracts borrower T has successfully settled
  |In(T)| = number of incoming active vouches to T
```

### Step 4 — Epistemic uncertainty
```
sigma2_epistem = 1 / (1 + N_data_points * completeness)

Where:
  N_data_points = number of verified data sources (bank statements, AA records, settled loans)
  completeness  = fraction of expected fields that are non-null in cash-flow data

Cold-start (no data): sigma2 = 1.0   (maximum uncertainty)
Fully verified:       sigma2 -> 0    (minimum uncertainty)
sigma2 is NEVER negative.
Missing a field INCREASES sigma2 — do not impute missing fields; flag them.
```

### Step 5 — Score_final (Lower Confidence Bound)
```
kappa = 1.0   (uncertainty penalty; higher = more conservative)

Score_final = mu_composite - kappa * sqrt(sigma2_epistem)
```
`Score_final` is the number used to determine the loan limit. A thin-file borrower (high sigma2) gets a lower Score_final even if mu is moderate — this is intentional and must be visible in the UI as a shaded band.

---

## Loan limit derivation
```
Max_loan = Score_final * base_unit_INR
```
Where `base_unit_INR` is a configurable parameter (e.g. 10,000 INR per score point). Log its value in DECISIONS.md. All monetary output is `Decimal` with currency code `INR`.

---

## Edge cases (test all of these)

| Scenario | Expected output |
|---|---|
| Cold-start (R_graph=0, no cash-flow data) | mu_composite=0, sigma2=1.0, Score_final=-1.0 (below zero → loan limit = 0) |
| Thin-file with one incoming vouch, no history | mu_composite small but positive, sigma2 ~0.9, Score_final low but non-negative with a micro-limit |
| Rich-file: settled 3 loans, full cash-flow | mu_composite high, sigma2 <0.2, Score_final high, wide loan limit |
| DEFAULTED borrower (R_graph very negative after slash) | mu_composite negative or near zero, Score_final strongly negative, loan limit = 0 |
| DEMO_MODE what-if: increase income by 20% | S_cashflow increases, sigma2 unchanged (same data count), Score_final increases proportionally |

---

## Required unit tests

Every implementation must have at minimum:

1. **Thin-file test**: construct a node with R_graph=2, S_cashflow=0.3, N_settled=0, |In|=1, N_data=0, completeness=0. Assert `sigma2 = 1.0`, `mu_composite` matches formula, `Score_final = mu - 1.0`.
2. **Rich-file test**: R_graph=40, S_cashflow=0.8, N_settled=3, |In|=4, N_data=5, completeness=0.9. Assert sigma2, mu, Score_final all match the formula.
3. **Parameter sensitivity**: change alpha from 0.6 to 0.4. Assert mu_composite changes in the expected direction.

---

## What the UI must show

- **Primary number:** `Score_final` (the LCB)
- **Band:** `mu_composite ± kappa * sqrt(sigma2)` as a shaded range — wide band = low confidence
- **Labels:** "Expected capacity: X", "Uncertainty: Y%", "Assessment confidence: Z"
- **Illustrative notice:** "Illustrative data — not financial advice" on every screen
- **Do not:** show a single "credit score" number without the band. Judges specifically look for the uncertainty axis.

---
name: finance-domain
description: Finance formulas, glossary and regulatory vocabulary so logic isn't invented
---
# finance-domain

**Why this exists:** LLMs get finance maths subtly wrong (XIRR, amortization, risk metrics), so one verified reference keeps features consistent
**Used by:** Everyone
**Triggered by:** Any finance calculation

## When to use
Any code, copy or data involving money, rates, returns, risk or regulation. Use these definitions instead of improvising; if something is missing, add a `/decide` entry for the chosen definition before coding it.

## Money handling (non-negotiable)
- Never float. Python `decimal.Decimal` (create from strings, not floats); JS/TS use integer minor units or a decimal library. Set the Decimal context precision explicitly (28+ digits).
- Every amount carries an ISO 4217 currency code. Never add or compare amounts of different currencies without an explicit FX rate and its date.
- Round only at the final presentation step. Default rounding: ROUND_HALF_EVEN (banker's) for ledgers; ROUND_HALF_UP where a product convention requires it. State the choice. Display 2 dp (0 dp for JPY-style currencies) but keep full precision internally.
- Rates: store as decimal fractions (0.05 = 5%); convert to percent only for display. Always state the compounding and day-count convention.
- Dates: use calendar dates (not datetimes) for cash flows; be explicit about timezone for timestamps; never use "now" inside a calculation that must be reproducible.

## Core formulas
- **Simple interest**: I = P·r·t. **Compound**: FV = PV·(1 + r/m)^(m·t); effective annual rate EAR = (1 + r/m)^m - 1.
- **Present / future value**: PV = FV / (1+r)^n. **NPV** = Σ CFₜ / (1+r)^t, with CF₀ at t=0.
- **Loan payment (EMI)** for principal P, periodic rate i, n periods: EMI = P·i·(1+i)^n / ((1+i)^n - 1); if i = 0, EMI = P/n. Each period: interest = balance·i; principal = EMI - interest; balance -= principal. Final payment absorbs rounding residue.
- **IRR**: rate where NPV = 0 for evenly spaced flows. **XIRR**: rate where Σ CFᵢ / (1+r)^((dᵢ - d₀)/365) = 0 for dated flows (Actual/365). Solve with a bracketed method (Brent/bisection), not blind Newton; require at least one negative and one positive flow; report "no solution" instead of a garbage number.
- **Return**: simple R = (V_end - V_start + income) / V_start. **CAGR** = (V_end/V_start)^(1/years) - 1. Time-weighted return chains sub-period returns Π(1+Rₖ) - 1 (removes the effect of flows); money-weighted return is the IRR.
- **Log vs simple returns**: log r = ln(Pₜ/Pₜ₋₁); do not average simple returns to annualize, compound them.
- **Volatility**: sample standard deviation of periodic returns; annualize by √252 (daily), √52 (weekly), √12 (monthly).
- **Sharpe** = (Rₚ - R_f) / σₚ (annualized, both in the same units). **Sortino** replaces σ with downside deviation.
- **Max drawdown** = min over t of (Vₜ / max_{s≤t} V_s - 1).
- **Beta** = Cov(Rₐ, R_m) / Var(R_m). **Alpha** = Rₐ - [R_f + β(R_m - R_f)].
- **VaR (historical, 95%)**: the 5th percentile of the return (or P&L) distribution over the horizon, reported as a positive loss; state horizon and window. **Expected shortfall**: mean loss beyond VaR.
- **Credit / lending**: LTV = loan / collateral value; DTI = monthly debt payments / gross monthly income; DSCR = net operating income / debt service (≥1 means it covers); utilization = balance / limit.
- **Accounting ratios**: current ratio = current assets / current liabilities; quick ratio excludes inventory; gross margin = (revenue - COGS)/revenue; EBITDA margin = EBITDA/revenue; ROE = net income / equity; interest coverage = EBIT / interest expense.
- **Day counts**: Actual/365, Actual/360, 30/360 differ; pick per instrument and state it. Rule of 72 is a mental estimate only, never for output.

## Glossary
Principal, coupon, yield, YTM, duration, basis point (1bp = 0.01% = 0.0001), notional, AUM, NAV, spread, liquidity, collateral, hedge, leverage, amortization, accrual, settlement (T+1/T+2), mark-to-market, P&L (realized vs unrealized), drawdown, benchmark, SIP/DCA, KYC, AML, PEP, sanctions screening.

## Regulatory vocabulary (use terms accurately; do not claim compliance)
KYC/AML (customer identification, suspicious activity), GDPR / data-protection (consent, minimization, right to erasure), PSD2 / open banking (account access via consented APIs), Basel III (capital and liquidity ratios), MiFID II (suitability, best execution, disclosures), SOX/audit trail, PCI DSS (card data), SEC/FCA-style fair-presentation of performance. Jurisdiction (e.g. India: RBI/SEBI, US: SEC/FINRA, EU/UK) is set in `docs/PROBLEM.md`; do not mix them.

## Required disclaimers and checks
- Demo outputs are illustrative on synthetic data and are not financial advice; say so in the UI.
- Every calculation needs at least one unit test with a known answer (e.g. a standard amortization table, a textbook XIRR example) before it is shown in the demo.

## Project-specific formulas (use these exactly; do not improvise)

These formulas are canonical for this project. For full derivation and invariants see the dedicated skills: `graph-trust-engine`, `dual-axis-scoring`, `slashing-cascade`.

### Trust path score
```
X = 0.5   (hop decay factor)
C_u = max(0, R_u)
W_uv = C_u / |Out(u)|   for each v in Out(u)

For path P = (v0, v1, ..., vk), v0 in InstitutionalAnchors, vk = T:
  Trust(P) = W_{v0,v1} * prod_{i=1}^{k-1} (W_{vi,vi+1} * X)

If any node in P is already in the visited-set VP: Trust(P) = 0 (cycle absorption).
R_graph(T) = sum of Trust(P) over all simple paths from anchors to T.
All arithmetic: Decimal. Never float.
```

### Dual-axis composite score
```
mu_composite = (alpha * R_graph + (1 - alpha) * S_cashflow)
             * exp(beta * (N_settled + |In(T)|))
sigma2_epistem = 1 / (1 + N_data_points * completeness)   range [0.0, 1.0], never negative
Score_final    = mu_composite - kappa * sqrt(sigma2_epistem)   (Lower Confidence Bound)

Defaults: alpha=0.6, beta=0.1, kappa=1.0. Log in DECISIONS.md if changed.
```

### Slashing cascade
```
k=0 (defaulter):  R_B <- R_B - delta0; state -> DEFAULTED; C_B = 0
k=1 (sponsor):    delta = 0.5 * W_AB * delta0
k=2 (ancestor):   delta = 0.25 * delta0
k>=3:             delta = 0   (hard cutoff)
Apply atomically. Never sequentially.
```

### DSCR (project standard)
```
DSCR = Net Operating Income / Total Debt Service
DSCR >= 1.25 considered adequate for micro-lending in seed data and demo narrative.
```

### Epistemic uncertainty (information gap)
```
Missing field in cash-flow: do NOT impute. Increase sigma2 by the field's weight.
sigma2 = 1.0 for a cold-start node (no data). Decreases only as verified data arrives.
```

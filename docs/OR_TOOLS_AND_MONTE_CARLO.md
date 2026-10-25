# Google OR-Tools and Monte Carlo stress testing in VeriTrust

**Why this file exists:** explains the technical rationale, architectural necessity, and practical value of combining Google OR-Tools CP-SAT optimization with Monte Carlo stochastic simulation in VeriTrust credit underwriting.

## At a glance

| Engine | What it does | Why it is needed | Why not alternative approaches? |
|---|---|---|---|
| **Google OR-Tools** (CP-SAT) | Discrete constrained optimization over loan principal, tenure, and repayment instalments | Finds the mathematically optimal feasible loan or restructuring plan when a requested loan violates policy constraints | Replaces flat loan rejections and manual trial-and-error with provably optimal, constraint-aware restructuring options; avoids black-box ML hallucination |
| **Monte Carlo simulation** | Forward-looking stochastic cash-flow stress testing across 5,000 seeded economic scenarios | Measures default probability under income volatility, payment receipt delays, and emergency cash shocks | Static monthly debt-to-income checks fail during real-world income volatility; stochastic simulation tests cash survival without requiring historical default training data |

---

## 1. Google OR-Tools: constrained loan optimization

### What it is
Google OR-Tools is an open-source software suite for combinatorial optimization. VeriTrust utilizes its **CP-SAT (Constraint Programming - Satisfiability)** solver to search the discrete space of loan amounts ($P$) and tenures ($T$) subject to non-linear affordability and policy rules.

### The problem it solves
In conventional credit scoring, if an applicant's requested loan violates any policy rule (e.g., requested EMI exceeds disposable income, or principal exceeds maximum credit limit), the borrower is simply rejected with a flat "NO".

However, credit applicants frequently ask for sub-optimal loan structures—such as requesting ₹5,00,000 over 67 months when their verified income can only safely support ₹3,29,000 over 36 months. 

Without an optimizer, a loan officer or platform has only two bad choices:
1. Flat rejection, losing the creditworthy borrower.
2. Heuristic manual guessing of alternative terms, which is slow, inconsistent, and prone to policy violations.

### How VeriTrust uses CP-SAT
VeriTrust models loan structuring as an integer constraint satisfaction problem:
- **Decision variables:**
  - Principal: $P \in [P_{\min}, P_{\max}]$ in discrete steps of ₹1,000.
  - Tenure: $T \in [T_{\min}, T_{\max}]$ in monthly increments.
- **Constraints enforced simultaneously:**
  - $P \le \text{Credit Limit}$ (derived from dual-axis Lower Confidence Bound LCB and Web-of-Trust $R_{\text{graph}}$).
  - $\text{EMI}(P, T, r) \le D$ (where $D = I - E - B_{\text{floor}}$ is verified disposable income).
  - $\text{EMI}(P, T, r) / I \le 0.40$ (FOIR/ITI policy cap).
  - $(\text{Debt} + \text{EMI}(P, T, r)) / I \le 0.50$ (DTI policy cap).
- **Dual optimization objectives:**
  - `MAX_PRINCIPAL`: Maximizes funded capital $P$ subject to all safety constraints (liquidity-focused).
  - `MIN_COST`: Minimizes total interest paid over the life of the loan (cost-focused).

### Why not simple mathematical formulas?
A single closed-form formula cannot simultaneously satisfy:
- Discrete step increments for principal and tenure.
- Non-linear monthly EMI compounding:
  $$\text{EMI} = P \times \frac{r(1+r)^T}{(1+r)^T - 1}$$
- Multiple piecewise constraints (disposable income floor, ITI cap, DTI cap, and trust-graph credit ceiling).
- Trade-offs between competing objectives (e.g. extending tenure lowers monthly instalment to meet DTI, but increases total interest).

OR-Tools solves this non-linear discrete space in under 5 milliseconds.

### Why not machine learning (ML)?
1. **Explainability & compliance:** Under credit regulations (e.g., Fair Credit Reporting, RBI credit guidelines), lenders must disclose the exact reasons for loan adverse action. OR-Tools explicitly identifies which binding constraint disqualified the plan (e.g., `DISPOSABLE_INCOME` or `CREDIT_CEILING`). ML models provide opaque probabilistic weights.
2. **Boundary safety:** Neural networks and regression models can extrapolate outside training data, approving dangerous loan terms. CP-SAT enforces mathematical hard bounds that can never be violated.
3. **Zero training data requirement:** Optimization operates strictly on the borrower's verified balance sheet and configured policy rules; no historical default dataset is required.

---

## 2. Monte Carlo simulation: forward-looking stress testing

### What it is
Monte Carlo simulation is a computational algorithm that models probability distributions of uncertain outcomes through repeated random sampling. In VeriTrust, `MonteCarloStressTester` simulates 5,000 distinct financial lifetimes for a borrower over the proposed loan tenure.

### The problem it solves: the flaw of static affordability
Static affordability formulas assume that every month looks like the borrower's average month:
$$D = I - E - B$$

In the real economy—especially for informal workers, freelancers, micro-entrepreneurs, and agricultural producers—income and expenses are never static:
- **Income volatility:** Monthly revenue fluctuates by $\pm 15\text{--}30\%$.
- **Payment delays:** Clients or buyers delay payments by 15 to 45 days.
- **Emergency expenses:** Equipment repairs, medical bills, or family emergencies create sudden cash outflows.

A loan plan that appears 100% affordable under static calculations can have an 80% probability of default during a 3-month seasonal downturn.

### How VeriTrust uses Monte Carlo
For each of the 5,000 simulated paths, the simulator steps through month $t = 1 \dots T$:
1. **Stochastic income drift:** Samples monthly income from a Gaussian distribution:
   $$I_t \sim \mathcal{N}(\mu_I, \sigma_I^2)$$
2. **Stochastic payment delay:** Evaluates whether an invoice or receivable is delayed:
   $$\text{Delay} \sim \text{Bernoulli}(p_{\text{delay}})$$
   If delayed, cash is deferred to month $t+1$.
3. **Stochastic emergency expense:** Evaluates sudden unplanned outflows:
   $$\text{Shock} \sim \text{Poisson}(\lambda_{\text{shock}})$$
4. **Cash flow accounting:**
   $$\text{Net Cash}_t = I_t - E - \text{Debt} - \text{EMI} - \text{Shock}_t$$
   $$\text{Liquid Reserve}_t = \text{Liquid Reserve}_{t-1} + \text{Net Cash}_t$$

### Key metrics produced
1. **Shortfall / Default risk (%):** Percentage of the 5,000 simulated futures where liquid cash drops below zero before loan maturity.
2. **Adverse 5th-percentile cash cushion:** The net cash remaining in the 5% worst economic scenarios. A positive 5th-percentile cushion proves the borrower survives extreme economic downturns without defaulting.
3. **Income shock tolerance (%):** The maximum percentage drop in monthly income the borrower can absorb before entering cash deficit.
4. **Affordability break-even income:** The exact gross income threshold below which monthly instalments become unsustainable.

### Why deterministic reproducibility matters
The simulation uses fixed pseudo-random seeds. Running the simulation on Plan A and Plan B uses the **exact same simulated futures**. This enables head-to-head comparison:
> "Under the exact same 5,000 economic shocks, extending tenure from 12 to 24 months cuts default probability from 2.56% to 1.16% and preserves ₹2,064.81 more adverse cash buffer."

### Why not machine learning (ML)?
1. **The cold-start problem:** Thin-file and unbanked borrowers have no credit bureau history. An ML model trained on past defaults cannot score them fairly.
2. **Structural cash-flow testing:** Monte Carlo evaluates whether the borrower's actual cash inflows can physically service the debt under stochastic shocks. It is based on accounting mechanics, not demographic correlation.
3. **No black-box hallucination:** All simulation parameters (volatility %, delay probability, shock severity) are explicit, transparent, and configurable by risk officers.

---

## 3. The four-layer underwriting pipeline

Google OR-Tools and Monte Carlo stress testing do not operate in isolation. They form a four-layer verification pipeline:

```text
+-------------------------------------------------------------+
| LAYER 1: Rule-Based Affordability Engine                     |
| Computes: D = I - E - B                                     |
| Enforces: Disposable floor, ITI <= 40%, DTI <= 50%          |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| LAYER 2: Google OR-Tools CP-SAT Optimizer                   |
| Explores: Discrete (Principal, Tenure) search space         |
| Solves: MAX_PRINCIPAL or MIN_COST under Layer 1 bounds      |
| Generates: Feasible restructured alternatives               |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| LAYER 3: Monte Carlo Stochastic Stress Tester               |
| Simulates: 5,000 stochastic economic lifetimes              |
| Evaluates: Income volatility, payment delays, shocks        |
| Outputs: Shortfall risk %, 5th-percentile cushion, break Pt |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| LAYER 4: Multi-Dimensional Explanation Engine               |
| Synthesizes: Financial Capacity, Evidence Quality,          |
|              Web-of-Trust Reputation, Stress Resilience     |
| Generates: Traceable, auditable, fair restructuring report  |
+-------------------------------------------------------------+
```

---

## 4. Practical summary: why this matters for the product

1. **For the borrower:**
   - Avoids automated "black-box" rejections.
   - Provides concrete, mathematically feasible restructuring alternatives with transparent trade-offs (e.g. lower monthly payment vs. lower total interest).
   - Gives borrowers confidence that their loan is resilient against real-world emergencies.

2. **For the lender:**
   - Eliminates blind lending by verifying cash-flow survival under thousands of adverse scenarios.
   - Prevents over-indebtedness through hard mathematical constraint enforcement.
   - Allows fine-grained risk tuning (e.g., rejecting plans with >10% simulated shortfall risk).

3. **For regulators and governance:**
   - Zero black-box bias or demographic discrimination.
   - Complete auditability: every decision traces directly to explicit formulas, solver constraints, and seeded simulation distributions.
   - Compliant with fair lending standards and borrower recourse rights.

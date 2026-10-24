# Problem Statement

**Track:** F-04 · Fair and Explainable Creditworthiness Assessment  
**Domain:** Lending · Financial Inclusion

---

## Why this file exists

One agreed source of truth for what we are solving and how we are judged, so all three of us (and every agent) aim at the same target.

---

## The Problem (verbatim)

> Access to credit is important for individuals and small businesses, but assessing the ability to repay a loan can be difficult when financial records are limited, inconsistent, or incomplete. Conventional assessment approaches may not adequately capture a borrower's actual repayment capacity, while inaccurate assessments can expose lenders and borrowers to financial risk.

---

## What We Are Building

A solution that helps evaluate the creditworthiness of individuals or small businesses using relevant financial information and **clearly communicates the factors influencing the assessment**.

---

## Factors to Consider

| Factor | Notes |
|---|---|
| Income stability | Regular vs irregular income sources |
| Existing obligations | Current loans, EMIs, recurring liabilities |
| Repayment history | Past behaviour as signal of future behaviour |
| Cash-flow patterns | Inflows/outflows over time, seasonality |
| Debt burden | Debt-to-income ratio and similar measures |
| Data reliability / completeness | Flag when records are thin, inconsistent, or missing |

**Key distinction the solution must make:** absence of financial history ≠ evidence of inability to repay.

---

## Expected Outcome

A **working credit-assessment prototype** that:

1. Produces an **interpretable evaluation** of repayment capacity.
2. Identifies relevant **risk factors** and **information gaps**.
3. Demonstrates how **different financial circumstances or loan conditions** affect the assessment (sensitivity / what-if).
4. Helps users understand the **strengths, limitations, and uncertainties** of an assessment.
5. Is **consistent and fair**, and explicitly guards against drawing conclusions from incomplete or misleading data.

---

## Judging Criteria (inferred from PS)

- Interpretability — can a non-expert understand why a score/band was given?
- Completeness handling — graceful degradation when data is missing.
- Fairness — no proxy discrimination; thin-file borrowers treated equitably.
- Scenario/sensitivity analysis — what-if on loan terms, repayment schedules, changing circumstances.
- Working demo — judges will click through it.

---

## Core User

**Primary:** Loan officer or credit analyst at an MSME/microfinance lender evaluating a thin-file applicant.  
**Secondary:** The borrower themselves, wanting to understand their profile.

---

## Core Flow

1. Intake — enter or upload borrower financial data (income, obligations, history, cash-flow).
2. Assessment — system scores repayment capacity, flags data gaps.
3. Explanation — human-readable breakdown of drivers (positive and negative).
4. Sensitivity — adjust loan amount / tenure / income and see updated assessment.
5. Output — summary report the officer can share with the applicant.

---

## Sponsor Tech / Bonus APIs

- TODO(kickoff): confirm with Abhishek after sponsor briefing.

---

## Out of Scope

- Live credit bureau API integration (use simulated / seed data for demo).
- Regulatory approval or production deployment.
- Collecting or storing real personal financial data.

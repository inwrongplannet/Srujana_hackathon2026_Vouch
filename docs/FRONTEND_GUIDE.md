# Frontend guide

**Why this file exists:** This document is the integration guide for the frontend team. It explains the backend capabilities, the exact data required for each calculation, what screens can do right now, and how the frontend can request backend changes and evaluate whether they are feasible.

---

## 1. Overview and architecture

The VeriTrust platform combines Web-of-Trust graph propagation, rule-based cash-flow affordability, Google OR-Tools constraint optimization, Monte Carlo stress testing, and explainable predictive risk models.

The frontend connects to the backend through typed REST interfaces (`frontend/src/api/backend.ts`). Every TypeScript type in `frontend/src/types/api.d.ts` is automatically generated from the backend OpenAPI specification via `make types`, guaranteeing that frontend and backend models never drift.

```text
+-----------------------------------------------------------------------------------+
|                                  Frontend UI                                      |
|   Landing  |  Onboarding  |  Borrower  |  Community  |  Assess Desk  |  Lender    |
+-----------------------------------------------------------------------------------+
                                       |
                   Typed API Client (src/api/backend.ts)
                                       |
+-----------------------------------------------------------------------------------+
|                              FastAPI REST Backend                                 |
|                                                                                   |
|  1. Web-of-Trust Engine    : Graph traversal, capacity conservation, hop decay   |
|  2. Dual-Axis Underwriter  : Trust score R, capacity S_D, epistemic uncertainty   |
|  3. Affordability Engine   : Disposable income D = I - E - B, FOIR/DTI caps       |
|  4. OR-Tools Optimizer     : CP-SAT loan restructuring (MIN_COST / MAX_PRINCIPAL) |
|  5. Monte Carlo Simulator  : 5,000 seeded paths, shortfall risk, adverse cash     |
|  6. Predictive ML & Explain: Calibrated default probability, conformal sets       |
|  7. Temporal Freshness     : Half-life decay C(t) = 2^(-dt/H), staleness alerts   |
|  8. Slashing & Treasury    : 4-level damped default cascade, 1% platform fee cut  |
|  9. Append-Only Ledger     : SHA-256 tamper-evident cryptographic event chain     |
+-----------------------------------------------------------------------------------+
```

---

## 2. What backend provides

The backend offers nine core analytical engines exposed through clear REST endpoints:

### Web-of-Trust trust graph
- **What it does:** Calculates transitive trust propagation across the endorsement network.
- **Key mechanics:** Geometric hop decay ($\lambda = 0.5$ per hop), cycle absorption (zeroing cyclical feedback), and capacity conservation across siblings.
- **Output:** Individual reputation score $R \in [0, 100]$, borrowing capacity $C$, and incoming active trust paths.
- **Endpoint:** `GET /api/v1/users/{id}/vouch-summary`, `GET /api/v1/graph`.

### Dual-axis credit scoring
- **What it does:** Underwrites thin-file borrowers by combining social collateral ($R_{\text{graph}}$) and cash-flow capacity ($S_D$) into composite capacity $\mu$.
- **Key mechanics:** Epistemic uncertainty $\sigma^2 \in [0, 1]$ measures evidence sparsity. Approved credit limit is derived from the Lower Confidence Bound (LCB):
  $$L = \max\left(0, \lfloor (\mu - k \sigma) \times U \rfloor\right)$$
  where $k = 1.0$ and base scale unit $U = 10,000 \text{ INR}$.
- **Endpoint:** `POST /api/v1/applications/{id}/assessments`, `GET /api/v1/assessments/{id}`.

### Rule-based affordability engine
- **What it does:** Ensures borrowers never receive loans they cannot service.
- **Key mechanics:** Evaluates monthly income $I$, non-discretionary obligations $E$, existing debt, and protected emergency cash buffer $B = \max(3,000 \text{ INR}, 15\% \times I)$.
  - Disposable income: $D = I - E - B$.
  - Maximum affordable EMI is bounded by: $\min(D, 0.40 \times I - \text{Debt}, 0.50 \times I - \text{Debt})$.
- **Status:** Returns `SUFFICIENT`, `BORDERLINE`, or `INSUFFICIENT` with the exact binding constraint.

### Google OR-Tools CP-SAT restructuring optimizer
- **What it does:** If an applicant's requested loan is unaffordable, the solver finds the optimal feasible alternative rather than rejecting them.
- **Objectives:**
  - `MIN_COST`: Minimizes total interest paid while fitting monthly instalment within disposable cash flow.
  - `MAX_PRINCIPAL`: Maximizes disbursed principal within the borrower's LCB credit limit and disposable income.
- **Restructuring levers:** Tenure extension (12 to 36 months), principal right-sizing, and interest rate adjustment.

### Monte Carlo stress testing
- **What it does:** Simulates 5,000 macroeconomic and idiosyncratic shock paths over the loan lifetime.
- **Outputs:**
  - Shortfall probability (fraction of simulated paths experiencing negative cash flow).
  - Adverse 5th-percentile cash buffer (worst-case liquidity buffer).
  - Income shock tolerance percentage (maximum income reduction tolerated before default).
  - Resilience rating: `HIGH`, `MODERATE`, `VULNERABLE`, or `CRITICAL`.

### Predictive risk and model explainability
- **What it does:** Provides instant credit risk evaluation with statistical guarantees and transparent reasons.
- **Outputs:**
  - Calibrated default probability $P(\text{Default})$ and Basel scorecard credit rating ($300\text{--}900$).
  - Split-conformal prediction sets with 90% finite-sample coverage (`ELIGIBLE`, `REVIEW`, or `DECLINE_CANDIDATE`).
  - Additive local reason codes (positive and risk factors with log-odds and observed values).
  - Missing evidence disclosures (`MISSING_BANK_STATEMENT`, `MISSING_BUREAU_FILE`, `MISSING_GST`, `MISSING_DECLARED_INCOME`).
  - 4-Dimensional underwriting scores (Financial Capacity, Evidence Reliability, Graph Reputation, Stress Resilience).
  - Actionable counterfactual remedies (sustainable principal, recommended tenure, required income delta).
- **Endpoint:** `POST /api/v1/predict`, `GET /api/v1/predict/sample`.

### Temporal uncertainty and evidence freshness
- **What it does:** Decays confidence in stale historical data without erasing historical credibility.
- **Key mechanics:** Asymmetric half-life decay $C_k(t) = 2^{-\Delta t / H_k}$ across distinct horizons:
  - Cash flows: $H_{CF} = 6 \text{ months}$ (fast decay; cash flows fluctuate quickly).
  - Peer vouches: $H_V = 24 \text{ months}$ (medium decay; relationships change gradually).
  - Repayment track record: $H_R = 36 \text{ months}$ (slow decay; integrity is durable).
- **Uncertainty inflation:** When evidence is older than 12 months, epistemic uncertainty $\sigma^2(t)$ inflates toward 1.0, triggering staleness warnings and lowering LCB limits until refreshed.

### Damped default cascade and platform treasury
- **What it does:** Penalizes defaults through a damped multi-hop cascade while accumulating platform transaction fees.
- **Cascade mechanics:**
  - Level 0 (defaulter): Reputation slashed by $-\delta_0$ (default $-10.0$), status set to `DEFAULTED`.
  - Level 1 (direct sponsors): Slashed by $0.5 \times W \times \delta_0$.
  - Level 2 (grand-sponsors): Slashed by $0.25 \times \delta_0$.
  - Circuit breaker: Halts cascade if any node drops below $-50.0$.
- **Platform treasury:** A 1% platform transaction fee cut is recorded on loan disbursements and repayments, tracked in `PlatformTreasury`.
- **Endpoint:** `POST /api/v1/loans/repay`, `POST /api/v1/loans/{id}/default`, `GET /api/v1/platform/treasury`.

### Tamper-evident ledger
- **What it does:** Records every reputation mutation, endorsement, loan creation, repayment, fee cut, and penalty in an append-only hash chain.
- **Audit:** Any client can audit the SHA-256 chain from genesis to head or deterministically reconstruct state from raw events.
- **Endpoint:** `GET /api/v1/transactions` (money movements with fees). The hash-chain audit and replay have no endpoint yet; run them with `python main.py audit` and `python main.py replay` in `backend/`.

---

## 3. Data backend expects from frontend

All monetary values are transmitted as decimal strings with two decimal places (e.g. `"150000.00"`). Currency is ISO 4217 code `INR`. Floating-point numbers are strictly forbidden for currency amounts to eliminate rounding drift.

### Core input requirements by endpoint

| Endpoint | Purpose | Required fields | Optional fields |
|---|---|---|---|
| `POST /api/v1/applications` | Create loan application | `borrower_id`, `principal` | `annual_rate` (default 0.12), `term_months` (default 12), `purpose_category` |
| `POST /api/v1/applications/{id}/evidence` | Register consented document | `description` | `evidence_type` (default `BANK_STATEMENT`), `source`, `uri_or_hash`, `confidence` |
| `POST /api/v1/applications/{id}/assessments` | Run assessment and OR-Tools optimization | None | `objective` (`MIN_COST` or `MAX_PRINCIPAL`), `enable_stress_test` (bool), `simulation_scenarios` (int), `bureau_status`, `bureau_score` |
| `POST /api/v1/assessments/{id}/scenarios` | Run counterfactual simulation | None (empty object `{}` re-runs base assessment) | `simulated_income`, `simulated_expenses`, `simulated_principal`, `simulated_tenure` |
| `POST /api/v1/predict` | Fast prediction and full explanation | None (all fields have safe defaults or borrower lookup) | `borrower_id`, `monthly_income`, `monthly_debt`, `requested_amount`, `requested_tenure_months`, `annual_interest_rate`, `bureau_score`, `bureau_status`, `vouch_count`, `vouch_score`, `bank_bounces_3m`, `bank_income_cv`, `bank_statement_status`, `evidence_age_months` |
| `POST /api/v1/endorsements` | Issue peer endorsement | `endorser_id`, `recipient_id` | `statement`, `verification_quality`, `relevance` |
| `POST /api/v1/vouch-requests` | Ask a peer for an endorsement | `requester_id`, `voucher_id` | `note` |
| `POST /api/v1/vouch-requests/{id}/respond` | Accept or decline vouch request | `accept` (bool) | None |
| `POST /api/v1/loans/repay` | Repay loan instalment | `loan_id`, `amount` | None |
| `POST /api/v1/loans/{id}/default` | Trigger default and slashing | None | `delta0` (slash severity, default `10.0`) |
| `POST /api/v1/community/asks/{id}/vouches` | Stake community vouch | `voucher_id`, `kind` (`KNOWN` or `EVIDENCE`), `stake` | `relationship`, `years_known`, `read_verified` |
| `POST /api/v1/community/asks/{id}/setback` | Broadcast borrower setback | `text` | None |
| `POST /api/v1/community/asks/{id}/setback/respond` | Voucher response to setback | `voucher_id`, `choice` (`STAND_BY` or `STEP_BACK`) | None |

### Value formats and formatting rules

- **Money amounts:** Decimal string, e.g. `"38000.00"`. Do not pass `38000` or `38000.0` as a JSON number.
- **Interest rates:** Decimal ratio as JSON number, e.g. `0.18` represents 18% annual percentage rate.
- **Tenure:** Integer months, e.g. `12`, `24`, `36`.
- **Status strings:** Upper snake-case literals, e.g. `NO_FILE`, `VERIFIED`, `PARTIAL`, `NOT_PROVIDED`, `WITHHELD`.
- **Evidence age:** Float months, e.g. `0.0` (fresh), `6.0` (six months old), `24.0` (two years stale).

---

## 4. What frontend can build and display

The existing frontend pages and proposed UI panels map directly to backend capabilities:

### Assessment desk (`/app/assess`)
- **What it does:** Primary underwriter dashboard for loan officer evaluation.
- **Backend calls:**
  - `POST /api/v1/applications/{id}/assessments`: Runs the dual-axis score, affordability check, OR-Tools optimizer, and Monte Carlo stress test in a single pass.
  - `POST /api/v1/assessments/{id}/scenarios`: Interactive sliders for income, expenses, and principal; recalculates feasibility instantly.
- **UI components:**
  - Side-by-side Dual-Axis Score Card: Displays Credit Bureau status/score beside Web-of-Trust vouch score.
  - Restructuring Comparison Card: Original requested terms vs Google OR-Tools optimal feasible plan (tenure, EMI, savings).
  - Stress Resilience Gauge: 5,000 Monte Carlo simulations showing shortfall probability and adverse cash buffer.
  - Interactive What-If Scenario Sandbox: Real-time sliders recalculating residual cash flow and binding constraints.

### Predictive risk and explanation inspector
- **What it does:** Consumer-facing and underwriter-facing explanation view answering *why* a decision was made and *how* to qualify.
- **Backend call:** `POST /api/v1/predict` (or `GET /api/v1/predict/sample` for sandbox initialization).
- **UI components:**
  - Decision Banner: Conformal set guarantee badge (`ELIGIBLE` in green, `REVIEW` in amber, `DECLINE_CANDIDATE` in red) with statistical confidence guarantee (90%).
  - Calibrated Credit Rating Gauge: Basel scorecard rating ($300\text{--}900$) and default probability.
  - Reason Code Cards: Split into Positive Factors (lowering risk) and Risk Factors (raising risk) with exact observed values and log-odds impact.
  - Missing Evidence Disclosures: Alert pills indicating missing bureau history or unverified bank statements, explaining alternative evidence utilized.
  - Temporal Freshness Indicator: Displays age of financial statements and vouches with half-life decay indicators and staleness warnings.
  - Counterfactual Action Guide: Specific steps the applicant can take to qualify (e.g. "Extend tenure to 24 months to lower EMI to 7,930.66 INR" or "Add 2 guild endorsements to lift score above 50").

### Borrower portal (`/app/borrower`)
- **What it does:** Borrower dashboard displaying current standing and active loans.
- **Backend calls today:** none; it runs on the guided-story mock (`frontend/src/mocks/`). A live version would use `GET /api/v1/users/{id}/vouch-summary`, `GET /api/v1/loans`, `POST /api/v1/loans/repay`.
- **UI components:**
  - Approved Credit Limit Card: Displays Lower Confidence Bound ceiling and remaining borrowing capacity.
  - Active Loan Card: Outstanding balance, interest rate, tenure, and next instalment.
  - One-Click Repay Modal: Submits repayment, displays 1% platform fee transparency, and shows instant reputation boost upon settlement.

### Community platform (`/community`, `/community/p/:id`, `/community/me`)
- **What it does:** Social underwriting network where peers vouch for each other with reputation stakes.
- **Backend calls:** `GET /api/v1/community/asks`, `POST /api/v1/community/asks/{id}/vouch-preview`, `POST /api/v1/community/asks/{id}/vouches`, `POST /api/v1/community/asks/{id}/setback`.
- **UI components:**
  - Discover Feed: Filter community borrowing asks by trade, location, and funding progress.
  - Vouch Impact Preview: Interactive slider displaying score gain if loan is repaid versus reputation loss if defaulted.
  - Setback Stand-By Modal: Vouchers review borrower hardship notices and choose whether to stand by them or step back.

### Lender portfolio and treasury view (`/app/lender`)
- **What it does:** Portfolio management dashboard for capital providers. The story file view runs on the mock; the live book calls the backend.
- **Backend calls (live book):** `GET /api/v1/loans`, `GET /api/v1/transactions`, `GET /api/v1/platform/treasury`, `POST /api/v1/loans/{id}/default`.
- **UI components:**
  - Portfolio Yield Dashboard: Total principal disbursed, active interest yield, and recovery rate.
  - Treasury Fee Monitor: Cumulative platform transaction fee cut collected (`PlatformTreasury`).
  - Default Simulation Tool: Simulates default on non-performing loans, demonstrating the 4-level atomic slashing cascade on direct and transitive sponsors.

---

## 5. How frontend can request backend changes

To maintain high development velocity and prevent contract drift, frontend change requests follow this evaluation rubric:

### Fast-track requests (high feasibility, backend eager to build)
- **New query filters or sorting parameters:** E.g. filtering `/api/v1/users` by anchor status, sorting `/api/v1/community/asks` by score or date.
- **Composite summary endpoints:** Grouping related records to eliminate multiple network round-trips on initial screen mount.
- **Additional counterfactual target variables:** E.g. simulating the addition of collateral or co-signers in the what-if engine.
- **Local reason code metadata:** Adding structured category tags, localized human labels, or tooltip descriptions to reason codes.
- **Webhooks or Server-Sent Events (SSE):** Streaming long-running Monte Carlo stress tests or dispatching live updates on vouch events.

### Pushback requests (require architectural review or alternative design)
- **Passing currency as floating-point numbers:** The backend strictly forbids floats for money. All monetary amounts must remain decimal strings.
- **Black-box machine learning outputs:** The backend will not expose predictions without auditable reason codes, conformal set bounds, and traceable feature columns.
- **Mutating state without ledger events:** Every state change must produce a cryptographically verifiable SHA-256 ledger event.
- **Silent fallback to unverified defaults:** When required financial evidence is absent, the backend discloses it honestly rather than fabricating synthetic data.

### The 4-step contract-first protocol

1. **Identify the screen need:** Open a task or brief outlining the user interaction and required fields.
2. **Draft the contract addition:** Add or update the endpoint shape in `docs/API_CONTRACT.md` under the appropriate section.
3. **Backend implementation & verification:** Backend implements the endpoint with comprehensive unit tests and runs `make types`.
4. **Frontend type consumption:** Frontend pulls updated TypeScript definitions directly from `frontend/src/types/api.d.ts` via `make types`, ensuring type-safe client calls without hand-written interfaces.

---

## 6. Error handling and HTTP response codes

The backend returns standardized JSON error responses with a `detail` message:

```json
{
  "detail": "Borrower 'UNKNOWN_USER' does not exist."
}
```

For Pydantic schema validation errors (HTTP 422), `detail` is a list of field error objects.

| HTTP status | Cause | Backend scenario | Recommended frontend handling |
|---|---|---|---|
| `200 OK` | Successful request | Data returned as specified | Render screen or update store |
| `201 Created` | Successful entity creation | Application, evidence, user, or vouch created | Show success notification and navigate |
| `400 Bad Request` | Business invariant violated | Self-vouching attempted, insufficient capacity, loan exceeds ceiling | Display inline field error or alert banner with the returned message |
| `404 Not Found` | Entity does not exist | Unknown `borrower_id`, `application_id`, or `loan_id` | Render empty state or redirect to list page |
| `409 Conflict` | State conflict | Vouch already active, request already pending, application already decided | Disable action button and display current status |
| `422 Unprocessable` | Schema validation error | Missing required field, malformed decimal string, out-of-range number | Highlight invalid form fields |
| `500 Server Error` | Unexpected backend exception | Unhandled server error | Display error boundary with retry button |

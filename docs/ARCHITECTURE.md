# Architecture

**Why this file exists:** a shared picture of how the pieces fit, so parallel work lines up and the pitch has a diagram ready.

## System overview

Vouch (VeriTrust) is a decentralized, explainable credit-underwriting and risk-assessment platform designed to solve the thin-file trap. It combines six orthogonal layers:
1. **Rule-based affordability engine:** Evaluates verified cash inflows, essential expenses, protected buffers, and debt caps ($D = I - E - B$).
2. **Google OR-Tools CP-SAT optimizer:** Restructures infeasible requests into mathematically optimal alternative plans.
3. **Web-of-Trust graph engine:** Transitive trust propagation with out-degree conservation, hop decay, and per-path cycle absorption.
4. **Monte Carlo stochastic stress tester:** Simulates 5,000 forward-looking economic scenarios (income volatility, payment delays, emergency shocks).
5. **Explainability & forensic audit engine:** Traces rule evaluations, evidence links, graph paths, and cryptographic event hashes.
6. **Predictive risk layer:** `POST /api/v1/predict` (`prediction.py`) returns a default probability, a 300-900 scorecard rating, a two-outcome conformal-style set and a tri-state decision (`ELIGIBLE`, `REVIEW`, `DECLINE_CANDIDATE`) from deterministic, inspectable rules, with `rule_fallback.py` behind it. The trained models (EBM, XGBoost, PyTorch, LightGBM, conformal sets) live offline in `backend/ml/` and produce the benchmarks; the API does not load them.

Where each part runs today:
- **Backend** (`backend/`, FastAPI on port 8000): every layer above, served by the endpoints in `docs/API_CONTRACT.md`. State lives in memory and is saved to `backend/data/store.json`; applications and assessments are in-memory only and lost on restart.
- **Frontend** (`frontend/`, Vite on port 5173): the Assessment desk, the community and the lender console's live book call the backend and fall back to recorded or demo data when it is down (`docs/FRONTEND_FALLBACK.md`).
- **Guided story** (landing, onboarding, borrower, voucher, lender views): runs entirely on the frontend engine in `frontend/src/mocks/engine/`, whose formulas differ from the backend's (for example, story edge weight $W = C/|Out|$ summed over all anchor paths). Formula pages say which engine they describe.

```mermaid
flowchart TD
    subgraph INGESTION["Evidence & Identity Ingestion"]
        A["Applicant Profile & Consent"] --> B["Financial Evidence (Bank/DigiLocker)"]
        A --> C["Web-of-Trust Endorsements"]
        A --> D["Bureau Record (Available / No-File)"]
    end

    subgraph ENGINE["Core VeriTrust Underwriting Engine"]
        B --> E["Rule-Based Affordability Engine<br/>(D = I - E - B, FOIR <= 40%, DTI <= 50%)"]
        E --> F["Google OR-Tools Optimizer<br/>(CP-SAT Restructuring)"]
        C --> G["Web-of-Trust Graph Engine<br/>(Transitive Propagation & Cycle Absorption)"]
        F & G --> H["Dual-Axis Scoring & Limit Determination<br/>(LCB Score & Max Credit Ceiling)"]
        H --> I["Monte Carlo Stress Tester<br/>(5,000 Seeded Stochastic Scenarios)"]
        H & I --> P["Explainable ML & Conformal Predictor<br/>(EBM + GPU Meta-Ensemble, Sets >= 90%)"]
    end

    subgraph SETTLEMENT["Audit, Recourse & Settlement"]
        I & P --> J["Multi-Dimensional Explainer<br/>(Capacity, Evidence, Reputation, Resilience)"]
        J --> K["Forensic Decision Audit Explorer"]
        J --> L["Borrower Recourse & Dispute Protocol"]
        K & L --> M["SHA-256 Cryptographic Event Ledger"]
        M --> N["Lending Lifecycle & Slashing Cascade"]
    end
```

---

## Component architecture

### 1. Ingestion and consent layer
- **Role:** Captures verified applicant declarations, consented account aggregator statements, and explicit peer endorsements.
- **Regulatory alignment:** Adheres to RBI Digital Lending Directions (2025) by requiring explicit, need-based borrower consent and object-level authorization.

### 2. Rule-based affordability engine
- **Formula:**
  $$D = I_{\text{net}} - E_{\text{essential}} - B_{\text{floor}}$$
- **Enforcement:**
  - Hard floor: Disposable income $D > 0$.
  - Fixed Obligation to Income Ratio (FOIR/ITI): $\le 40\%$.
  - Debt-to-Income (DTI): $\le 50\%$.
  - Protected cash buffer: $B_{\text{floor}} = \max(\text{₹3,000}, 0.15 \times I_{\text{net}})$, raised by 15% for partial or unverified data (completeness 0.50 to 0.85) and by 30% for a thin file (below 0.50).

### 3. Google OR-Tools CP-SAT optimizer
- **Role:** When an applicant's requested loan exceeds approved credit limits or monthly repayment caps, the optimizer searches the discrete $(P, T)$ grid to find the optimal feasible plan:
  - `MAX_PRINCIPAL`: Maximizes available loan capital within risk limits.
  - `MIN_COST`: Minimizes lifetime interest obligations.
- **Output:** Returns best feasible plan, monthly EMI, total interest, and binding constraints that disqualified alternative plans.

### 4. Web-of-Trust graph engine
- **Mathematical invariants:**
  1. *Out-degree capacity conservation:*
     $$\sum_{v \in \text{Out}(u)} W_{uv} \le C_u \quad \text{where } C_u = \max(0, R_u)$$
  2. *Chronological rank diminishing returns:* Incoming endorsements are weighted by immutable chronological arrival order:
     $$\alpha_{uv} = \frac{1}{2^{r_{uv} - 1}}$$
     The 1st voucher receives weight 1.0, 2nd receives 0.5, 3rd receives 0.25, rendering Sybil burst swarms mathematically ineffective.
  3. *Multi-hop path transmission:* Trust on path $P = (v_0, v_1, \dots, v_h)$ decays by node out-degrees, edge ranks, and hop attenuation:
     $$T(P) = R_{v_0} \cdot \prod_{i=0}^{h-1} \frac{1}{d_{v_i}} \cdot \prod_{i=0}^{h-1} \alpha_{v_i v_{i+1}} \cdot \delta^{h-1}$$
  4. *Same-source min-path consolidation & distinct aggregation:*
     $$p_u(s) = \min_{P \in \mathcal{P}(s, u)} T(P), \quad G(u) = \sum_{s \ne u} p_u(s), \quad G_{\text{score}}(u) = \min(G(u), G_{\text{max}})$$
  5. *Repeat transaction reputation minting:* Diminishing returns prevent transaction farming:
     $$M_k = M_0 \exp(-\lambda(k - 1)) \quad \text{with } \lambda = \ln(2) \approx 0.6931$$
  6. *Per-path cycle absorption:* Graph traversal tracks visited nodes per path branch, terminating circular loops without artificial gain.
  7. *Anchor grounding:* Trust propagates strictly from authorized institutional roots (`is_anchor=True`).

### 5. Monte Carlo stress tester
- **Role:** Tests repayment viability across 5,000 seeded stochastic economic futures over the proposed loan horizon.
- **Parameters:**
  - Income volatility: monthly income times a multiplier drawn from $\mathcal{N}(1, 0.15^2)$, floored at 0.
  - Payment receipt delays: $\text{Bernoulli}(0.05)$ per month; 40% of that month's income moves to the next month.
  - Emergency expenditure shocks: $\text{Bernoulli}(0.10)$ per month, cost drawn from $\mathcal{N}(4000, 2000^2)$ INR, floored at 0.
  - Seed 42, so runs are reproducible.
- **Diagnostics:** Shortfall risk %, 5th-percentile adverse cash cushion, and exact income drop tolerance before insolvency.

### 6. Explanation and forensic audit explorer
- **Role:** Synthesizes actionable audit reports across four orthogonal dimensions:
  1. *Financial capacity:* Verified disposable cash flow and binding policy constraints.
  2. *Evidence reliability:* Documentation confidence and data-quality grading.
  3. *Graph reputation:* Active Web-of-Trust paths and anchor endorsement weights.
  4. *Stress resilience:* Simulated shortfall risk and emergency shock tolerance.

### 7. Borrower recourse and dispute workflow
- **Role:** Allows borrowers to contest erroneous transactions or submit updated documentation without conflating data errors with economic repayment capacity.
- **Classification:** Categorizes records as `VERIFIED`, `MISSING`, `STALE`, `DUPLICATED`, or `DISPUTED`.
- **Ledger integration:** Logs all dispute filings and resolutions as immutable SHA-256 events.

### 8. Platform treasury and transaction fee cut
- **Role:** Ensures economic sustainability for protocol operators through an automated, auditable transaction fee cut.
- **Mechanism:**
  - Configurable fee rate cut (default: $1.0\%$ / 100 bps surcharge via `PLATFORM_FEE_RATE`).
  - Recorded on every `Transaction` (`amount`, `fee`, `net_amount`) across loan disbursements and repayments.
  - Surcharge collected into a centralized `PlatformTreasury` ledger balance, verifiable via `GET /api/v1/platform/treasury` and CLI `python main.py treasury`.
  - Audited in `LOAN_DISBURSED` and `LOAN_REPAID` ledger event payloads with deterministic disaster recovery replay.

### 9. Explainable ML and conformal uncertainty layer
- **Role:** Delivers predictive credit risk inference, Basel scorecard rating (300-900), and finite-sample uncertainty coverage alongside deterministic rule scoring.
- **Components:**
  - `POST /api/v1/predict` (`prediction.py`): deterministic risk rules over affordability, graph score and temporal confidence; it does not load the trained models.
  - Offline model palette (`backend/ml/`, benchmarks only): Glassbox Explainable Boosting Machines (EBM), XGBoost GPU with TreeSHAP, PyTorch GPU Tabular Net with Monte Carlo Dropout, LightGBM, and $L_2$ Logistic Scorecard.
  - Conformal Prediction Sets: Split and Mondrian conformal methods guaranteeing $\ge 90\%$ coverage with tri-state decisions (`ELIGIBLE`, `REVIEW`, `DECLINE_CANDIDATE`).
  - Additive Local Reasons: Inspectable log-odds contributions and observed values per risk factor.

---

## State machine and lifecycle

```mermaid
stateDiagram-v2
    [*] --> REGISTERED: Node created
    REGISTERED --> ACTIVE: Institutional vouch received
    ACTIVE --> VOUCHING: Allocates capacity (sum W <= C)
    ACTIVE --> BORROWING: Applies for loan (Affordability + OR-Tools + Monte Carlo)
    BORROWING --> ACTIVE: Loan fully repaid (+Reputation yield)
    BORROWING --> SUSPENDED: Payment missed (>30d grace)
    SUSPENDED --> DEFAULTED: Grace expired (4-level slashing cascade)
    DEFAULTED --> RESTRICTED: Capacity clamped to 0
    RESTRICTED --> [*]
```

---

## Data model relationships

```text
User (Node)
  ├── 1:N --> ConsentRecord (RBI Compliance)
  ├── 1:1 --> FinancialProfile (Income, Expenses, Debt)
  ├── 1:N --> Endorsement (Outbound Vouches)
  ├── 1:N --> LoanApplication (Borrowing Requests)
  └── 1:N --> EvidenceItem (Document Hashes)

LoanApplication
  ├── 1:1 --> Assessment (Affordability, OR-Tools, Monte Carlo)
  ├── 1:N --> RepaymentOutcome (Instalment Tracking)
  └── 1:N --> DisputeCase (Recourse Workflow)

ReputationLedger
  └── 1:N --> LedgerEvent (SHA-256 Chained Audit Trail)
```

---

## Production hardening and security

1. **Deterministic core:** Pure functions with `Decimal` arithmetic prevent floating-point drift in financial scoring.
2. **Cryptographic tamper evidence:** Every state mutation produces a cryptographically linked event hash (`prev_hash` chaining).
3. **Glassbox explainability and conformal bounds:** No opaque black-box models; predictive risk relies on Glassbox Explainable Boosting Machines (EBM), Scorecards, and finite-sample Conformal Prediction sets guaranteeing $\ge 90\%$ coverage across completeness tiers.
4. **Regulatory readiness:** Aligns with RBI Digital Lending Directions (2025) and Fair Credit Reporting standards.

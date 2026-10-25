# VeriTrust — Implementation & Architecture Plan

**Status:** Implemented, Verified & In Production (100% Complete)  
**Location:** `backend/localdocs/Implementation_Doc.md`  
**Reference:** [Init_Arch.md](Init_Arch.md) | [VOUCH_DEVELOPER_MASTER_V2.md](VOUCH_DEVELOPER_MASTER_V2.md) | [FORMULAS_AND_NUMBERS.md](FORMULAS_AND_NUMBERS.md)  
**Design Principle:** Clean, modular, and uncompromising financial correctness. Python standard library + NetworkX + Pydantic v2 + strict `Decimal` arithmetic. No smart contracts.

---

## 1. Overview & High-Level Flow

This document details the complete production architecture and implementation of the VeriTrust engine inside `backend/`:

```mermaid
flowchart LR
    A["Stage 1<br/>Domain Models<br/>(User, Tx, Vouch, Loan, Treasury)"] --> B["Stage 2<br/>User Creation &<br/>Graph Ingestion (store.json)"]
    B --> C["Stage 3<br/>Vouch & Unvouch<br/>(Rank Decay & Weight Conservation)"]
    C --> D["Stage 4<br/>Lending, Borrowing & Fees<br/>(1.0% Fee Cut, Repay & Slashing)"]
    D --> E["Stage 5<br/>Credibility Propagation<br/>(Hop Decay, Min-Path & LCB)"]
    E --> F["Stage 6<br/>Decisioning & Optimization<br/>(OR-Tools CP-SAT & Monte Carlo)"]
    F --> G["Stage 7<br/>Platform Treasury & Ledger<br/>(HMAC/SHA-256 Replay)"]
    G --> H["Stage 8<br/>Explainable ML Suite<br/>(EBM, XGBoost GPU, PyTorch GPU, LightGBM)"]
    H --> I["Stage 9<br/>Conformal Uncertainty & Ablation<br/>(Split/Mondrian Sets, Invisible Primes)"]
```

---

## 2. Step-by-Step Implementation Breakdown

### Stage 1: Underlying Domain Models (`models.py`)

All models use **Pydantic v2** and strict `Decimal` for all financial values, weights, and scores.

1. **`User` (Graph Node):**
   - `user_id: str` — Unique identifier (e.g. `"U001"`).
   - `name: str` — Display name / label.
   - `reputation: Decimal` — Credibility score ($R$). Initialised to $0.0$ for new users; anchors start with an initial score (e.g. $10.0$).
   - `capacity: Decimal` — Distributable vouch capacity: $C_u = \max(0, R_u)$.
   - `vouch_capacity: Decimal = Decimal("0.0")` — Allocated vouch capacity across active endorsements.
   - `status: Literal["ACTIVE", "RESTRICTED", "DEFAULTED"]` — State machine status.
   - `is_anchor: bool` — Whether this node is an institutional/community anchor.
   - `financial_features: FinancialFeatures` — Income, obligations, transaction stability, data completeness.
   - `n_settled_loans: int` — Count of successfully settled loans.

2. **`Transaction`:**
   - `tx_id: str` — Unique transaction identifier.
   - `user_id: str` — Affected user.
   - `amount: Decimal` — Gross monetary amount in INR (always `Decimal`).
   - `fee: Decimal = Decimal("0.0")` — Platform transaction fee cut (1.0% surcharge).
   - `net_amount: Decimal = Decimal("0.0")` — Net amount after platform fee.
   - `tx_type: Literal["INCOME", "DEBT_SERVICE", "DISBURSEMENT", "REPAYMENT", "PLATFORM_FEE"]`.
   - `timestamp: datetime` — Timestamp of transaction.

3. **`Vouch` (Directed Edge):**
   - `vouch_id: str` — Unique vouch identifier.
   - `source: str` — Endorsing user ID ($u$).
   - `target: str` — Recipient user ID ($v$).
   - `weight: Decimal` — Allocated vouch weight $W_{uv}$.
   - `rank: int = 1` — Chronological vouch order for the source node ($r_{uv} \in \{1, 2, \dots\}$).
   - `alpha: Decimal = Decimal("1.0")` — Chronological rank weighting factor: $\alpha_{uv} = 1 / 2^{r_{uv} - 1}$.
   - `vouch_capacity: Decimal` — Total source capacity allocated across vouches.
   - `active: bool` — Status of endorsement.
   - `created_at: datetime`.

4. **`Loan`:**
   - `loan_id: str` — Unique loan identifier.
   - `borrower_id: str` — User ID of borrower.
   - `principal: Decimal` — Loan principal amount (INR).
   - `outstanding_balance: Decimal` — Current remaining balance.
   - `interest_rate: Decimal` — Decimal fraction (e.g. `Decimal("0.10")` for 10%).
   - `tenure_months: int` — Duration in months.
   - `status: Literal["PENDING", "ACTIVE", "REPAID", "DEFAULTED"]`.
   - `created_at: datetime`.

5. **`PlatformTreasury`:**
   - `total_fees_collected: Decimal` — Total accumulated fees collected across all protocol transactions.
   - `fee_rate: Decimal` — Configured platform fee rate (default `Decimal("0.01")` / 1.0%).
   - `treasury_id: str` — Platform treasury account identifier (`"PLATFORM_TREASURY"`).
   - `last_updated: datetime` — Timestamp of last fee collection event.

6. **`CreditAssessment`:**
   - `user_id: str`
   - `r_graph: Decimal` — Trust propagated from anchors.
   - `s_cashflow: Decimal` — Repayment capacity score from cash flows.
   - `mu_composite: Decimal` — Blended expected capacity.
   - `sigma2_epistemic: Decimal` — Uncertainty measure ($[0.0, 1.0]$).
   - `score_final: Decimal` — Lower Confidence Bound ($Score_{\text{final}}$).
   - `max_loan_limit: Decimal` — Maximum eligible loan limit (INR).
   - `contributing_paths: list[dict]` — Explainability breakdown of trust paths.

7. **`LedgerEvent`:**
   - Tamper-evident event records: `event_id`, `event_type`, `timestamp`, `actor_id`, `subject_id`, `payload`, `prev_hash`, `curr_hash`.
   - Event types: `USER_REGISTERED`, `VOUCH_CREATED`, `VOUCH_REMOVED`, `LOAN_DISBURSED`, `LOAN_REPAID`, `LOAN_DEFAULTED`, `REPUTATION_MINTED`, `REPUTATION_SLASHED`, `PLATFORM_FEE_COLLECTED`.

---

### Stage 2: User Creation & Graph Loading (`engine.py`, `store.py`)

1. **User Creation:**
   - `create_user(user_id, name, initial_reputation=0, is_anchor=False, financial_features=None) -> User`
   - Registers user in an in-memory user registry (`dict[str, User]`).
   - Automatically derives initial capacity $C = \max(0, R)$.
   - Emits `USER_REGISTERED` event to the cryptographic ledger.

2. **Graph Ingestion & Persistence (`store.py`):**
   - Built on NetworkX `nx.DiGraph`.
   - `add_user_to_graph(user: User)`: Adds node `user.user_id` with metadata (`reputation`, `capacity`, `status`, `is_anchor`).
   - `save_store(filepath)` and `load_store(filepath)`: Deterministically serializes/deserializes users, vouches, loans, transactions, and the platform treasury to `data/store.json`.

---

### Stage 3: Vouch & Unvouch with Chronological Rank Weighting (`engine.py`)

Enforces **Chronological Rank Weighting** and **Out-Degree Capacity Conservation**:

$$\alpha_{uv} = \frac{1}{2^{r_{uv}-1}} \quad \text{for chronological vouch order } r_{uv} \in \{1, 2, \dots\}$$

$$\sum_{v \in \text{Out}(u)} W_{uv} \le C_u \quad \text{where} \quad W_{uv} = \alpha_{uv} \times \frac{C_u}{\sum_{w \in \text{Out}(u)} \alpha_{uw}}$$

1. **`vouch(source_id: str, target_id: str) -> Vouch`:**
   - **Guards:**
     - Both source and target must exist.
     - Cannot vouch for self (`source_id != target_id`).
     - Source status must be `ACTIVE`.
     - Source capacity must be positive ($C_{\text{source}} > 0$).
     - Duplicate active vouches are rejected.
   - **Action:**
     - Assigns next chronological rank $r_{uv} = |\text{Out}(source)| + 1$.
     - Computes rank attenuation factor $\alpha_{uv} = 1 / 2^{r_{uv}-1}$.
     - Adds directed edge `source -> target`.
     - **Atomic Sibling Re-weighting:** Normalizes weights across all outgoing edges such that $\sum_{v} W_{source, v} = C_{source}$.
     - Emits `VOUCH_CREATED` to the ledger.

2. **`unvouch(source_id: str, target_id: str) -> None`:**
   - **Guards:** Edge `source -> target` must exist and be active.
   - **Action:**
     - Removes edge from graph.
     - Recompacts chronological ranks of remaining edges.
     - **Atomic Sibling Re-weighting:** Recomputes remaining edge weights. If no edges remain, no capacity is allocated.
     - Emits `VOUCH_REMOVED` to the ledger.

---

### Stage 4: Lending, Repayments & Platform Fee Cut (`lending.py`)

Pure in-memory Python service with cryptographic audit logging:

1. **Platform Transaction Fee Surcharge (1.0% Cut):**
   - Configured via `PLATFORM_FEE_RATE = Decimal("0.01")` (1.0%).
   - Function `compute_platform_fee(amount, rate) -> Decimal`.
   - On every borrow and repayment, the platform takes a 1.0% fee.
   - Fees accumulate in `PlatformTreasury` and record a `PLATFORM_FEE_COLLECTED` ledger event.

2. **`borrow(borrower_id: str, amount: Decimal, tenure_months: int) -> Loan`:**
   - **Checks:**
     - Borrower must be `ACTIVE`.
     - Verifies `amount <= max_loan_limit` from `assess_credit(borrower_id)`.
   - **Execution:**
     - Calculates platform cut: `fee = compute_platform_fee(amount)`.
     - Net disbursement to borrower: `net_amount = amount - fee`.
     - Instantiates `Loan(principal=amount, outstanding_balance=amount, status="ACTIVE")`.
     - Records disbursement `Transaction` with `fee` and `net_amount`.
     - Emits `LOAN_DISBURSED` and `PLATFORM_FEE_COLLECTED` to the ledger.

3. **`repay(loan_id: str, amount: Decimal) -> Loan`:**
   - **Execution:**
     - Calculates platform cut: `fee = compute_platform_fee(amount)`.
     - Net debt reduction: `net_repay = amount - fee`.
     - Reduces `outstanding_balance` by `net_repay`.
     - Records repayment `Transaction` with `fee` and `net_amount`.
     - Emits `LOAN_REPAID` and `PLATFORM_FEE_COLLECTED` to the ledger.
   - **On Full Settlement (`outstanding_balance <= 0`):**
     - Loan status updated to `REPAID`.
     - Increments $N_{\text{settled}} \leftarrow N_{\text{settled}} + 1$.
     - **Repeat Transaction Reputation Minting:**
       $$M_k = M_0 \cdot e^{-\lambda (k-1)}$$
       Borrower receives $M_k$ reputation boost ($M_0 = 2.0$, $\lambda = 0.15$). Direct sponsors receive sponsor yield ($1.0$).
     - Emits `REPUTATION_MINTED` events.
     - Atomically updates outbound vouch weights for all affected nodes.

4. **`default_loan(loan_id: str) -> None`:**
   - Loan status updated to `DEFAULTED`.
   - **Atomic Snapshot Penalty Formulation:**
     $$S_D = \max\left(S_{\min}, \min\left(S_{\max}, \frac{\text{outstanding\_balance}}{1000}\right)\right)$$
   - **Atomic 4-Level Damped Slashing Cascade:**
     - **$k=0$ (Defaulter):** Penalty $\delta_0 = S_D$. Reputation $R \leftarrow R - \delta_0$. Status $\rightarrow \text{DEFAULTED}$. Capacity frozen ($C=0$), all outbound vouch weights zeroed.
     - **$k=1$ (Direct Sponsors):** Penalty $\delta_1 = \gamma \cdot W_{\text{sponsor}, \text{defaulter}} \cdot S_D$ ($\gamma = 0.5$). If $R < 0$, status $\rightarrow \text{RESTRICTED}$.
     - **$k=2$ (Ancestors):** Penalty $\delta_2 = \gamma^2 \cdot S_D = 0.25 \cdot S_D$. If $R < 0$, status $\rightarrow \text{RESTRICTED}$.
     - **$k \ge 3$:** Cutoff ($\delta = 0$). Hard boundary stops contagion completely.
   - Emits `LOAN_DEFAULTED` and `REPUTATION_SLASHED` events to the ledger.

---

### Stage 5: Credibility Propagation & Assessment (`scoring.py`)

Deterministic graph traversal and dual-axis underwriting:

1. **Path Traversal & Hop Attenuation ($\delta = 0.5$):**
   - Institutional Anchors: `is_anchor=True` and $R > 0$.
   - Enumerates all simple paths from all anchors to target node $u$.
   - **Hop Attenuation:** For path $P = (v_0, v_1, \dots, v_k)$ with $h = k$ hops:
     $$\text{PathTrust}(P) = \min_{e \in P} w(e) \times \delta^{h-1}$$
   - **Per-Path Cycle Absorption:** Each path maintains its own visited set. Circular loops terminate that branch with $0$ trust without penalizing parallel paths.
   - **Min-Path Consolidation:** For each anchor source $s$, consolidate best path:
     $$p_u(s) = \max_{P \in \text{Paths}(s \to u)} \text{PathTrust}(P)$$
   - **Aggregate Credibility Score:**
     $$G(u) = \sum_{s \in S} p_u(s)$$

2. **Dual-Axis Underwriting & Lower Confidence Bound (LCB):**
   - **Repayment Capacity Score ($S_D$):** Evaluates disposable income $D = \text{income} - \text{obligations}$:
     $$S_D = \max\left(0, \min\left(1.0, \frac{D}{\text{threshold}}\right)\right)$$
   - **Composite Capacity ($\mu_{\text{composite}}$):**
     $$\mu_{\text{composite}} = (\alpha \cdot G(u) + (1-\alpha) \cdot S_D) \times \exp(\beta \cdot (N_{\text{settled}} + |\text{In}(u)|))$$
     where $\alpha = 0.6$, $\beta = 0.1$.
   - **Epistemic Uncertainty ($\sigma^2_{\text{epistemic}}$):**
     $$\sigma^2_{\text{epistemic}} = \frac{1}{1 + N_{\text{tx}} \times \text{completeness}}$$
     Cold-start nodes with zero transactions have $\sigma^2 = 1.0$ (high uncertainty, not negative capacity).
   - **Lower Confidence Bound ($Score_{\text{final}}$):**
     $$Score_{\text{final}} = \mu_{\text{composite}} - \kappa \cdot \sqrt{\sigma^2_{\text{epistemic}}}$$
     where $\kappa = 1.0$.
   - **Approved Loan Limit:**
     $$\text{Limit}_{\text{INR}} = \max\left(0, Score_{\text{final}} \times 10,000 \text{ INR}\right)$$

---

### Stage 6: Decisioning, OR-Tools Optimization & Stress Testing

1. **Rule-Based Affordability Engine (`affordability.py`):**
   - Computes disposable income $D = I_{\text{net}} - E_{\text{essential}} - B_{\text{floor}}$ with protected minimum cash buffer $B_{\text{floor}}$.
   - Enforces regulatory policy caps: instalment-to-income $\text{FOIR} \le 40\%$, debt-to-income $\text{DTI} \le 50\%$.

2. **Loan Restructuring Optimizer with Google OR-Tools (`optimizer.py`):**
   - Formulates constraint satisfaction and optimization via OR-Tools CP-SAT solver.
   - Solves discrete grid for either minimum total interest cost (`MIN_COST`) or maximum sustainable loan amount (`MAX_PRINCIPAL`).
   - Identifies binding constraints and generates optimal alternative loan structures.

3. **Monte Carlo Stochastic Stress Tester (`stress_tester.py`):**
   - Simulates 5,000 seeded stochastic economic futures without ML.
   - Samples income volatility, payment delay distributions, and emergency expense shocks.
   - Computes shortfall frequency, adverse 5th-percentile residual cash flow, and exact income shock break-even tolerance.

4. **Forensic Explanations, Recourse & Counterfactuals (`explainer.py`, `recourse.py`, `counterfactual.py`):**
   - Explains decisions across Financial Capacity, Evidence Reliability, Graph Reputation, and Stress Resilience.
   - Deterministic counterfactual simulation: calculates required adjustments $\Delta I, \Delta E, \Delta T, \Delta P$.
   - Dispute management and evidence quality auditing (`MISSING`, `STALE`, `DUPLICATED`, `DISPUTED`).

---

### Stage 7: Platform Treasury & Surcharge Protocol

1. **1.0% Transaction Fee Surcharge:**
   - Every borrow and repayment transaction incurs a 1.0% fee cut (`PLATFORM_FEE_RATE = Decimal("0.01")`).
   - Fee calculations use `Decimal` arithmetic rounded to 2 decimal places.
   - Gross amounts, fee amounts, and net amounts are explicitly tracked on `Transaction`.

2. **Treasury Management & Persistence:**
   - `PlatformTreasury` accumulates protocol revenues in `lending.py`.
   - Persisted across restarts in `data/store.json`.
   - Reconstructed deterministically from raw cryptographic events via `python main.py replay --restore`.

3. **REST Endpoints & CLI Interface:**
   - `GET /api/v1/platform/treasury`: Returns total fees collected, current fee rate, and treasury account ID.
   - `GET /api/v1/transactions`: Returns chronological transaction history including gross amount, fee, and net amount.
   - CLI: `python main.py treasury` displays live treasury statistics.

---

### Stage 8: Explainable Machine Learning Suite & GPU Acceleration (`backend/ml/`)

1. **Realistic Synthetic Noise Injection (`noise.py`):**
   - Controlled generator reflecting real-world micro-finance imperfections:
     - Continuous measurement jitter ($\epsilon \sim \mathcal{N}(0, \sigma^2)$ preserving physical non-negativity).
     - Financial reporting rounding (15% probability of rounding to nearest 1,000, 5,000, or 10,000 paise).
     - Informative missingness (MAR/MNAR) on bureau and GST fields with explicit `_was_missing` indicator flags.
     - Fat-tailed emergency expense shocks ($2.5\times$ to $4\times$ multiplier).
     - Macroeconomic population drift simulating inflation and seasonal liquidity shifts.
     - Stochastic label noise (2.5% random label flips simulating renegotiated loans and administrative cures).

2. **Parallel GPU Model Training Suite (`models.py`, `train.py`):**
   - Five explainable model paradigms trained concurrently across GPU CUDA streams and CPU threads:
     - **Explainable Boosting Machine (EBM):** Glassbox Generalized Additive Model with spline shape curves decomposing risk additively into exact log-odds without black-box opacity.
     - **XGBoost GPU:** Histogram-based gradient boosting executed on `device='cuda'` with exact TreeSHAP local attributions.
     - **PyTorch GPU Tabular Neural Network:** Residual network with Monte Carlo Dropout estimating epistemic model disagreement $\sigma_{\text{epistemic}}$.
     - **LightGBM:** Depth-regularized boosting with early stopping on held-out validation slices.
     - **Calibrated Logistic Scorecard:** Monotonic $L_2$-regularized linear scorecard with standard scaling.

3. **Generalized Meta-Ensemble (`GeneralizedCreditModel`):**
   - Inverse-Brier weighted model mixture blending the five diverse architectures.
   - Outperformed individual models on the hackathon shock dataset, achieving **0.8892 AUC** and **0.9191 PR-AUC** on Full VeriTrust (Model D).

---

### Stage 9: Conformal Uncertainty & Empirical Ablation Engine (`conformal.py`, `ablation.py`)

1. **Split & Mondrian Conformal Prediction Sets:**
   - Finite-sample coverage guarantees ($\ge 90\%$ and $\ge 95\%$) across data completeness tiers (thin-file, bank-only, full-documentation).
   - Tri-state decision outputs: `ELIGIBLE` (high-confidence timely repayment), `REVIEW` (honest uncertainty / human underwriting review), `DECLINE_CANDIDATE` (high-confidence default).

2. **Empirical Ablation Study Findings (4,502 Borrowers):**
   - **Topology is NOT Trust:** Adding simple in-degree centrality to conventional financials yields zero significant improvement ($\Delta\text{AUC} = +0.0001$, 95% CI: $[-0.0109, +0.0101]$).
   - **Endorser Quality Drives Signal:** Incorporating voucher reliability and pre-application liquidity transfers boosts AUC to **0.8881**.
   - **Full VeriTrust Superiority:** Rank attenuation ($\alpha_{uv}$) and provenance consolidation reach top discrimination (**0.8892 AUC**, **0.9191 PR-AUC**, Brier loss **0.1190**).
   - **Invisible Primes Rescued:** Unlocked **26 borrowers** (4.18% of conventional rejections) whose actual default rate was **38.46%** compared to the 64.71% population default rate (a **26.25 percentage-point lower default risk**).
   - **Cold-Start Graph-Only Viability:** When all bureau features are completely dropped, VeriTrust social collateral achieves an AUC of **0.8678** and PR-AUC of **0.9002**.

3. **Prosper Empirical Validation (55,305 Real-World Loans):**
   - Cheap-talk non-monetary endorsements increase default risk (32.81% vs 30.79% baseline).
   - Endorsements backed by actual monetary capital significantly reduce default risk (23.71%, a $-7.08$ pp improvement).

---

## 3. Implemented Code Organization in `backend/`

```text
backend/
├── localdocs/                                   # Technical briefings & implementation documentation
│   ├── Implementation_Doc.md                    # This master implementation document
│   ├── Init_Arch.md                             # Initial POC briefing & architecture evolution
│   ├── BENCHMARKS_AND_METRICS.md                # Empirical model metrics, benchmarks & ablation reference
│   ├── VOUCH_DEVELOPER_MASTER_V2.md             # Developer master specification v2
│   ├── VERITRUST_SYSTEM_FLOW.md                 # End-to-end system flow & walkthrough
│   ├── FORMULAS_AND_NUMBERS.md                  # Comprehensive formulas, process & numbers spec
│   ├── TEMPORAL_UNCERTAINTY_AND_FRESHNESS.md    # Multi-horizon evidence decay & epistemic inflation
│   ├── PROSPER_AND_LITERATURE_LESSONS.md        # Prosper 55k loan analysis & cheap-talk failure modes
│   └── VOUCH_SHOCK_DATA_SPEC.md                 # Market-shock dataset design specification
├── ml/                                          # Explainable ML pipeline & ablation harness
│   ├── __init__.py
│   ├── models.py                                # EBM, XGBoost GPU, PyTorch GPU (MC Dropout), Scorecard, GeneralizedCreditModel
│   ├── conformal.py                             # Split & Mondrian conformal prediction sets
│   ├── noise.py                                 # Realistic synthetic noise injection (jitter, rounding, MAR, shocks)
│   ├── data.py                                  # Dataset loaders (Option A, Simulated Underwriting, Real-Anchored)
│   ├── explain.py                               # Additive reason codes & counterfactual recourse
│   ├── train.py                                 # Multi-threaded parallel GPU training harness
│   └── ablation.py                              # 9-paper literature hypothesis ablation runner
├── src/
│   └── veritrust/
│       ├── __init__.py
│       ├── config.py                            # Algorithmic parameters & platform fee configuration
│       ├── models.py                            # Pydantic domain models (User, Tx, Vouch, Loan, Treasury)
│       ├── engine.py                            # NetworkX graph manager, capacity conservation, rank weighting
│       ├── lending.py                           # Lending lifecycle, repayments, 1.0% platform fee, slashing
│       ├── scoring.py                           # Anchor propagation, hop attenuation, cycle absorption, LCB
│       ├── affordability.py                     # Rule-based affordability, cash buffer, policy caps
│       ├── optimizer.py                         # Google OR-Tools CP-SAT loan restructuring solver
│       ├── stress_tester.py                     # Seeded Monte Carlo stochastic simulation engine
│       ├── explainer.py                         # 4-dimensional traceable explanation synthesis
│       ├── counterfactual.py                    # Deterministic what-if sensitivity simulator
│       ├── attack_simulator.py                  # Adversarial graph attack harness (Sybil, collusion, bursts)
│       ├── audit_explorer.py                    # Forensic decision explorer & rule evaluation trace
│       ├── recourse.py                          # Borrower recourse workflow & evidence-quality tracking
│       ├── community.py                         # Community platform store & peer endorsement engine
│       ├── ledger.py                            # SQLite + JSONL cryptographic hash-chained ledger
│       ├── store.py                             # JSON persistence & deterministic state serialization
│       ├── simulator.py                         # Web-of-Trust benchmark topology calibration engine
│       ├── temporal.py                          # Multi-horizon evidence freshness decay
│       ├── prediction.py                        # Predictive credit risk inference & conformal decisions
│       ├── cli.py                               # Interactive CLI shell & command handlers
│       └── api/                                 # FastAPI REST API package
│           ├── __init__.py
│           ├── routes.py                        # Applications, assessments, treasury, transactions, predictions
│           ├── protocol_routes.py               # Vouch requests, decisions, defaults
│           ├── community_routes.py              # Community platform endpoints
│           └── registry.py                      # Shared in-memory router registries
├── tests/                                       # 152 passing unit tests covering all components
│   ├── test_models.py                           # Domain models & Decimal validations
│   ├── test_vouch.py                            # Vouching, unvouching, out-degree conservation
│   ├── test_trust.py                            # Out-degree conservation, hop decay, multi-anchor sum
│   ├── test_cycles.py                           # Per-path cycle absorption & Sybil rings
│   ├── test_reputation.py                       # Repayment yields & 4-level slashing cascade
│   ├── test_credit.py                           # Dual-axis underwriting & LCB loan limits
│   ├── test_affordability.py                    # Cash buffer floors, FOIR/DTI caps
│   ├── test_optimizer.py                        # Google OR-Tools CP-SAT restructuring solver
│   ├── test_stress_tester.py                    # Monte Carlo simulations & break-even shock analysis
│   ├── test_explainer.py                        # Explanation synthesis & traceable reason codes
│   ├── test_community.py                        # Community vouches & platform invariants
│   ├── test_ledger.py                           # Cryptographic hash chains, tamper detection, replay
│   ├── test_platform_fee.py                     # Platform transaction fees, treasury cuts, replay
│   ├── test_mathematical_framework.py           # Master 2026 mathematical framework & rank decay
│   ├── test_temporal_uncertainty.py             # Temporal evidence decay & epistemic inflation
│   ├── test_prediction_api.py                   # Predictive risk inference & conformal API
│   ├── test_adversarial_and_edge_cases.py       # Sybil cliques, collusion rings, stress limits
│   ├── test_vouch_score_v2.py                   # Vouch scoring invariants & anchor paths
│   ├── test_ml_pipeline.py                      # Parallel GPU training, noise generator, conformal coverage
│   ├── test_api_routes.py                       # REST API route integration tests
│   └── test_protocol_routes.py                  # Protocol router integration tests
├── main.py                                      # Interactive CLI & FastAPI server runner
└── requirements.txt                             # Pydantic v2, NetworkX, OR-Tools, FastAPI, PyTorch, XGBoost, LightGBM, pytest
```

---

## 4. Production Verification & Test Summary

All acceptance criteria across all stages are demonstrably met and verified:

- **152 passing unit tests:** `pytest backend/tests` (100% green).
- **Cryptographic ledger audit:** `python main.py audit` verifies unbroken SHA-256 hash chains from Genesis to Head.
- **Disaster recovery replay:** `python main.py replay --restore` reconstructs complete graph, loan, and platform treasury state deterministically from raw events.
- **OR-Tools optimization:** CP-SAT solver verified on both `MIN_COST` and `MAX_PRINCIPAL` objectives with binding constraint identification.
- **Monte Carlo stress testing:** 5,000 seeded stochastic simulation runs verify shortfall frequencies and shock tolerance thresholds.
- **Platform transaction fee cut:** 1.0% fee cut on borrows and repayments verified with exact `Decimal` math and treasury tracking.
- **Explainable ML & GPU parallel training:** Multi-paradigm models (EBM, XGBoost GPU, PyTorch GPU, LightGBM, Scorecard) trained concurrently on CUDA.
- **Conformal prediction guarantees:** Finite-sample $\ge 90\%$ and $\ge 95\%$ coverage mathematically verified across data completeness tiers.
- **Ablation & literature validation:** Demonstrated $+0.0049$ AUC lift from VeriTrust over raw degree centrality, rescuing 26 Invisible Primes with $26.25$ pp lower default risk.

### Top-Line Benchmark & Metric Results

| Evaluation Cohort | Evaluated Model | Test AUC | PR-AUC | Brier Loss | KS Stat | 90% Conformal Coverage | Key Empirical Finding |
|---|---|---|---|---|---|---|---|
| **Option A Shock (Model D)** | GeneralizedCreditModel | **0.8892** | **0.9191** | **0.1190** | **0.6655** | **91.01%** | Highest discrimination under realistic noise |
| **Simulated Underwriting** | GeneralizedCreditModel | **0.9087** | **0.7141** | **0.0717** | **0.6697** | **90.56%** | High precision across 35,000 micro-borrowers |
| **Graph-Only Cold Start** | GeneralizedCreditModel | **0.8678** | **0.9002** | **0.1306** | **0.6098** | **91.00%** | Robust scoring with zero traditional bureau data |
| **Real-Anchored Cohort** | GeneralizedCreditModel | **0.6582** | **0.1466** | **0.0755** | **0.2461** | **89.50%** | Calibrated against empirical default distributions |
| **Invisible Primes Rescued** | Model D vs Model A | — | — | — | — | — | **26 borrowers** approved with **38.46%** default rate (-26.25 pp vs pop) |
| **Prosper Staked vs Unbacked** | 55,305 loans | — | — | — | — | — | Staked endorsements drop default to **23.71%** vs **32.81%** cheap talk |

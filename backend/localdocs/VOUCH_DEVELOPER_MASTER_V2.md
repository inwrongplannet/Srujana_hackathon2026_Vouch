# Vouch developer master documentation — version 2

**Why this file exists:** comprehensive master technical specification, architecture, mathematical formulation, and expanded scenario analysis for the Vouch fair and explainable creditworthiness assessment platform (F-04).

## Status and disclaimer
- **Document status:** Production reference specification and verified architecture design.
- **Scope note:** Stack, schemas, endpoints, weights, and mathematical formulations below represent the production reference design. All features built in code are verified against the 134-test harness.

---

## 1. Executive summary

Vouch is a complementary credit-assessment layer, not a replacement for CIBIL, Experian, or other authorized credit bureau scores. It adds a peer-endorsement graph and a bounded Vouch Score alongside conventional credit information, repayment affordability, data quality indicators, and explicit explanations.

The primary target cases are:
1. **First-time / thin-file borrowers:** Individuals with no formal credit history whose creditworthiness must not be assumed negative merely due to absent records.
2. **Temporary financial shocks:** Borrowers whose bureau score declined following an isolated, reviewable event (e.g. emergency expense) while their underlying earning and repayment capacity remains intact.

The system enforces a strict invariant: **The platform must not infer that a borrower is safe merely because peers vouch for them, nor infer inability to repay from absent credit history.**

### Core assessment outputs
- **Bureau score:** Displays the score from an authorized bureau with source and timestamp; never fabricates an official score.
- **Vouch Score (0–100):** A bounded measure of outcome-aware peer endorsements, not a raw default probability.
- **Affordability:** Verified income stability, non-discretionary obligations, estimated disposable cash flow ($D$), and proposed-loan EMI.
- **Explainability:** Evidence-backed positive and negative reason codes, missing information disclosures, confidence ratings, and scenario sensitivity.
- **Decision support:** Flags cases for informed human underwriter review; does not make opaque automated approval or rejection decisions.

---

## 2. Problem statement mapped to requirements

| Pain point | System response |
|---|---|
| **No or limited credit history** | Treat bureau history as unavailable/no-file, not as negative repayment behavior. Use verified income, cash buffers, and obligations; optionally incorporate Vouch relational evidence. |
| **Score may not reflect current circumstances** | Display bureau score, current cash-flow affordability, and data freshness as three distinct, unblended signals. |
| **Temporary financial shock** | Surface unusual expense spikes or revolving utilization surges as reviewable events only when supported by evidence, without jumping to adverse conclusions. |
| **Black-box credit assessment** | Return machine-readable reason codes, evidence source URIs, timestamps, uncertainty metrics, and missing field declarations. |
| **Endorsement gaming and collusion** | Enforce diminishing returns, individual commitment caps, reciprocal cycle absorption, and verified outcome conditioning. |
| **Fairness and incomplete data** | Low data quality produces an explicit uncertainty rating or review flag—never an invented default value or automated adverse rejection. |

---

## 3. Recommended technical stack

| Layer | Recommendation | Technical notes |
|---|---|---|
| **Frontend** | React + TypeScript + Vite + Tailwind CSS | Borrower onboarding, endorsement workflow, what-if counterfactual exploration, and bank underwriter dashboard. |
| **Backend API** | Python 3.12+ + FastAPI + Pydantic v2 | Typed request/response validation, automated OpenAPI docs, and strict `Decimal` financial arithmetic. |
| **Database** | PostgreSQL | Users, consent records, applications, endorsements, outcomes, assessments, and tamper-evident event log. |
| **Graph engine** | PostgreSQL edge relations; NetworkX for graph traversal | Multi-hop trust propagation, per-path cycle absorption, and capacity conservation checks. |
| **Async jobs** | Redis + RQ/Celery (optional) | Asynchronous document parsing and Monte Carlo scenario batch runs. |
| **Explainability** | Deterministic rule engine + reason codes | Explicit mathematical threshold evaluation; optional LLM phrasing constrained strictly to observed inputs. |
| **Testing** | pytest, HTTPX, React Testing Library | Unit, API, stress testing, and adversarial graph attack harnesses. |
| **Deployment** | Docker Compose | Reproducible local and staging deployment with environment configuration isolation. |

---

## 4. Architecture and repository layout

```text
React UI (Frontend)
 | HTTPS + authenticated requests
 v
FastAPI Modular Monolith (Backend)
 ├── authentication / authorization / consent
 ├── borrower profile and evidence metadata
 ├── loan application and affordability calculator
 ├── vouch graph and score engine
 ├── assessment + explainability report
 └── audit / dispute recourse workflow
 |   |
 v   v
 PostgreSQL       Private Document Storage
 |
 Redis / Worker (Optional)

backend/
├── main.py                                      # Application entry point / CLI / server
├── src/veritrust/
│   ├── api/                                     # HTTP endpoints (routes, protocol_routes, community_routes)
│   │   ├── routes.py                            # Applications, assessments, platform treasury, transactions
│   │   ├── protocol_routes.py                   # Vouch requests, loan decisions, default triggers
│   │   ├── community_routes.py                  # Community platform endpoints
│   │   └── registry.py                          # In-memory storage registries
│   ├── config.py                                # Algorithmic parameters & platform fee configuration
│   ├── store.py                                 # JSON persistence & deterministic state serialization
│   ├── models.py                                # Pydantic domain schemas with Decimal validation
│   ├── engine.py                                # NetworkX graph builder, capacity conservation, rank weighting
│   ├── lending.py                               # Lending lifecycle, repayments, 1.0% fee cut, & 4-level slashing
│   ├── scoring.py                               # Dual-axis LCB scoring & graph trust propagation
│   ├── affordability.py                         # Rule-based affordability & cash buffer engine
│   ├── optimizer.py                             # Google OR-Tools CP-SAT restructuring solver
│   ├── stress_tester.py                         # Monte Carlo stochastic scenario simulation
│   ├── counterfactual.py                        # Deterministic what-if sensitivity simulator
│   ├── attack_simulator.py                      # Adversarial graph vulnerability harness
│   ├── audit_explorer.py                        # Forensic decision explanation & rule trace
│   ├── recourse.py                              # Borrower dispute & evidence-quality tracking
│   ├── community.py                             # Community platform store & peer endorsement engine
│   ├── simulator.py                             # Web-of-Trust benchmark topology calibration engine
│   └── ledger.py                                # SHA-256 tamper-evident reputation event ledger
└── tests/                                       # 134 passing test suites
```

---

## 5. Domain data model

| Entity | Core schema fields | Purpose |
|---|---|---|
| `User` | `id` (UUID/str), `display_name`, `verification_status`, `is_anchor`, `reputation`, `capacity`, `vouch_capacity`, `created_at` | Participant identity and reputation anchor. |
| `ConsentRecord` | `user_id`, `purpose`, `scope`, `granted_at`, `revoked_at`, `policy_version` | Regulatory consent tracking per RBI guidelines. |
| `FinancialProfile` | `user_id`, `monthly_net_income`, `income_stability`, `essential_expenses`, `existing_debt`, `updated_at` | Baseline financial capacity inputs. |
| `LoanApplication` | `id`, `borrower_id`, `principal`, `annual_rate`, `term_months`, `purpose_category`, `status` | Credit request specification. |
| `EvidenceItem` | `id`, `owner_id`, `type`, `source`, `observed_at`, `verified_at`, `confidence`, `uri_or_hash` | Supporting factual documentation. |
| `Endorsement` / `Vouch` | `id`, `source`, `target`, `weight`, `rank`, `alpha`, `active`, `created_at` | Directed Web-of-Trust vouch relation with chronological rank weighting. |
| `Transaction` | `tx_id`, `user_id`, `amount`, `fee`, `net_amount`, `tx_type`, `timestamp` | Financial ledger transaction with platform fee cut tracking. |
| `PlatformTreasury` | `total_fees_collected`, `fee_rate`, `treasury_id`, `last_updated` | Tracks platform surcharge revenue accumulated across protocol transactions. |
| `RepaymentOutcome` | `application_id`, `period`, `due_amount`, `paid_amount`, `paid_date`, `dispute_status` | Repayment lifecycle verification. |
| `Assessment` | `application_id`, `bureau_status`, `bureau_score`, `vouch_score`, `affordability_status`, `lcb_score`, `reasons` | Multi-dimensional credit assessment snapshot. |
| `AuditEvent` | `event_id`, `prev_hash`, `actor_id`, `event_type`, `timestamp`, `payload_hash` | SHA-256 cryptographically chained audit record (`PLATFORM_FEE_COLLECTED`, etc.). |

---

## 6. Vouch network and graph mathematics

### 6.1 Endorsement edge weighting and rank decay
For a directed edge from endorser $u$ to recipient $v$, the effective weight $W_{uv}$ is derived from the chronological rank $r_{uv} \in \{1, 2, \dots\}$:

$$\alpha_{uv} = \frac{1}{2^{r_{uv}-1}}$$

Weights are conserved and normalized across all active outgoing edges from $u$:

$$W_{uv} = \alpha_{uv} \times \frac{C_u}{\sum_{w \in \text{Out}(u)} \alpha_{uw}} \quad \text{such that} \quad \sum_{v \in \text{Out}(u)} W_{uv} \le C_u$$

Where:
- $C_u = \max(0, R_u)$: Distributable vouch capacity of endorser $u$.
- $r_{uv}$: The 1-based chronological order in which the vouch was created.
- Sibling re-weighting is executed atomically whenever an edge is added or removed.

### 6.2 Path trust and anchor propagation
When trust propagates across multi-hop path $P = (v_0, v_1, \dots, v_k)$ of length $h = k$ hops originating from an institutional anchor node $s$:

$$\text{PathTrust}(P) = \min_{e \in P} w(e) \times \delta^{h-1} \quad (\text{geometric hop decay } \delta = 0.5)$$

Paths are consolidated per anchor $s$ to target $u$:

$$p_u(s) = \max_{P \in \text{Paths}(s \to u)} \text{PathTrust}(P)$$

The composite Web-of-Trust credibility score aggregates anchor contributions:

$$G(u) = \sum_{s \in S} p_u(s)$$

### 6.3 Dynamic reputation update rule
Reputation updates follow outcome-conditioned, bounded rules:

1. **Successful settlement (repeat transaction minting):**
   $$M_k = M_0 \cdot e^{-\lambda (k-1)} \quad (M_0 = 2.0, \lambda = 0.15)$$
   Borrower reputation increases by $M_k$ on their $k$-th settled loan. Direct sponsors receive sponsor yield ($+1.0$).

2. **Atomic snapshot default penalty:**
   $$S_D = \max\left(S_{\min}, \min\left(S_{\max}, \frac{\text{outstanding\_balance}}{1000}\right)\right)$$

3. **4-Level Damped Slashing Cascade:**
   - **$k=0$ (Defaulter):** Penalty $\delta_0 = S_D$. Reputation $R \leftarrow R - \delta_0$, status $\rightarrow \text{DEFAULTED}$, capacity frozen ($C = 0$).
   - **$k=1$ (Direct Sponsors):** Penalty $\delta_1 = \gamma \cdot W_{uv} \cdot S_D$ ($\gamma = 0.5$).
   - **$k=2$ (Transitive Ancestors):** Penalty $\delta_2 = \gamma^2 \cdot S_D = 0.25 \cdot S_D$.
   - **$k \ge 3$:** Cutoff ($\delta = 0$). Hard isolation stops systemic contagion.

### 6.4 Abuse safeguards
1. **Diminishing returns & chronological rank damping:** Later endorsements receive exponentially smaller weight ($\alpha_{uv} = 1/2^{r-1}$).
2. **Out-degree capacity conservation:** Total outgoing edge weights from a node are bounded by node capacity: $\sum_v W_{uv} \le C_u$.
3. **Per-path cycle absorption:** Traversal tracks visited nodes per path branch, terminating circular self-endorsement loops.
4. **Anchor grounding:** Unanchored components receive zero credibility regardless of internal endorsement density.
5. **Temporal velocity damping:** Rapid clusters of endorsements immediately prior to borrowing trigger provisional seasoning haircuts.

---

## 7. Affordability and scenario engine

### 7.1 Affordability formulation
For loan principal $P$, annual rate $A$, monthly rate $r = A / 12$, and tenure $n$ months:

$$\text{EMI} = \begin{cases} P \cdot \frac{r(1+r)^n}{(1+r)^n - 1} & \text{if } r > 0 \\ \frac{P}{n} & \text{if } r = 0 \end{cases}$$

$$\text{Disposable Income } D = I_{\text{net}} - E_{\text{essential}} - B_{\text{floor}}$$

$$\text{Monthly Surplus} = D - \text{Debt}_{\text{existing}} - \text{EMI}$$

$$\text{FOIR / ITI} = \frac{\text{EMI}}{I_{\text{net}}} \le 40\% \quad \Big| \quad \text{DTI} = \frac{\text{Debt}_{\text{existing}} + \text{EMI}}{I_{\text{net}}} \le 50\%$$

### 7.2 What-if scenario exploration
The system supports non-destructive scenario simulation:
- **Base scenario:** Verified income, documented obligations, requested loan terms.
- **Income shock scenario:** Configurable percentage drop in recurring revenue ($I \cdot (1 - \delta_I)$).
- **Emergency expense scenario:** One-off unexpected expense shock ($S_{\text{emergency}}$).
- **Restructuring scenario:** Parameter sweep over feasible $(P, T)$ pairs to restore positive surplus.

### 7.3 Platform treasury and transaction fee cut
To sustain decentralized protocol operations, every borrowing and repayment transaction incurs a transparent platform transaction fee cut:
- **Fee cut rate:** Configured by `PLATFORM_FEE_RATE` (default `Decimal("0.01")` / 1.0%).
- **Calculation:**
  $$\text{fee} = \text{round}(\text{amount} \times \text{PLATFORM\_FEE\_RATE}, 2)$$
  $$\text{net\_amount} = \text{amount} - \text{fee}$$
- **Disbursement:** The borrower receives `net_amount` while `fee` is routed to `PLATFORM_TREASURY`.
- **Repayment:** The gross repayment is split: `net_repay` reduces principal debt while `fee` is collected by `PLATFORM_TREASURY`.
- **Audit & Replay:** Every fee collection generates a `PLATFORM_FEE_COLLECTED` ledger event. Replaying the cryptographic ledger deterministically reconstructs treasury balances.
The system supports non-destructive scenario simulation:
- **Base scenario:** Verified income, documented obligations, requested loan terms.
- **Income shock scenario:** Configurable percentage drop in recurring revenue ($I \cdot (1 - \delta_I)$).
- **Emergency expense scenario:** One-off unexpected expense shock ($S_{\text{emergency}}$).
- **Restructuring scenario:** Parameter sweep over feasible $(P, T)$ pairs to restore positive surplus.

---

## 8. Presentation of combined assessment

The assessment separates orthogonal signals into an unblended, auditable structure:

```json
{
  "bureau": {
    "status": "AVAILABLE",
    "score": 640,
    "as_of": "2026-10-01"
  },
  "vouch": {
    "score": 74,
    "status": "ACTIVE",
    "confidence": "HIGH",
    "eligible_endorsements": 3
  },
  "affordability": {
    "disposable_income": "10750.00",
    "max_affordable_emi": "10750.00",
    "status": "SUFFICIENT"
  },
  "data_quality": "HIGH_CONFIDENCE_VERIFIED",
  "positive_factors": [
    {
      "code": "INCOME_STABLE",
      "text": "Verified recurring income documented via bank statement",
      "source": "EVID_BANK_01"
    }
  ],
  "risk_factors": [
    {
      "code": "OBLIGATION_SPIKE",
      "text": "Reported revolving credit utilization increased",
      "source": "EVID_BUREAU_PULL"
    }
  ],
  "missing_information": [],
  "review_flags": [],
  "algorithm_version": "veritrust-v2.0"
}
```

---

## 9. Explainable AI and audit boundaries

1. **Deterministic rules first:** Score calculations, constraint evaluations, and reason codes are derived strictly through versioned deterministic logic.
2. **AI boundary:** Generative LLMs may rephrase structured reason codes into natural language reports, but **must never** invent facts, fabricate financial numbers, assume sensitive medical diagnoses without verified evidence, or make lending decisions.
3. **Traceability:** Every decision records the active rule set, input evidence hashes, and algorithm version for compliance auditability.

---

## 10. API route specification

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/applications` | Create loan application; validate amount, interest rate, and tenure. |
| `POST` | `/api/v1/applications/{id}/evidence` | Register consented evidence metadata (retaining private documents off-chain). |
| `POST` | `/api/v1/endorsements` | Issue peer endorsement; enforce identity, consent, and exposure limits. |
| `GET` | `/api/v1/users/{id}/vouch-summary` | Return Vouch Score, confidence rating, and eligible endorsement count. |
| `POST` | `/api/v1/applications/{id}/assessments` | Run rule-based affordability, OR-Tools optimization, and stress tests. |
| `GET` | `/api/v1/assessments/{id}` | Retrieve multi-dimensional assessment, rule trace, and reason codes. |
| `POST` | `/api/v1/assessments/{id}/scenarios` | Run counterfactual simulation without mutating base assessment. |
| `POST` | `/api/v1/endorsements/{id}/dispute` | File formal borrower contestation or evidence dispute. |
| `GET` | `/api/v1/platform/treasury` | Return platform treasury fee collection statistics and cut rate. |
| `GET` | `/api/v1/transactions` | Query chronological transaction records with gross amount, fee, and net amount. |
| `POST` | `/api/v1/vouch-requests` | Create structured vouch request. |
| `POST` | `/api/v1/vouch-requests/{id}/respond` | Accept or reject pending vouch request. |
| `POST` | `/api/v1/applications/{id}/decision` | Record underwriter decision on loan application. |
| `POST` | `/api/v1/loans/{id}/default` | Trigger loan default and atomic 4-level slashing cascade. |
| `GET` | `/api/v1/loans` | List all active and historical loans. |
| `GET` | `/health` | Health check endpoint exposing no secrets or internal configuration. |

---

## 11. Security, privacy, and regulatory compliance

- **Authentication & RBAC:** Session-based authentication, password hashing with Argon2id/bcrypt, and object-level permissions.
- **Need-based data collection:** Only request and retain data strictly necessary for credit assessment.
- **Data storage isolation:** Sensitive financial records and personally identifiable documents are kept off-chain in private storage.
- **India regulatory compliance (RBI Digital Lending Directions 2025):** Enforces explicit borrower consent, transparent disclosures, need-based data collection, and formal borrower recourse channels.

---

## 12. Expanded core scenarios

### Scenario 1 — First-time borrower / no bureau score
- **Context:** A young adult or new entrepreneur applies for their first loan without credit bureau history.
- **System behavior:** Bureau status is explicitly recorded as `NO_FILE` or `UNAVAILABLE`. The system **never** assigns a zero or default penalty for absent credit history.
- **Assessment response:** Evaluates verified cash inflows, bank statements, and eligible peer endorsements. Computes affordability strictly from verified cash flows.
- **Explanation:** *"No usable bureau score was available. Verified income evidence is present. Eligible peer endorsements provide additional relational evidence but do not replace cash-flow affordability. Review missing living cost disclosures before underwriting."*

### Scenario 2 — Temporary financial shock / sudden score decline
- **Context:** An established borrower with consistent repayment history experiences an unexpected emergency expense (e.g., equipment breakdown or uninsured medical cost), temporarily driving up revolving credit utilization.
- **System behavior:** The bureau score drops, but the system does not automatically classify the borrower as unviable. It compares before/after cash flows and isolates the shock.
- **Assessment response:** Recomputes affordability with current obligations, flags reason code `UTILIZATION_SPIKE` and `INCOME_STABLE`, and evaluates whether income can service the restructured debt.
- **Explainability rule:** Requires verified documentation before labelling an expense as a medical or business emergency; otherwise uses neutral wording: *"Large recent outflow; purpose unverified."*

### Scenario 3 — Peer-to-peer vouching and reciprocal incentives
- **Context:** An established member of the community endorses an applicant, staking platform reputation.
- **System behavior:** The endorsement creates a directed edge with bounded capacity. If the borrower repays, the endorser earns reputation yield. If the borrower defaults, the endorser faces a proportionate slashing cascade.
- **Safeguard:** Disputed, ambiguous, or unverified defaults do not trigger automatic reputation slashing. Vouching is a reputation stake, not an unconditional financial guarantee.

### Scenario 4 — Dilution, influential endorsers, and endorsement rings
- **Context:** An applicant attempts to game the system through endorsement farming, mutual collusion rings, or soliciting high-reputation accounts.
- **Safeguards triggered:**
  - *Diminishing returns:* Saturation parameter $\tau$ caps total score contribution.
  - *Capacity conservation:* High-degree endorsers have their vouch weight divided equally across all outgoing edges ($\sum W \le C$).
  - *Cycle absorption:* Circular endorsement rings (e.g. $A \to B \to C \to A$) are truncated at first recurrence.
  - *Velocity detector:* Endorsement bursts immediately prior to application trigger provisional holding haircuts.

---

## 13. Cross-cutting case: explainability & evidence quality

Explainability is a first-class architectural component, providing:
1. **Explicit rule evaluation trace:** Every rule reports observed value, policy threshold, and Pass/Fail result.
2. **Primary evidence linkage:** Links every factual claim to a specific evidence ID and verification date.
3. **Graph path transparency:** Discloses the exact trust paths, intermediate hops, and weights connecting anchors to the borrower.
4. **Data quality separation:** Distinguishes data-quality flags (`VERIFIED`, `MISSING`, `STALE`, `DUPLICATED`, `DISPUTED`) from ability-to-pay economics.

---

## 14. Scenario-to-component mapping

| Scenario | Core modules | Test coverage |
|---|---|---|
| **No credit history** | `affordability.py`, `scoring.py`, `engine.py` | `test_affordability.py`, `test_credit.py` |
| **Temporary shock** | `counterfactual.py`, `stress_tester.py`, `explainer.py` | `test_counterfactual.py`, `test_stress_tester.py` |
| **Peer vouching** | `engine.py`, `lending.py`, `ledger.py` | `test_trust.py`, `test_vouch.py`, `test_lending.py` |
| **Dilution & ring attacks** | `attack_simulator.py`, `engine.py` | `test_attack_simulator.py`, `test_cycles.py` |
| **Explainability & recourse** | `audit_explorer.py`, `recourse.py`, `explainer.py` | `test_audit_explorer.py`, `test_recourse.py` |
| **Mathematical calibration** | `engine.py`, `scoring.py`, `models.py` | `test_mathematical_framework.py` |
| **Platform treasury & fee cut** | `lending.py`, `models.py`, `store.py` | `test_platform_fee.py` |

---

## 15. Acceptance criteria for the scenario module

1. The system **never** treats missing credit bureau history as a numeric zero or automatically as negative behavior.
2. A bureau score drop triggers an evidence-based review rather than an automatic causal rejection.
3. The assessment view keeps bureau score, Vouch Score, cash-flow affordability, and data quality clearly distinguishable.
4. Vouch Score and peer endorsements **cannot override** a clear affordability shortfall.
5. Every endorsement records actor, timestamp, status, and auditable contribution weight.
6. Unverified or disputed loan defaults do not trigger immediate reputation slashing.
7. Adding multiple low-quality, circular, or correlated endorsements has strictly bounded marginal impact.
8. Every credit explanation identifies supporting evidence, missing fields, policy limits, and calculation version.
9. Base assessments remain immutable when running counterfactual what-if scenarios.
10. All presentation materials clearly distinguish implemented features from future roadmap capabilities.

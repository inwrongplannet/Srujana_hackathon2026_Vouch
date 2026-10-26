# Technical Concept: Transitive Decentralized Credit Assessment

> This file captures the initial abstract design. It is the founding technical reference.
> Scope and complexity will be trimmed to what is demoable in the hackathon window.
> Decisions on what to include or defer go in `docs/DECISIONS.md`.

---

## Core Thesis

Replace opaque, centralised credit bureaus with an **open, transitive web-of-trust** built over a directed acyclic evaluation graph, combining:

- Zero-knowledge identity anchors
- Out-degree vouch conservation
- Cycle-absorbing score propagation
- Dual-axis uncertainty underwriting

---

## 1. Problem Alignment

### 1.1 The Bureau Blind Spot

Conventional credit scoring relies on historical, centrally gathered financial records. Three fundamental system failures result:

| Failure | Description |
|---|---|
| **Thin-File Trap** | Absence of records is conflated with bad credit. New-to-credit individuals and informal businesses receive default negative indicators, excluding them from low-cost formal credit. |
| **Black-Box Centralization** | Score determination is opaque, proprietary, and lagging (30-90 day bank reporting cycles) with zero user-verifiable factors. |
| **Fragile Single-Point Defaults** | Localised shocks (droughts, floods, micro-market collapses) trigger rigid score depreciation -- no distinction between moral hazard and structural force majeure. |

### 1.2 The Paradigm Shift

Creditworthiness is unbundled into two distinct, mathematically verifiable vectors:

| Vector | Symbol | Meaning |
|---|---|---|
| Character / Moral Hazard | `mu_trust` | Derived from a verifiable, staked web-of-trust graph. Reputable peers allocate non-transferable vouch capacity to endorse new actors. |
| Epistemic Uncertainty | `sigma2_epistem` | Explicitly quantified via information entropy. A borrower with no history starts with **high uncertainty**, not negative capacity. |

**Settlement Oracles:** Credibility is exclusively minted when debt contracts successfully settle, grounding social attestations in realised capital execution.

---

## 2. Mathematical & Algorithmic Specifications

### 2.1 Identity & Non-Invertible Nullifier

Enforce strict **1 Person = 1 Node** while preventing identity leaks:

```text
Identity Secret  sk  = Poseidon(Aadhaar_raw, Salt_user)
Node ID (Nullifier)  = Poseidon(sk, Protocol_Salt)
```

Verified via a zero-knowledge circuit (Circom/Groth16). The protocol salt ensures the Nullifier is platform-unique.

**Key property:** Defaulters cannot burn identity wallets to escape negative scores -- re-registering with the same Aadhaar/PAN regenerates the identical, slashed on-chain Nullifier.

### 2.2 Conserved Out-Degree Vouch Capacity

A node's reputation is treated as a **finite, distributable resource**.

- Let `R_u` = verified reputation score of node `u`.
- Available vouch capacity: `C_u = max(0, R_u)`
- Weight of edge from `u` to each target `v`: `W_uv = C_u / |Out(u)|`
- **Invariant (Out-Degree Conservation):** `sum(W_uv) <= C_u`
- Adding an additional vouch automatically dilutes **all** previous vouches emitted by `u`. Vouching carries a mathematical opportunity cost.

### 2.3 Hop Attenuation & Cycle Absorption

Let `X in (0,1)` be the geometric hop decay factor (default `X = 0.5`).

For every simple path `P = (v0, v1, ..., vk)` where `v0 in InstitutionalAnchors` and `vk = T`:

```text
Trust(P) = W_{v0,v1} * prod_{i=1}^{k-1} (W_{vi,vi+1} * X)
```

**Invariant (Cycle Absorption):** Let `VP` be the visited-set along the current path. If `v_{m+1} in VP`, then `Trust(P union {v_{m+1}}) = 0`.

A closed loop (e.g., `A -> B -> C -> A`) is absorbed on re-entry and produces zero incremental credibility.
Nodes with `R <= 0` have capacity `C = 0`, so zero-score clusters cannot fabricate reputation.

### 2.4 Damped Negative Cascade (Slashing Dynamics)

When borrower `B` defaults on a contract:

1. **Primary Slash:** `R_B <- R_B - delta0` (locks node capacity; state -> RESTRICTED)
2. **Immediate voucher** (`k = 1`) incurs: `delta_A = gamma * W_AB * delta0` where `gamma = 0.5`
3. **Transitive ancestor** (`k = 2`) incurs: `delta_ancestor = gamma^2 * delta0 ~= 0.0625 * delta0`
4. **Horizon cutoff** (`k >= 3`): `delta_k = 0`

Downstream defaults are mathematically isolated beyond 2 hops to prevent systemic social contagion.

### 2.5 Dual-Axis Assessment Matrix

The underwriting engine produces a 2D decision vector:

```text
Decision Vector = [mu_composite, sigma2_epistem]

mu_composite = alpha * R_graph + (1 - alpha) * S_cashflow
             * exp(beta * (N_settled + |In(T)|))

Score_final  = mu_composite - kappa * sigma
```

- `mu_composite`: Expected repayment capacity
- `sigma2_epistem`: Epistemic uncertainty band
- `Score_final`: Lower Confidence Bound (LCB) -- ensures thin-file borrowers can access micro-limits without exposing pools to unpriced variance

---

## 3. System Architecture

### 3.1 Client Tier

| Component | Role |
|---|---|
| Identity Onboarding | Collects ID locally, computes the client-side Poseidon nullifier, issues a zero-knowledge membership proof |
| Underwriter Dashboard | Visualises graph topology, multi-path trust flow, active exposure, dual-axis risk/uncertainty gauge |
| Borrower Portal | Shows available vouch capacity, active incoming attestations, credit ceiling progression |

### 3.2 Off-Chain Analytical Engine

| Component | Role |
|---|---|
| Graph Evaluation Service | Executes path traversals from root institutional anchors to target node; enforces cycle absorption and hop attenuation |
| Solvency Ingestion Engine | Interfaces with Account Aggregator (AA) rails or banking APIs to extract recurring cash-flow metrics, net debt burn, transaction volatility |
| Underwriting Synthesizer | Merges graph trust with cash-flow scoring; calculates epistemic uncertainty band; outputs interpretable decision payload |

### 3.3 Smart Contract Layer (EVM)

| Contract | Role |
|---|---|
| `IdentityRegistry` | Tracks Poseidon nullifiers; maps each identity to ACTIVE, RESTRICTED, or DEFAULTED; rejects duplicate registrations |
| `VouchHub` | Records directed attestations; enforces out-degree weight conservation; dynamically locks capacity during active loan periods; manages yield distribution or slash execution |
| `LoanEscrow` | Acts as settlement oracle; accepts loan principal deposits; manages repayment schedules; signals successful settlement or default events to VouchHub |

---

## 4. State Transitions & Lifecycle

### 4.1 Node Lifecycle

1. **Cold-Start Registration:** Node registers with a valid ZK-nullifier. `R = 0`, `C = 0`, `sigma2 = 1.0`.
2. **Sponsorship:** An active ancestor (`R > 0`) registers a directed vouch; a portion of the ancestor's capacity is locked.
3. **Capital Issuance:** Underwriter issues a micro-limit based on incoming path trust and high uncertainty buffer.
4. **Settlement:** Borrower completes repayment. Protocol mints intrinsic credibility to borrower, unlocks the sponsor's capacity, awards a small reputation yield to both.
5. **Vouching Authorization:** Once `R > 0`, the node gains outbound vouch capacity and can sponsor other community members.

### 4.2 Default Lifecycle

1. **Default Trigger:** Grace period expires on LoanEscrow without debt servicing.
2. **Primary Slash:** Target node credibility drops into negative territory. Status -> DEFAULTED. All outbound capacity frozen.
3. **Cascade Propagation:** Direct sponsor (`k = 1`) incurs 50% baseline penalty; transitive sponsor (`k = 2`) incurs 12.5% penalty; nodes at distance `k >= 3` remain untouched.
4. **Circuit Breaker Check:** If localised default covariance exceeds a cluster threshold theta (e.g., severe environmental or regional shock), automated slashes are paused for debt restructuring.

---

## 5. Security Model

| Threat Vector | Attack Scenario | Protocol Defense |
|---|---|---|
| Dictionary / Rainbow Inversion | Adversary attempts to reverse-engineer Aadhaar/PAN from public ledger hashes | Client-side Poseidon ZK-Nullifier + private high-entropy salt prevents brute-force preimage attacks |
| Wash Vouching / Collusion Rings | Sybil cluster cross-vouches to mutually inflate scores | Zero credibility -> zero allocatable capacity; closed cycles absorbed with zero incremental weight |
| Identity Churn (Wallet Burning) | Defaulted borrower discards private keys and registers a fresh wallet | Nullifiers are strictly deterministic; re-registering resolves to the identical slashed identity state |
| Endorsement Dilution Fraud | Reputable node sells unlimited vouches off-chain for bribes | Out-degree conservation strictly splits available trust; each additional vouch dilutes all existing edges |
| Systemic Contagion | A localised failure triggers runaway cascade across community | Hard 2-hop horizon cutoff isolates shocks; cluster default covariance triggers automatic circuit breakers |

---

## 6. Key Differentiators vs Legacy Bureaus

| Dimension | Legacy Bureau | This System |
|---|---|---|
| Cold-start capability | Instant rejection for thin-file borrowers | Community-backed bootstrapping from Day 1 |
| Auditability | Opaque proprietary scorecard | Every score point maps to a deterministic mathematical graph path |
| Incentive alignment | Bureau profit vs borrower privacy | Sponsors risk their own social reputation capacity -- organic peer-level underwriting |
| Uncertainty handling | Absence of data = negative score | Absence of data = high uncertainty band, not negative capacity |
| Shock resilience | Rigid depreciation regardless of cause | Circuit breaker distinguishes moral hazard from force majeure |

---

## 7. Hackathon Scope Notes

> What is described above is the full system vision. For the 24-48h demo, the following reductions apply (to be finalised in `docs/DECISIONS.md`):

- **ZK circuits:** Replace with mock/simulated nullifier generation; the math is real, the crypto proof is stubbed.
- **Smart contracts:** Simulate on-chain state with an in-memory or SQLite store; no live EVM deployment required for judging.
- **AA rails:** Use the seeded cash-flow figures in `backend/src/veritrust/store.py` (and the frontend mocks) instead of live Account Aggregator API calls.
- **Graph size:** 20-50 seeded nodes is sufficient to demonstrate multi-hop trust propagation and cycle absorption.
- **Underwriter UI:** A single dashboard showing the dual-axis score, graph visualisation, and what-if sliders is the minimum demoable surface.

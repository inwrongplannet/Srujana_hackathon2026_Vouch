# VeriTrust — Complete End-to-End System Flow & Architecture

This document provides a clear, comprehensive, and visual walkthrough of the **VeriTrust Web-of-Trust Credit Engine & Reputation Ledger**. It explains the real-world problem being solved, the mathematical foundations, and the exact step-by-step lifecycle of a borrower in the system.

---

## 1. Executive Summary & The Problem

### The Traditional Credit Bureau Failure: The "Thin-File Trap"
Traditional credit bureaus (like CIBIL or Experian) rely entirely on past formal repayment history. 
* If a street vendor, gig worker, or rural farmer has never taken a formal bank loan, they are categorized as a **"thin-file"** or **"no-file"** borrower.
* Bureaus assign them a zero/negative score or reject them outright.
* **The fundamental mistake:** Conflating **lack of information (epistemic uncertainty $\sigma^2 \approx 1.0$)** with **bad credit risk ($R \approx -1.0$)**.

### The VeriTrust Solution
VeriTrust breaks the thin-file trap through **Dual-Axis Underwriting** backed by a decentralized **Web-of-Trust Graph** and an **Immutable Cryptographic Ledger**:
1. **Transitive Social Capital:** Local community leaders, cooperatives, or microfinance institutions ("Anchors") endorse trustworthy members. Trust propagates mathematically across network paths.
2. **Dual-Axis Underwriting:** Evaluates **Repayment Capacity ($\mu$)** on one axis and **Data Uncertainty ($\sigma^2$)** on the other axis, computing an eligible credit limit using a conservative **Lower Confidence Bound (LCB)**.
3. **Skin-in-the-Game Incentives:** Endorsing someone risks slashing your own reputation if they default, but yields a reputation reward when they repay.
4. **Verifiable Audit Ledger:** Every vouch, loan, repayment, and penalty is an immutable event in a cryptographically chained ledger with verifiable evidence.

---

## 2. High-Level Architecture Flow

The entire VeriTrust protocol is structured into four interacting layers:

```mermaid
flowchart TD
    subgraph Data["1. Identity & Signals Layer"]
        U["User Registration<br/>(Anchor or Community Member)"]
        FF["Cash-Flow Signals<br/>(Income, Obligations, Stability)"]
        EV["Verifiable Evidence<br/>(DigiLocker, Bank Stmts, Receipts)"]
    end

    subgraph Trust["2. Web-of-Trust Graph Engine"]
        CAP["Out-Degree Capacity Conservation<br/>C_u = max(0, R_u)"]
        VOUCH["Directed Endorsements (W_uv)<br/>W_uv = C_u / |Out(u)|"]
        DIL["Atomic Sibling Dilution"]
    end

    subgraph Scoring["3. Dual-Axis Underwriting Engine"]
        PROP["Path Enumeration & Hop Decay<br/>(lambda = 0.5, Per-Path Cycle Absorption)"]
        DUAL["LCB Score Calculation<br/>Score = mu - kappa * sqrt(sigma2)"]
        LIMIT["Approved Credit Limit (paise / INR)"]
    end

    subgraph Execution["4. Lending, Platform Treasury & Cryptographic Ledger"]
        LOAN["Loan Contracts (Disbursement / Repayment)"]
        TREASURY["Platform Treasury & Surcharge<br/>(1.0% Fee Cut on Borrow & Repay)"]
        SLASH["4-Level Atomic Slashing Cascade"]
        LEDGER["Append-Only Event Store<br/>(SQLite + JSONL SHA-256 Hash Chain)"]
        REPLAY["Disaster Recovery & State Replay"]
    end

    Data --> Trust
    Trust --> Scoring
    Scoring --> Execution
    Execution --> TREASURY
    Execution -.->|"Repayment Boost (+R) or Slashing (-R)"| Trust
    Execution -->|"Audit Trail & Fee Logs"| LEDGER
    LEDGER -.->|"State Reconstruction"| REPLAY
```

---

## 3. Mathematical Foundations (Made Simple)

### Invariant 1: Out-Degree Capacity Conservation Law
In VeriTrust, you cannot manufacture trust out of thin air. A user's total ability to endorse others is strictly bounded by their own reputation score:

$$\text{Capacity } C_u = \max(0, R_u)$$

When user $u$ vouches for $k$ different peers, their capacity is divided equally among them:

$$W_{uv} = \frac{C_u}{|\text{Out}(u)|} \quad \text{such that} \quad \sum_{v \in \text{Out}(u)} W_{uv} \le C_u$$

```mermaid
flowchart LR
    subgraph Single["Scenario A: Alice vouches for 1 peer"]
        A1["Alice (Capacity C = 10.0)"] -->|"Weight W = 10.0"| B1["Bob"]
    end

    subgraph Multiple["Scenario B: Alice vouches for 2 peers (Atomic Dilution)"]
        A2["Alice (Capacity C = 10.0)"] -->|"Weight W = 5.0"| B2["Bob"]
        A2 -->|"Weight W = 5.0"| C2["Charlie"]
    end
```

> [!NOTE]
> **Why this matters:** A user with $10$ reputation cannot vouch for $100$ people and give each of them $10$ trust. Vouching for more people automatically dilutes each endorsement, preventing spam and Sybil collusion rings.

---

### Invariant 2: Geometric Hop Attenuation & Cycle Absorption
When trust travels along a chain from an institutional anchor to a borrower, it attenuates with distance:

$$\text{Trust}(P) = W_{v_0, v_1} \times \prod_{i=1}^{k-1} (W_{v_i, v_{i+1}} \times 0.5)$$

* **First Hop:** Full strength ($W_{v_0, v_1}$). The Anchor directly trusts Alice.
* **Subsequent Hops:** Attenuated by geometric decay factor $\lambda = 0.5$. Alice trusts Bob, Bob trusts Dave.
* **Per-Path Cycle Absorption:** If a path loops back into an already-visited node (e.g. $A \rightarrow B \rightarrow C \rightarrow A$), that specific cycle terminates with **$0$ trust**. However, other independent paths to the borrower remain valid.

```mermaid
flowchart LR
    ANCHOR["Institutional Anchor<br/>(Seed Bank)"] -->|"Direct Hop: W = 20.0"| ALICE["Alice<br/>(Community Leader)"]
    ALICE -->|"Hop 2: W = 10.0 * 0.5 = 5.0"| BOB["Bob<br/>(Shop Owner)"]
    BOB -->|"Hop 3: W = 5.0 * 0.5 = 2.5"| CHARLIE["Charlie<br/>(Farmer)"]

    style ANCHOR fill:#e1f5fe,stroke:#0288d1
    style CHARLIE fill:#e8f5e9,stroke:#388e3c
```

---

### Invariant 3: Dual-Axis Underwriting & Lower Confidence Bound (LCB)

Instead of a single scalar credit score, VeriTrust evaluates two distinct dimensions:

```mermaid
flowchart TD
    subgraph Axis1["Axis 1: Expected Capacity (mu)"]
        RG["Graph Trust Score (R_graph)"]
        SC["Cash-Flow Repayment Score (S_cashflow)"]
        BOOST["Settled Loans & Endorsement Count"]
        RG & SC --> BLEND["Blended Capacity: 0.6 * R + 0.4 * S"]
        BLEND & BOOST --> MU["mu_composite = Blended * exp(0.1 * (N_settled + |In(T)|))"]
    end

    subgraph Axis2["Axis 2: Epistemic Uncertainty (sigma2)"]
        NDATA["Transaction Data Volume"]
        COMP["Data Completeness (0.0 to 1.0)"]
        NDATA & COMP --> SIGMA["sigma2 = 1 / (1 + N_data * completeness)"]
    end

    subgraph Decision["Decision: Lower Confidence Bound (LCB)"]
        MU & SIGMA --> LCB["Score_final = mu - kappa * sqrt(sigma2)"]
        LCB --> LIMIT["Credit Limit = max(0, Score_final * 10,000 INR)"]
    end
```

#### Why LCB Protects Borrowers and Lenders
* **Thin-File / New User:** High uncertainty ($\sigma^2 = 1.0$), but **not** negative credit. They start with a modest, safe micro-limit.
* **Reputable, Well-Documented User:** High $\mu$, low uncertainty ($\sigma^2 \rightarrow 0$). The penalty vanishes and their full borrowing limit is unlocked.

---

## 4. End-to-End Walkthrough: The Lifecycle of a Borrower

Here is the exact step-by-step journey through the system from registration to borrowing, settlement, and default handling.

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Alice (Voucher)
    actor Bob as Bob (Borrower)
    participant Engine as TrustEngine
    participant Scorer as CreditScorer
    participant Lending as LendingService
    participant Ledger as ReputationLedger (SQLite + JSONL)

    Note over Alice,Bob: Step 1: Vouching & Capacity Conservation
    Alice->>Engine: vouch("ALICE", "BOB")
    Engine->>Ledger: append_event("VOUCH_CREATED", actor="ALICE", subject="BOB")
    Ledger-->>Engine: Event Committed (SHA-256 Chained)
    Engine->>Engine: Conserve capacity & re-weight all siblings
    Engine-->>Alice: Vouch active (Assigned Weight: 5.0)

    Note over Bob,Lending: Step 2: Underwriting, Borrowing & Fee Cut
    Bob->>Lending: borrow("BOB", amount=25000 INR)
    Lending->>Scorer: assess_credit("BOB")
    Scorer->>Engine: enumerate_paths(from anchors to "BOB")
    Scorer-->>Lending: Approved Limit = 32,150 INR (Score: 3.215)
    Lending->>Lending: Calculate 1.0% platform fee cut: fee = 250 INR, net = 24,750 INR
    Lending->>Ledger: append_event("LOAN_DISBURSED", loan_id="LN_00001", amount=25000)
    Lending->>Ledger: append_event("PLATFORM_FEE_COLLECTED", fee=250, treasury="PLATFORM_TREASURY")
    Ledger-->>Lending: Events Committed
    Lending-->>Bob: Loan LN_00001 Disbursed (Net: 24,750 INR, Fee: 250 INR)

    alt Scenario A: Happy Path (Repayment, Fee Cut & Yield Minting)
        Bob->>Lending: repay("LN_00001", amount=25000)
        Lending->>Lending: Calculate 1.0% platform fee cut: fee = 250 INR, net_repay = 24,750 INR
        Lending->>Ledger: append_event("PLATFORM_FEE_COLLECTED", fee=250, treasury="PLATFORM_TREASURY")
        Lending->>Ledger: append_event("LOAN_REPAID", net_repaid=24750, balance=0)
        Lending->>Ledger: append_event("REPUTATION_MINTED", subject="BOB", delta=+2.0)
        Lending->>Ledger: append_event("REPUTATION_MINTED", subject="ALICE", delta=+1.0)
        Lending->>Engine: Update reputation: Bob +2.0, Alice +1.0
        Lending-->>Bob: Loan Settled! Borrower boosted (+2.0), Sponsor rewarded (+1.0), Fee recorded (250 INR)
    else Scenario B: Unhappy Path (Default & Slashing Cascade)
        Lending->>Lending: default_loan("LN_00001")
        Lending->>Ledger: append_event("LOAN_DEFAULTED", subject="BOB")
        Lending->>Ledger: append_event("REPUTATION_SLASHED", subject="BOB", level=0, delta=-10.0)
        Lending->>Ledger: append_event("REPUTATION_SLASHED", subject="ALICE", level=1, delta=-2.5)
        Lending->>Engine: Freeze Bob (Capacity=0, DEFAULTED), Slash Alice (delta=2.5)
        Lending-->>Bob: Node DEFAULTED. 4-level slashing cascade executed.
    end
```

---

## 5. Slashing Cascade on Default: Contagion Control

When a borrower defaults, VeriTrust executes an **Atomic 4-Level Damped Slashing Cascade** to penalize reckless endorsements while strictly containing systemic contagion:

```mermaid
flowchart TD
    subgraph K0["k = 0: Defaulter Node (B)"]
        D0["Defaulter Reputation: R_B <- R_B - delta_0 (e.g. -10.0)<br/>Status -> DEFAULTED<br/>Capacity -> C = 0 (Frozen)<br/>All outbound edges -> W = 0"]
    end

    subgraph K1["k = 1: Direct Sponsors (A vouched for B)"]
        D1["Proportional Penalty: delta_1 = 0.5 * W_AB * delta_0<br/>Damped by endorsement weight W_AB<br/>If R_A < 0 -> Status: RESTRICTED"]
    end

    subgraph K2["k = 2: Transitive Ancestors (Z vouched for A)"]
        D2["Quadratic Damped Penalty: delta_2 = (0.5)^2 * delta_0 = 0.25 * delta_0<br/>If R_Z < 0 -> Status: RESTRICTED"]
    end

    subgraph K3["k >= 3: Isolation Boundary (Cutoff)"]
        D3["Hard Boundary: Penalty delta = 0.0<br/>Contagion stops completely. System is immune."]
    end

    K0 ==>|"Penalizes Direct Sponsors"| K1
    K1 ==>|"Penalizes Ancestors"| K2
    K2 ==>|"Boundary Cutoff"| K3

    style K0 fill:#ffebee,stroke:#c62828
    style K1 fill:#fff3e0,stroke:#ef6c00
    style K2 fill:#fffde7,stroke:#fbc02d
    style K3 fill:#e8f5e9,stroke:#2e7d32
```

---

## 6. The Cryptographic Reputation Ledger & Audit Trail

### Events as the Source of Truth
State mutations do not happen haphazardly. The ledger is the **sole source of truth**:
1. When any mutation is triggered (e.g., `borrow`, `repay`, `vouch`), an event is appended to the ledger **first**.
2. If the ledger insertion fails (e.g., duplicate `event_id`), the in-memory graph is never touched.
3. Every event is cryptographically linked to the previous event hash, forming an unbroken SHA-256 blockchain-style hash chain:

```mermaid
flowchart LR
    G["GENESIS HASH<br/>0000000000000000..."] --> E1["Sequence 1<br/>USER_REGISTERED<br/>Actor: SYSTEM_ANCHOR<br/>Subject: ANCHOR_BANK<br/>Hash: e2e6179a..."]
    E1 --> E2["Sequence 2<br/>USER_REGISTERED<br/>Actor: ALICE<br/>Subject: ALICE<br/>Hash: c33c454c..."]
    E2 --> E3["Sequence 3<br/>VOUCH_CREATED<br/>Actor: ANCHOR_BANK<br/>Subject: ALICE<br/>Hash: fca36ce8..."]
    E3 --> E4["Sequence 4<br/>LOAN_DISBURSED<br/>Actor: BOB<br/>Subject: BOB<br/>Hash: 217f721c..."]
    E4 --> E5["Sequence 5<br/>REPUTATION_MINTED<br/>Actor: ORACLE<br/>Subject: BOB (Delta: +2.0)<br/>Hash: affc9b80..."]
```

### Audit & Disaster Recovery Commands
* **Audit (`python main.py audit`):** Verifies the mathematical integrity of every SHA-256 hash link from Genesis to Head. Detects any row tampering or broken links instantly.
* **History (`python main.py history [user_id]`):** Shows the full chronological audit trail explaining *why* someone's score changed and attaching verifiable evidence.
* **Replay (`python main.py replay --restore`):** If the database or state file is corrupted or lost, replaying all raw events from Genesis deterministically reconstructs the complete graph, reputation scores, edge weights, and loan statuses.

---

## 7. Command Reference & Hands-on Verification

You can explore and verify this entire flow using the CLI:

```bash
# 1. Inspect initial nodes and network
python main.py users
python main.py graph

# 2. Check a user's standing and credit limit
python main.py check BOB
python main.py whoami

# 3. Log in, borrow within limit, and view active loans
python main.py login BOB
python main.py borrow 5000
python main.py loans --mine

# 4. Repay the loan to trigger reputation yields
python main.py repay LN_00001 5000

# 5. Inspect the immutable audit ledger for Bob and Alice
python main.py history BOB
python main.py history ALICE

# 6. Inspect platform treasury fee collection
python main.py treasury

# 7. Audit cryptographic integrity of the hash chain
python main.py audit

# 8. Run loan optimization & stress testing
python main.py optimize 15000

# 9. Test disaster recovery state reconstruction
python main.py replay --restore
```

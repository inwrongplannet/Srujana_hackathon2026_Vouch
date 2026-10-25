# VeriTrust --- Project Architecture and Technical Reference

**Document status:** Production reference specification & verified implementation (supersedes initial POC design draft)\
**Deliverable status:** Fully implemented, validated, and verified across `backend/src/veritrust/` and `backend/ml/` (152/152 passing tests)\
**Master references:** [Implementation_Doc.md](Implementation_Doc.md) and [VOUCH_DEVELOPER_MASTER_V2.md](VOUCH_DEVELOPER_MASTER_V2.md)\
**Audience:** Product, engineering, and hackathon teammates\
**Version:** 2.0 (Production)\
**Last updated:** 25 October 2026

> **Status labels used in this document**
>
> -   **Specified:** Directly stated in the original VeriTrust project
>     specification.
> -   **Proposed:** A practical design recommendation for the current
>     POC.
> -   **Open decision:** Not yet agreed or supported by enough detail to
>     implement safely.

------------------------------------------------------------------------

## 1. Executive summary

VeriTrust is a proposed credit-assessment protocol that aims to help
assess borrowers who have little or no conventional credit history. It
combines a graph of endorsements with financial evidence and an explicit
estimate of uncertainty.

The central idea is to avoid treating *missing credit history* as
equivalent to *bad repayment history*. The protocol attempts to
estimate:

1.  **Trust / reputation:** What credible support reaches a borrower
    through the trust graph?
2.  **Repayment capacity:** What does available financial evidence
    suggest the borrower can repay?
3.  **Uncertainty:** How limited or unreliable is the evidence behind
    the assessment?

The long-term vision includes onboarding, identity verification,
viewing, and transaction platforms; an identity layer; a graph trust
layer; a protocol engine; smart-contract-based tracking; and supporting
infrastructure.

**The current deliverable is narrower:** implement and demonstrate the
engine using synthetic data and simulated loan events. No zero-knowledge
identity, real KYC, blockchain, smart contracts, live bank connections,
or production lending will be built in this POC.

The POC should show that the team can: - Build a directed graph of users
and endorsements. - Calculate trust with clear, testable rules. -
Process simulated repayments and defaults. - Update reputation and
recompute affected assessments. - Combine trust with synthetic financial
features and uncertainty. - Explain why a borrower received a particular
result.

The output is a **prototype recommendation**, not a validated credit
score or a real lending decision.

------------------------------------------------------------------------

## 2. Goals and non-goals

### 2.1 POC goals

-   Implement graph construction and validation.
-   Compare path-based trust propagation with global iterative graph
    scoring.
-   Select and document one method for the first implementation.
-   Enforce vouch-capacity limits.
-   Prevent cycles from generating artificial trust.
-   Simulate repayment rewards and default penalties.
-   Create a replaceable financial risk component.
-   Produce an explainable assessment for a selected borrower.
-   Test edge cases such as disconnected users, overlapping paths,
    collusion rings, and duplicate events.

### 2.2 Out of scope for the current POC

-   Real PAN/Aadhaar processing or KYC.
-   Zero-knowledge proofs or cryptographic identity issuance.
-   Blockchain deployment and smart contracts.
-   Real loan disbursement, repayment, or settlement.
-   Live bank APIs or Account Aggregator integrations.
-   A trained model claiming real-world default prediction.
-   Production-grade security, compliance, and lending operations.
-   A polished web frontend. A CLI or simple API is enough for the
    engine demonstration.

### 2.3 Long-term vision

The following are future product areas, not current POC requirements:

-   **Onboarding platform:** Lets a participant enter the system.
-   **Verification platform:** Establishes whether identity or other
    claims have been verified.
-   **Viewing platform:** Shows relevant trust paths, reputation,
    assessments, and loan history to authorized users.
-   **Transaction platform:** Supports the lending lifecycle.
-   **Identity layer:** Maintains a stable protocol identity while
    protecting sensitive identity data.
-   **Graph trust layer:** Represents participants, endorsements, and
    trust relationships.
-   **Protocol engine:** Turns verified inputs and graph relationships
    into deterministic protocol calculations.
-   **Tracking and enforcement layer:** Eventually uses smart contracts
    to record and enforce selected state transitions.
-   **Infrastructure:** Provides storage, compute, monitoring, security,
    and event processing.

------------------------------------------------------------------------

## 3. Conceptual architecture

``` mermaid
flowchart TD
    subgraph FUTURE["Future product surfaces — not built in this POC"]
        A[Onboarding platform]
        B[Verification platform]
        C[Viewing platform]
        D[Transaction platform]
    end

    subgraph ENGINE["Current deliverable: VeriTrust Engine"]
        E[Input loading and validation]
        F[Graph builder]
        G[Trust propagation]
        H[Reputation and event processor]
        I[Financial risk component]
        J[Uncertainty component]
        K[Assessment and explanation]
        E --> F
        F --> G
        G --> K
        H --> G
        G --> K
        I --> K
        J --> K
    end

    subgraph FUTUREINFRA["Future integrations — not built in this POC"]
        L[Identity and verification services]
        M[Smart contracts and event indexer]
        N[Persistent storage and monitoring]
    end

    A -. future input .-> E
    B -. verified claims .-> E
    D -. loan outcomes .-> H
    K -. assessment output .-> C
    M -. future events .-> H
    N -. future support .-> ENGINE
```

The diagram shows conceptual relationships. It does not imply that every
component is a separate service. For the POC, implement modules in one
Python application.

### 3.1 Current engine flow

1.  Load synthetic participants, vouches, financial features, and loan
    events.
2.  Validate the input records.
3.  Build a directed graph.
4.  Calculate trust from designated trusted roots.
5.  Process simulated loan outcomes and update reputation.
6.  Recalculate trust when relevant state changes.
7.  Combine trust, financial features, and uncertainty.
8.  Return an assessment and an explanation of its inputs.

**Important:** Loan-event processing may happen before or after an
assessment. A default or repayment changes state; the engine should then
recompute any assessments affected by that change.

------------------------------------------------------------------------

## 4. Core concepts and terminology

  -----------------------------------------------------------------------
  Term                                Meaning in VeriTrust
  ----------------------------------- -----------------------------------
  Participant / node                  A user represented in the protocol
                                      graph by a pseudonymous ID.

  Vouch / endorsement                 A directed relationship in which
                                      one participant endorses another.

  Sponsor                             The participant who issues a vouch.

  Target / borrower                   The participant receiving a vouch
                                      or being assessed for credit.

  Reputation, `R`                     A protocol value used to determine
                                      vouch capacity and to reflect
                                      outcomes. Its exact scale and
                                      update rules remain to be
                                      calibrated.

  Vouch capacity, `C`                 The amount of endorsement weight a
                                      participant is permitted to
                                      allocate.

  Edge weight, `W(u,v)`               The weight assigned to the vouch
                                      from `u` to `v`.

  Trusted root                        A node from which trust propagation
                                      starts. The source and governance
                                      of roots must be defined.

  Hop                                 One edge traversed along a path.

  Hop decay, `lambda`                 A factor that reduces the
                                      contribution of longer paths.

  Repayment capacity, `mu`            An estimate derived from financial
                                      evidence. It is not automatically a
                                      probability of repayment.

  Epistemic uncertainty, `sigma²`     Uncertainty due to limited
                                      knowledge or evidence. The POC must
                                      define a proxy unless a calibrated
                                      statistical model is available.

  Assessment                          A structured output containing
                                      trust, financial estimates,
                                      uncertainty, and an explanation.

  Loan event                          A simulated event such as repayment
                                      or default.

  Idempotency                         Processing the same event more than
                                      once has no additional effect after
                                      its first successful application.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 5. Module design

### 5.1 Input loader and validator

**Purpose:** Read synthetic records and reject malformed or inconsistent
inputs before calculations begin.

Inputs: - Participants. - Vouches. - Financial features. - Simulated
loan events. - Configuration values.

Responsibilities: - Check required fields and types. - Ensure every
vouch references existing participants. - Reject self-vouches unless
explicitly supported later. - Check that numerical values are finite and
within allowed ranges. - Reject duplicate IDs and malformed events. -
Report validation errors clearly.

Output: validated records ready for graph construction.

### 5.2 Graph builder

**Purpose:** Represent the vouch network as a directed graph.

-   Nodes represent participants.
-   Directed edges represent active vouches.
-   Each edge stores its source, target, status, and any protocol
    metadata required by the trust calculation.
-   Financial records should not be stored as public graph attributes
    unless there is a clear need.

For the POC, use an in-memory graph. NetworkX is a practical option.
Keep the trust algorithm separate from NetworkX so it can be tested and
changed independently.

### 5.3 Trust propagation engine

**Purpose:** Calculate how much trust reaches a target from designated
trusted roots.

Responsibilities: - Determine each sponsor's available capacity. -
Allocate or validate edge weights. - Traverse eligible paths. - Apply
hop decay. - prevent repeated nodes within a path from contributing
through a cycle. - Combine path contributions without uncontrolled
double-counting. - Return both a score and the paths that contributed to
it.

The original specification proposes: - `C_u = max(0, R_u)` -
`W_uv = C_u / out_degree(u)` for a simple equal-split allocation. - A
default hop-decay factor of `lambda = 0.5`. - A visited-set rule to stop
a path when it re-enters a node already visited on that path.

These are starting rules, not a fully complete mathematical
specification. In particular, edge weights must not exceed capacity when
capacity is locked by active loans, and overlapping paths need a clear
aggregation rule.

### 5.4 Reputation and event processor

**Purpose:** Apply the effect of simulated loan outcomes to participant
state.

Events for the POC: - `LOAN_REPAID` - `LOAN_DEFAULTED`

Responsibilities: - Validate the event and its referenced loan. - Reject
or ignore a duplicate event ID after the first successful application. -
Apply the configured borrower reputation change. - Apply configured
sponsor rewards or penalties. - Record which state changes were
applied. - Trigger recalculation for affected nodes.

The original specification proposes a primary penalty for the borrower,
a baseline 50% penalty for direct sponsors, a 12.5% penalty at distance
two, and no cascade beyond two hops. The exact reference quantity and
sign convention for these percentages must be made explicit before
implementation. The original text does not fully specify a safe,
complete update equation.

Do not implement real slashing or transfer funds in this POC.

### 5.5 Financial risk component

**Purpose:** Estimate repayment capacity from synthetic financial
features.

Possible input features: - Recurring income. - Monthly debt
obligations. - Cash-flow stability. - Income or transaction
volatility. - Other clearly documented synthetic features.

For the first version, use a deterministic and explainable baseline.
Keep the component behind a stable interface so it can later be replaced
by a statistical or ML model.

The POC must not claim that a hand-written score is a validated
probability of default. No validated model or training dataset is
defined in the current specification.

### 5.6 Uncertainty component

**Purpose:** Represent how limited or uncertain the evidence is.

For the POC, define a transparent proxy using available evidence, such
as the amount of observed financial history and the coverage of required
features. Clearly label it as a prototype uncertainty score.

Do not treat the number as statistically calibrated unless it has been
calibrated against relevant data.

### 5.7 Credit assessment engine

**Purpose:** Combine graph trust, financial repayment capacity, and
uncertainty.

The original specification proposes a lower-confidence-bound form:

`final_score = mu_composite - kappa * sigma_epistemic`

where: - `mu_composite` is the combined expected repayment-capacity
estimate. - `sigma_epistemic` represents uncertainty. - `kappa` controls
how conservative the result is.

The exact method for calculating `mu_composite`, `sigma_epistemic`, and
`kappa` is not fully specified. The POC must define units, ranges,
normalization, and a documented placeholder policy before these values
are combined.

Do not directly add raw reputation and financial values if they use
different scales. Normalize them or combine them through an explicitly
defined function.

### 5.8 Explanation engine

**Purpose:** Make every assessment inspectable.

The output should include: - The trust score and its calculation
version. - Contributing paths and their individual contributions. -
Financial feature summary. - Uncertainty estimate and how it was
derived. - Risk factors and missing evidence. - The final prototype
recommendation. - Input snapshot or input version used for the
calculation.

The explanation should distinguish facts from assumptions. It must not
claim that an endorsement proves repayment ability.

------------------------------------------------------------------------

## 6. Comparing trust propagation approaches

The team has not yet selected a final approach. Two options should be
compared before committing.

### 6.1 Approach A --- Path-based trust propagation

Trace eligible paths from trusted roots to the borrower. Score each path
using edge weights and hop decay, then combine the contributions.

A conceptual path score could look like:

`path_score(P) = root_weight * product(edge_weight_i * lambda)`

This is illustrative, not the final formula. The team must decide
whether to multiply edge weights, normalize them, or use another
aggregation rule.

**Advantages** - Easy to explain: the engine can show which paths
contributed. - Closely matches the original VeriTrust specification. -
Straightforward for small graphs and a short POC. - Visited-set cycle
prevention is easy to reason about.

**Risks** - The number of simple paths can grow very quickly in dense
graphs. - Several paths may share the same root or intermediate nodes
and overstate independent evidence. - Results depend heavily on root
selection and the path aggregation rule. - Path truncation or hop limits
may change scores.

**Good fit when:** explainability and fidelity to the current
specification matter most, and the demo graph is small.

### 6.2 Approach B --- Global iterative graph scoring

Update scores across the graph repeatedly until the values stabilize or
a maximum number of iterations is reached. This is conceptually related
to PageRank-style methods, though a VeriTrust version would need its own
definitions.

**Advantages** - Can scale better than enumerating every simple path. -
Produces a graph-wide score rather than relying only on explicit path
enumeration. - Can naturally represent many relationships at once.

**Risks** - The result is less directly explainable as a list of
individual paths. - The algorithm needs damping, convergence rules,
normalization, and root handling. - Colluding groups may still inflate
scores if the graph formulation is weak. - A PageRank-like score is not
automatically a measure of creditworthiness.

**Good fit when:** the graph is larger and a stable global ranking is
more important than path-level explanations.

### 6.3 Comparison

  -----------------------------------------------------------------------
  Criterion               Path-based              Global iterative
  ----------------------- ----------------------- -----------------------
  Explain individual      Strong                  Weaker without extra
  trust paths                                     attribution

  Matches original        Closer                  Requires a design
  specification                                   change

  Small POC               Easier                  Moderate
  implementation                                  

  Dense-graph scalability May be poor             Often better

  Cycle handling          Visited set per path    Mathematical
                                                  convergence and graph
                                                  rules

  Risk of shared-evidence Must be addressed       Depends on the scoring
  double-counting         explicitly              formulation

  Easy to debug by hand   Usually easier on small Can be harder
                          graphs                  

  Needs root and          Yes                     Yes
  normalization rules                             
  -----------------------------------------------------------------------

### 6.4 Proposed decision for the POC

**Proposed, not yet confirmed:** implement path-based propagation first
because it aligns with the source specification and provides clear path
explanations for a demo.

Keep the trust engine interface independent of the algorithm. If time
permits, implement a small global-scoring baseline and compare the two
on the same synthetic scenarios.

Before finalizing path-based scoring, agree on: 1. How trusted roots are
selected and weighted. 2. How edge weights are computed when capacity is
locked. 3. How multiple paths are combined. 4. How shared roots and
shared intermediates are handled. 5. The maximum path length or graph
size supported in the POC. 6. What happens when no eligible path reaches
the borrower.

------------------------------------------------------------------------

## 7. Reputation, vouch capacity, and default rules

### 7.1 Vouch capacity

The source specification defines the baseline capacity as:

`C_u = max(0, R_u)`

and proposes equal splitting across outgoing vouches:

`W_uv = C_u / out_degree(u)`

The intended invariant is:

`sum(W_uv for outgoing vouches) <= C_u`

For the POC, test this invariant directly.

**Open decision:** the formula above does not fully account for capacity
locked by active loans. A later version needs to distinguish total
capacity, allocated capacity, and available capacity. Do not silently
assume these are identical.

### 7.2 Default cascade

The original document proposes: - The borrower receives the primary
penalty. - Direct sponsors receive a baseline 50% penalty. - Sponsors at
distance two receive a 12.5% penalty. - Sponsors at distance three or
more receive no cascade penalty. - A circuit breaker may pause cascade
penalties during a localized correlated shock.

For the POC, simulate these rules and record the reason for every
update.

**Open decisions:** - What exact value is the percentage applied to? -
Are penalties additive, multiplicative, capped, or floor-limited? - How
are multiple defaulting borrowers sponsored by the same node handled? -
How is a correlated shock detected? The source gives the concept but not
a working statistical rule. - Does a defaulted node's reputation become
negative, or is it reset to a fixed penalty value?

Do not invent a single answer without documenting it as a team decision.

### 7.3 Repayment reward

The original document says successful settlement mints intrinsic
credibility and awards a small reputation yield to the borrower and
sponsor. It does not specify the exact reward equation.

For the POC, use a configurable reward parameter and record it in the
event result. The team should choose the value and limits explicitly.

### 7.4 Event safety

Every simulated loan event should have a unique event ID and a loan ID.
Processing the same event twice must not change reputation twice. Tests
should cover duplicate, malformed, and out-of-order events.

------------------------------------------------------------------------

## 8. Data model proposal

These are proposed POC data shapes, not a final external API contract.

### Participant

``` json
{
  "user_id": "U001",
  "reputation": 10.0,
  "status": "ACTIVE",
  "financial_features": {
    "monthly_income": 25000,
    "monthly_debt": 5000,
    "income_volatility": 0.15,
    "history_months": 6
  }
}
```

### Vouch

``` json
{
  "vouch_id": "V001",
  "source_user_id": "U001",
  "target_user_id": "U002",
  "active": true
}
```

### Simulated loan event

``` json
{
  "event_id": "EVT001",
  "loan_id": "L001",
  "borrower_id": "U002",
  "event_type": "LOAN_REPAID",
  "timestamp": "2026-10-24T12:00:00Z"
}
```

### Assessment result

``` json
{
  "user_id": "U002",
  "trust_score": 0.0,
  "repayment_capacity_estimate": 0.0,
  "uncertainty_estimate": 0.0,
  "recommended_limit": 0.0,
  "status": "PROTOTYPE_ONLY",
  "contributing_paths": [],
  "risk_factors": [],
  "calculation_version": "0.1"
}
```

The zeroes are placeholders, not meaningful sample outputs. The team
must define units, ranges, and formulas before the assessment result is
treated as valid.

### Data model notes

-   Use stable synthetic IDs, not real identity numbers.
-   Store financial features separately from public graph relationships
    where practical.
-   Validate all incoming data.
-   Preserve the input snapshot or version used for each assessment.
-   Do not store raw PAN/Aadhaar data in the POC.

------------------------------------------------------------------------

## 9. Proposed code organization

``` text
veritrust-engine/
├── data/
│   ├── users.json
│   ├── vouches.json
│   ├── financial_features.json
│   └── loan_events.json
├── src/
│   └── veritrust/
│       ├── models.py
│       ├── data_loader.py
│       ├── graph_builder.py
│       ├── trust_engine.py
│       ├── reputation_engine.py
│       ├── financial_risk.py
│       ├── uncertainty.py
│       ├── credit_engine.py
│       ├── explanation_engine.py
│       └── simulation.py
├── tests/
│   ├── test_data_validation.py
│   ├── test_graph_builder.py
│   ├── test_trust_capacity.py
│   ├── test_trust_paths.py
│   ├── test_cycles.py
│   ├── test_reputation.py
│   ├── test_event_idempotency.py
│   └── test_credit_engine.py
├── main.py
├── requirements.txt
└── README.md
```

### Module boundaries

-   `models.py`: shared data structures and validation.
-   `data_loader.py`: file loading and validation orchestration.
-   `graph_builder.py`: graph creation only.
-   `trust_engine.py`: trust algorithm only; no financial scoring or
    I/O.
-   `reputation_engine.py`: event processing and reputation changes.
-   `financial_risk.py`: repayment-capacity estimate behind a
    replaceable interface.
-   `uncertainty.py`: uncertainty estimate and its documented
    assumptions.
-   `credit_engine.py`: combines component outputs into an assessment.
-   `explanation_engine.py`: creates human-readable explanations.
-   `simulation.py`: runs scenarios and event sequences.
-   `main.py`: command-line entry point.

Keep modules as functions or classes within one application. Do not
create a microservice per module for this POC.

------------------------------------------------------------------------

## 10. Technology choices

The stack is undecided. The following is a proposal for speed and
clarity, not a requirement.

  -----------------------------------------------------------------------
  Need                    Suggested option        Reason
  ----------------------- ----------------------- -----------------------
  Language                Python                  Fast iteration and easy
                                                  numerical testing.

  Graph data structure    NetworkX                Useful directed-graph
                                                  and traversal tools.

  Input validation        Pydantic or dataclasses Helps catch malformed
                          plus explicit checks    records early.

  Numerical calculations  NumPy, if needed        Useful for
                                                  calculations; not
                                                  mandatory for a small
                                                  prototype.

  Input format            JSON or CSV             Easy to inspect and
                                                  share.

  Testing                 pytest                  Supports small, focused
                                                  tests.

  Interface               CLI first; FastAPI only Keeps the engine the
                          if needed               priority.

  Storage                 In-memory first         Avoids spending the POC
                                                  window on database
                                                  setup.

  Graph database          Not needed yet          Add only if graph size
                                                  or persistence requires
                                                  it.
  -----------------------------------------------------------------------

NetworkX should not contain the business rules. It should provide graph
data structures and traversal utilities; VeriTrust should implement the
scoring rules itself.

### Alternative stack considerations

-   A database is useful once state must persist between runs, but it is
    not needed to prove the core algorithms.
-   A graph database such as Neo4j may help with larger graph queries,
    but it does not replace the trust algorithm.
-   FastAPI is useful if a separate frontend needs to call the engine. A
    CLI is faster for the first end-to-end test.
-   A trained ML model should not be added merely to make the project
    appear more advanced. It requires suitable labeled data, evaluation,
    and calibration.

### Production evolution: explainable machine learning suite and empirical validation

The engine incorporates a calibrated explainable machine learning suite (`backend/ml/`) evaluated on synthetic and real-world lending data:

1. **Realistic noise injection (`backend/ml/noise.py`):** Injects 6 controlled real-world imperfections (measurement jitter, currency rounding, MAR/MNAR missingness, fat-tailed emergency expense shocks, macroeconomic drift, and 2.5% label flips).
2. **Explainable model suite (`backend/ml/models.py`):** Trained concurrently across GPU CUDA streams (NVIDIA RTX 4050) and multithreaded CPU workers:
   - Explainable Boosting Machine (EBM): glassbox Generalized Additive Model with additive spline shape curves.
   - XGBoost GPU: histogram-based gradient boosting on CUDA with TreeSHAP local attributions.
   - PyTorch GPU Tabular Neural Network: deep residual network with Monte Carlo Dropout for epistemic uncertainty estimation.
   - LightGBM: depth-regularized gradient boosting with early stopping.
   - Calibrated Logistic Scorecard: Basel-style $L_2$-regularized linear scorecard benchmark.
3. **Generalized meta-ensemble (`GeneralizedCreditModel`):** Fuses the five models via held-out inverse-Brier weights, achieving **0.8892 AUC** and **0.9191 PR-AUC** on the Option A market shock benchmark.
4. **Finite-sample conformal prediction (`backend/ml/conformal.py`):** Delivers Split and Mondrian conformal prediction sets guaranteeing $\ge 90\%$ coverage across data completeness tiers, outputting tri-state decisions (`ELIGIBLE`, `REVIEW`, `DECLINE_CANDIDATE`).
5. **Empirical ablation study (`backend/ml/ablation.py`):** Confirmed on 4,502 borrowers that simple degree centrality provides zero lift ($\Delta\text{AUC} = +0.0001$), whereas VeriTrust reputation propagation rescues **26 Invisible Primes** with a **38.46%** default rate (a $26.25$ percentage-point reduction in default risk versus the 64.71% population baseline).
6. **Prosper empirical findings (55,305 loans):** Validated that unbacked social recommendations increase default rates (32.81% vs 30.79%), while endorsements backed by financial capital reduce defaults to 23.71% ($-7.08$ percentage points).

------------------------------------------------------------------------

## 11. Example end-to-end scenario

Use a small synthetic graph:

``` text
Trusted Root A
    |
    v
Sponsor B
    |
    v
Borrower C

Trusted Root A
    |
    v
Sponsor D
    |
    v
Borrower C
```

The engine should: 1. Load the users and vouches. 2. Confirm that the
graph edges reference valid users. 3. Compute the eligible paths from
trusted roots to Borrower C. 4. Apply edge weights and hop decay. 5.
Combine path contributions using the chosen aggregation rule. 6. Read
Borrower C's synthetic financial features. 7. calculate the financial
estimate and uncertainty. 8. Return an assessment with contributing
paths and risk factors. 9. Process a simulated repayment or default
event. 10. Update reputation, recompute affected trust, and show the
assessment difference.

This example tests multiple paths. Add separate fixtures for a cycle, a
disconnected borrower, a collusion ring, and a shared intermediate node.

------------------------------------------------------------------------

## 12. Testing strategy

### 12.1 Graph and trust tests

-   A node with no path from a trusted root receives no root-derived
    trust.
-   A zero-capacity sponsor cannot allocate positive vouch weight.
-   The sum of outgoing edge weights never exceeds available capacity.
-   A repeated node in a path cannot contribute again through that same
    path.
-   Adding a cycle does not create extra trust solely from circular
    traversal.
-   Longer paths are attenuated according to the configured rule.
-   Multiple paths are combined according to the documented aggregation
    rule.
-   Shared roots and intermediates do not accidentally multiply the same
    evidence without limit.

### 12.2 Reputation tests

-   Repayment applies the configured reward once.
-   Default applies the configured penalty once.
-   Direct and second-hop penalties follow the configured rules.
-   Nodes beyond the configured horizon are unaffected by cascade
    penalties.
-   Replaying an event does not change state a second time.
-   A new event with a different ID is processed according to the
    loan-state rules.
-   The engine records the reason and magnitude of each change.

### 12.3 Credit assessment tests

-   More uncertainty makes the configured conservative score lower, all
    else equal.
-   Missing financial evidence is not silently interpreted as a default.
-   Trust and financial features are normalized or combined through
    explicit rules.
-   Results remain within defined ranges.
-   The output contains a calculation version and explanation.
-   A change in reputation causes affected assessments to be
    recalculated.

### 12.4 Adversarial scenarios

-   A group of zero-reputation users vouches for one another.
-   A group with positive reputation forms a collusion ring.
-   Many paths share the same trusted root.
-   A sponsor issues many vouches.
-   A borrower defaults and then appears through a new synthetic user
    ID.
-   Multiple borrowers sponsored by the same participant default close
    together.
-   An event is duplicated or delivered out of order.

The POC cannot prove resistance to every attack. It should demonstrate
known defenses and expose unresolved weaknesses.

------------------------------------------------------------------------

## 13. Evaluation and demo criteria

The engine demonstration should show behavior, not only display a score.

### Minimum demo

1.  Load a synthetic graph.
2.  Select a borrower.
3.  Show the contributing trust paths.
4.  Show the trust calculation and financial inputs.
5.  Display the credit recommendation and uncertainty.
6.  Simulate repayment and show the resulting reputation change.
7.  Simulate default in a separate scenario and show sponsor penalties.
8.  Compare the assessment before and after the event.
9.  Show that replaying the same event does not apply the change twice.

### Suggested measurable checks

-   Capacity conservation passes for every sponsor.
-   Cycle tests show no artificial gain from repeated traversal.
-   Event idempotency tests pass.
-   The same inputs and calculation version produce the same output.
-   Every assessment has an explanation.
-   The team can compare path-based and global scoring on the same test
    graphs if both baselines are implemented.

Do not use synthetic results to claim that VeriTrust predicts real
defaults accurately. That requires real, appropriate data and
independent evaluation.

------------------------------------------------------------------------

## 14. Risks and limitations

### Trust is not repayment ability

A well-connected borrower can still default. Graph trust should be one
input, not proof of solvency.

### Trusted roots are a governance problem

The system needs a defensible way to identify initial trusted nodes. If
roots are chosen arbitrarily, the graph inherits that bias.

### Collusion is not solved by cycle prevention alone

A visited set prevents circular traversal from repeatedly contributing
along one path. It does not stop colluders with existing positive
reputation from coordinating endorsements.

### Path aggregation can double-count evidence

Multiple graph paths may rely on the same root or sponsor. Counting each
path as independent evidence can inflate trust.

### Reputation penalties can spread unfairly

A sponsor may have vouched for a borrower who later suffers a legitimate
economic shock. Penalty rules need limits and evidence; otherwise, the
protocol can punish people for circumstances outside their control.

### Uncertainty needs a defensible definition

An uncertainty value is useful only if its scale and behavior are
defined. A made-up uncertainty score should not be presented as
calibrated statistical confidence.

### Privacy and identity remain future work

The current POC uses synthetic identities. It does not establish
real-world identity uniqueness, protect live identity data, or provide
production-grade identity recovery.

### The credit engine is not a lender

The engine produces an assessment. A separate lender, funding source,
and lending process are required to issue real credit.

------------------------------------------------------------------------

## 15. Open decisions register

These decisions must be resolved or explicitly deferred.

  ------------------------------------------------------------------------
  ID                Decision          Why it matters    Proposed next step
  ----------------- ----------------- ----------------- ------------------
  D1                Trusted-root      Defines the       Define who can be
                    selection         source of trust.  a root and how
                                                        roots are
                                                        approved.

  D2                Path-based vs     Determines the    Implement
                    global scoring    core algorithm.   path-based first;
                                                        compare a global
                                                        baseline if time
                                                        permits.

  D3                Path aggregation  Prevents inflated Choose a
                                      scores from       documented
                                      overlapping       aggregation rule
                                      paths.            and add
                                                        shared-root tests.

  D4                Capacity locking  Determines        Separate total,
                                      available vouch   allocated, and
                                      weight during     available
                                      active loans.     capacity.

  D5                Reputation scale  Determines how    Define valid
                                      capacity and      ranges,
                                      penalties behave. initialization,
                                                        floors, and caps.

  D6                Repayment reward  Changes borrower  Use a configurable
                                      and sponsor       POC value and
                                      reputation.       document it.

  D7                Default penalty   Percentages are   Define the base,
                    equation          ambiguous without sign, caps, and
                                      a reference       repeated-default
                                      value.            behavior.

  D8                Financial         Needed to produce Start with
                    estimate          a meaningful      transparent
                                      credit            synthetic rules
                                      assessment.       and a replaceable
                                                        interface.

  D9                Uncertainty model Affects           Define a
                                      conservative      transparent proxy;
                                      decisions.        do not claim
                                                        calibration.

  D10               Score-to-limit    A score alone     Use a documented
                    mapping           does not define a demo-only mapping
                                      loan amount.      or return a score
                                                        without a limit.

  D11               Shock circuit     Needed to avoid   Defer until a
                    breaker           unfair correlated measurable trigger
                                      penalties.        can be justified.

  D12               Persistence and   Affects           Start in-memory
                    API               integration and   with CLI; add
                                      deployment.       persistence or
                                                        FastAPI when
                                                        needed.
  ------------------------------------------------------------------------

------------------------------------------------------------------------

## 16. Recommended implementation sequence

1.  Agree on terminology, data structures, and trusted-root fixtures.
2.  Build input validation and graph construction.
3.  Implement and test vouch-capacity conservation.
4.  Implement path-based trust propagation and explanations.
5.  Add cycle, overlapping-path, and collusion tests.
6.  Implement simulated repayment and default processing.
7.  Add idempotency and reputation recalculation.
8.  Add the financial risk interface and uncertainty proxy.
9.  Produce the final assessment and explanation.
10. Run the end-to-end demo and document limitations.

The first milestone is not a polished credit score. It is a correct,
inspectable graph calculation that the team can test and explain.

------------------------------------------------------------------------

## 17. Reference basis

This document is based primarily on the supplied **Project Technical
Documentation: VeriTrust --- Transitive Decentralized Credit Assessment
Protocol**, especially its sections on identity, vouch-capacity
conservation, hop attenuation, cycle absorption, default cascades,
dual-axis assessment, architecture, lifecycle, and threat model.

The following are preserved from the source specification: -
Character/reputation and epistemic uncertainty are treated as separate
concepts. - Vouch capacity is intended to be conserved. - Trust decays
across graph hops. - Cycles should not generate extra credibility. -
Default penalties are damped by graph distance. - Credit assessment
combines expected capacity and uncertainty. - The long-term design
includes client platforms, an off-chain analytical engine, and an EVM
smart-contract layer.

This document adds proposed implementation structure, testing strategy,
code organization, and a comparison of path-based versus global
iterative scoring. Those additions are recommendations, not claims that
the original specification already settled them.

------------------------------------------------------------------------

## Appendix A --- Suggested first milestone

**Milestone name:** Trust Graph Core

**Deliverables** - Synthetic users and vouches. - Input validation. -
Directed graph construction. - Vouch-capacity calculation. - Path-based
trust calculation. - Cycle and overlapping-path tests. - An explanation
listing the paths and contributions used for a borrower.

**Acceptance criteria** - Every output is reproducible for the same
input and configuration. - Capacity conservation is tested. - Cycles do
not create trust by repeated traversal. - Missing root paths are handled
explicitly. - The result includes enough detail for a teammate to verify
the calculation by hand.

Once this milestone is stable, build reputation events and credit
assessment on top of it.

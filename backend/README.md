# backend
Web-of-trust credit engine, dual-axis underwriting, and lending simulations.

## Status
- **Core Engine Complete:** User nodes, NetworkX DiGraph builder, out-degree capacity conservation, and atomic sibling re-weighting.
- **Propagation & Underwriting Complete:** Anchor path traversal, geometric hop attenuation ($\lambda = 0.5$), per-path cycle absorption, cash-flow scoring, and Lower Confidence Bound (LCB) loan limit derivation.
- **Lending & Slashing Complete:** In-memory lending service, repayment boosts, and atomic 4-level slashing cascade on default.
- **Trust Lifecycle & Reputation Ledger Complete:** Immutable append-only event store (ACID SQLite + POSIX JSONL mirror), SHA-256 cryptographic hash chaining, strict idempotency enforcement, and disaster recovery via deterministic state replay.
- **Credit Decisioning & Optimization Suite Complete:**
  - **Rule-based affordability engine:** Computes disposable income $D = I - E - B$, protected minimum cash buffer $B$, and maximum affordable monthly instalments under explicit policy caps (ITI/FOIR $\le 40\%$, DTI $\le 50\%$). Treats missing or unverified information separately from low affordability.
  - **Loan optimizer using Google OR-Tools:** Solves discrete search grid with CP-SAT constraint programming, optimizing for either lowest total borrowing cost (`MIN_COST`) or largest sustainable principal (`MAX_PRINCIPAL`). Outputs original request, best feasible alternative, EMI, total interest, and binding constraints.
  - **Monte Carlo stress tester:** Simulates thousands of stochastic financial scenarios (income volatility, payment delays, emergency expense shocks) using reproducible seeded pseudo-random sampling (no ML). Measures shortfall frequency, 5th-percentile adverse residual cash, and the exact income shock tolerance boundary.
  - **Explanation and evidence engine:** Generates traceable, auditable natural language explanations from the exact rules that fired, evaluating Financial Capacity, Evidence Reliability, Graph Reputation, and Stress-Test Resilience as four separate dimensions.
- **Test Suite Complete:** pytest suite covering models, vouch conservation, propagation, slashing, cryptographic ledger integrity, affordability rules, OR-Tools optimization, Monte Carlo stress testing, explanation synthesis, the community engine and every API router.
- **Demo seed:** the story cast (Sahyog Microfinance anchoring Meena, Ramesh and Anand; borrowers Lakshmi, Suresh and Imran), in `data/store.json` (store version 2.0; an older store is reseeded on load).

## Run
Create and activate a virtual environment, install dependencies, and run the engine:

```bash
# In the backend directory
python -m venv .venv

# On Windows PowerShell
.venv\Scripts\Activate.ps1

# On macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Mode A: Interactive Shell Mode (Recommended)

Run `python main.py` with no arguments to enter the interactive shell:

```bash
python main.py
```

You will enter an interactive prompt where you can execute commands directly:

```text
=======================================================================
 VeriTrust Interactive CLI — Web-of-Trust Credit & Lending Engine
 Type 'help' for available commands, or 'exit' / 'quit' to leave.
=======================================================================

veritrust> users
veritrust> login MEENA
veritrust (MEENA)> whoami
veritrust (MEENA)> vouch IMRAN
veritrust (MEENA)> exit
```

### Mode B: Single Command Line Invocations

Run commands directly from your terminal:

```bash
python main.py users                          # List all users
python main.py signup DAVID "David Miller"    # Create a new user
python main.py login MEENA                    # Log in as Meena
python main.py whoami                         # View current session details & credit limit
python main.py check LAKSHMI                      # Check vouch status & credit limit
python main.py vouch DAVID                    # Vouch for David as Meena
python main.py borrow 15000                   # Borrow INR 15,000 within credit limit
python main.py lend IMRAN 5000              # Peer-to-peer lend to Imran
python main.py repay LN_00001 15000           # Repay active loan
python main.py history LAKSHMI                    # View audit trail of all reputation events for Lakshmi
python main.py audit                          # Cryptographically audit SHA-256 ledger hash chain
python main.py replay --restore               # Deterministically reconstruct state from raw events
python main.py denounce IMRAN               # Denounce bad actor and trigger slashing
python main.py graph                          # Inspect Web-of-Trust graph topology
python main.py --demo                         # Run automated walkthrough simulation
```

### Step-by-Step Walkthrough

1. **View all nodes in the network:**
   ```bash
   python main.py users
   ```
   *Lists all users, their reputation $R$, capacity $C$, status, and anchor designation.*

2. **Register a new user:**
   ```bash
   python main.py signup DAVID "David Miller"
   ```
   *Registers `DAVID` into the Web-of-Trust graph.*

3. **Check David's trust standing:**
   ```bash
   python main.py check DAVID
   ```
   *Output: `UNVOUCHED: User 'DAVID' has no active endorsements. Credit Limit: INR 0.00`.*

4. **Log in as Meena (kirana store, Old Hubballi):**
   ```bash
   python main.py login MEENA
   python main.py whoami
   ```
   *Shows Meena's profile, $10.0$ capacity, active loans, and who she is endorsing.*

5. **Vouch for David:**
   ```bash
   python main.py vouch DAVID
   ```
   *Meena endorses David. Capacity is automatically conserved and divided equally among her vouchees.*

6. **Check David again:**
   ```bash
   python main.py check DAVID
   ```
   *Output: `VOUCHED: User 'DAVID' is actively endorsed.` with the limit the graph now supports.*

7. **Log in as David and borrow money:**
   ```bash
   python main.py login DAVID
   python main.py borrow 25000
   python main.py loans --mine
   ```
   *Disburses a ₹25,000 loan to David within his approved limit.*

8. **Repay the loan:**
   ```bash
   python main.py repay LN_00001 25000
   ```
   *Full settlement achieved! David’s reputation is boosted ($R + 2.0$), and Meena receives sponsor yield ($R + 1.0$).*

9. **Audit the Cryptographic Reputation Ledger:**
   ```bash
   python main.py history LAKSHMI
   python main.py audit
   ```
   *Displays the immutable history of all events impacting Lakshmi's score, attached settlement evidence, and verifies the complete SHA-256 hash chain from Genesis to Head.*

10. **Peer-to-peer lending (Meena funds Imran directly):**
    ```bash
    python main.py login MEENA
    python main.py vouch IMRAN
    python main.py lend IMRAN 5000
    ```
    *Meena funds Imran's loan directly. The contract tracks Meena as the lender.*

11. **View the Trust Graph:**
    ```bash
    python main.py graph
    ```
    *Displays an ASCII tree of all nodes, active endorsements, and edge weights.*

12. **Denounce a bad actor / trigger default:**
    ```bash
    python main.py denounce IMRAN --reason "Default on micro-loan"
    python main.py check IMRAN
    ```
    *Imran is marked `DEFAULTED`, capacity is frozen to 0, and the **atomic 4-level slashing cascade** penalizes Meena and transitive ancestors.*

13. **Disaster Recovery & State Replay:**
    ```bash
    python main.py replay --restore
    ```
    *Replays all raw immutable events from genesis, verifies cryptographic integrity, and reconstructs the full graph and loan state.*

14. **Reset state back to fresh seed data:**
    ```bash
    python main.py reset
    ```

### Command Cheat Sheet

| Command | Description |
|---|---|
| `users` | List all registered nodes, reputations, and capacities |
| `signup <id> [name]` | Register a new user node |
| `login <id>` | Log in as that user |
| `whoami` | Show current user's profile, credit limit, and vouches |
| `logout` | Clear active session |
| `check <id>` | Quick check: returns `VOUCHED`, `UNVOUCHED`, or `DENOUNCED` |
| `assess [id]` | Detailed dual-axis credit assessment ($\mu$, $\sigma^2$ uncertainty, limit) |
| `vouch <target>` | Vouch for a user (conserving capacity across siblings) |
| `unvouch <target>` | Remove an endorsement |
| `borrow <amount>` | Borrow money up to your approved credit ceiling |
| `repay <loan_id> <amount>` | Repay an active loan (boosts reputation on full payment) |
| `lend <borrower> <amount>` | Directly fund/lend to another user |
| `loans [--mine]` | List active and past loans |
| `history [user_id]` | View chronological reputation mutations, delta, and evidence |
| `audit` | Verify SHA-256 hash chain from Genesis to Head for tamper detection |
| `replay [--restore]` | Deterministically reconstruct protocol state from raw events |
| `optimize <amt> [-t tenure] [-b borrower] [--objective MIN_COST/MAX_PRINCIPAL]` | Run rule-based affordability, OR-Tools optimization, Monte Carlo stress testing & explanation |
| `counterfactual <amt> [-t tenure] [-b borrower]` | Deterministic what-if simulator computing exact Delta I, Delta E, Delta T, Delta P remedies |
| `stress-compare -pa <amt> -ta <t> -pb <amt> -tb <t>` | Compare two loan plans side-by-side under identical seeded Monte Carlo futures |
| `simulate-attack [--attack sybil/collusion/dilution/burst/all]` | Adversarial attack simulator testing graph invariants & defensive safeguards |
| `audit-decision <amt> [-t tenure] [-b borrower]` | Forensic decision explorer: explicit rule traces, primary evidence, paths, and sensitivity |
| `recourse file/resolve/audit` | Borrower dispute workflow, evidence quality classification & score recalculation audit |
| `serve [--host host] [--port port]` | Launch FastAPI REST API server (Swagger UI at `/docs`) |
| `graph` | Visualize the Web-of-Trust network |
| `denounce <id> [--reason]` | Denounce bad actor and trigger 4-level slashing cascade |
| `reset` | Reset state to clean demo seed data |

## Structure
- `localdocs/`: Architectural briefings and implementation specifications.
- `src/veritrust/`: Production engine package.
  - `models.py`: Pydantic domain entities (`User`, `Transaction`, `Vouch`, `Loan`, `CreditAssessment`, `Evidence`, `LedgerEvent`).
  - `ledger.py`: Append-only event store (`ReputationLedger`), SHA-256 cryptographic hash chaining, idempotency enforcement, and state reconstruction.
  - `engine.py`: NetworkX graph management, user creation, vouch/unvouch, capacity conservation, and ledger event dispatch.
  - `config.py`: Dynamic configuration loaded from environment or `.env` (`K`, `ALPHA`, `BETA`, `HOP_DECAY`, `GAMMA`, etc.).
  - `scoring.py`: Credibility path enumeration, hop decay, cycle absorption, and dual-axis underwriting.
  - `lending.py`: In-memory loan lifecycle, repayments, 4-level slashing cascade, and settlement yields.
  - `affordability.py`: Rule-based affordability engine ($D = I - E - B$, protected cash buffer $B$, ITI/FOIR $\le 40\%$, DTI $\le 50\%$).
  - `optimizer.py`: Google OR-Tools CP-SAT optimizer for loan plan restructuring (`MIN_COST` vs `MAX_PRINCIPAL`).
  - `stress_tester.py`: Seeded pseudo-random Monte Carlo stress tester (5,000 simulations, comparative dashboards).
  - `explainer.py`: Multi-dimensional explanation and evidence engine across Financial Capacity, Evidence Reliability, Graph Reputation, and Stress Resilience.
  - `counterfactual.py`: Deterministic counterfactual loan simulator computing sensitivity margins and remedies.
  - `attack_simulator.py`: Web-of-Trust attack simulator (Sybil cliques, collusion rings, sponsor dilution, burst anomalies).
  - `audit_explorer.py`: Forensic decision explorer detailing numerical rule traces, evidence links, and sensitivity deltas.
  - `recourse.py`: Borrower recourse protocol, evidence-quality tracking (`MISSING`, `STALE`, `DUPLICATED`, `DISPUTED`), and recalculation audit.
  - `community.py`: Community vouching engine (KNOWN and EVIDENCE vouches, capped evidence weight, reward preview) and its in-memory seeded store.
  - `simulator.py`: Simulation and parameter calibration engine across canonical Web-of-Trust benchmark topologies.
  - `api/`: FastAPI REST API package. `routes.py`: applications, evidence, endorsements, assessments, scenarios, disputes, users, loans, graph (uses the OR-Tools optimizer). `protocol_routes.py`: vouch requests, lender decisions, defaults. `community_routes.py`: the community platform. `registry.py`: in-memory applications and assessments shared by the routers.
- `tests/`: Pytest unit tests for all mathematical invariants, state transitions, and ledger integrity.
- `main.py`: End-to-end interactive CLI demonstration.
- `requirements.txt`: Python package requirements (`pydantic`, `networkx`, `ortools`, `fastapi`, `uvicorn`, `httpx`, `pytest`).

## Interfaces
- **`TrustEngine`**: Core graph state manager exposing `create_user()`, `vouch()`, `unvouch()`.
- **`CreditScorer`**: Underwriting interface exposing `assess_credit()`, `compute_vouch_score()`, `assess_combined()`.
- **`LendingService`**: Lending lifecycle interface exposing `borrow()`, `repay()`, `default_loan()`.
- **`ReputationLedger`**: Immutable event store exposing `append_event()`, `get_history()`, `verify_integrity()`, `reconstruct_state()`.
- **`AffordabilityEngine`**: Evaluates disposable income, minimum cash buffer, and maximum affordable EMI.
- **`LoanOptimizer`**: Google OR-Tools CP-SAT solver generating optimal feasible plans and restructuring alternatives.
- **`MonteCarloStressTester`**: Evaluates shortfall risk, adverse 5th-percentile cash, and side-by-side plan comparisons.
- **`CounterfactualSimulator`**: Evaluates parameter sweeps and derives exact required adjustments ($\Delta I, \Delta E, \Delta T, \Delta P$).
- **`TrustGraphAttackSimulator`**: Evaluates Sybil cliques, collusion rings, sponsor dilution, and temporal burst anomalies.
- **`DecisionAuditExplorer`**: Forensic inspection of rule thresholds, graph paths, evidence, and input sensitivity.
- **`BorrowerRecourseWorkflow`**: Dispute filing, evidence corrections, recalculation tracking, and quality auditing.
- **`FastAPI REST API`**: Interactive OpenAPI docs available at `http://localhost:8000/docs`; shapes in `docs/API_CONTRACT.md`. Every endpoint declares a response model, so `make types` generates `frontend/src/types/api.d.ts`.
- **`CommunityStore`**: Community asks, vouches, setbacks and consent, exposed under `/api/v1/community`.
- **CLI**: Executed via `python main.py`.

## Config
All algorithmic parameters can be configured via environment variables or a `.env` file (see `.env.example`):
- `K` / `KAPPA`: Epistemic uncertainty penalty parameter for LCB (default: `1.0`).
- `ALPHA`: Weight of graph trust vs cash-flow in composite capacity $\mu$ (default: `0.6`).
- `BETA`: Settled loan and vouch boost exponent (default: `0.1`).
- `HOP_DECAY` / `LAMBDA`: Geometric hop decay factor (default: `0.5`).
- `BASE_UNIT_INR`: Base monetary conversion scale per score point in INR (default: `10000.00`).
- `DEFAULT_BASE_SLASH`: Primary default slash amount $\delta_0$ (default: `10.0`).
- `GAMMA`: Direct sponsor penalty damping fraction (default: `0.5`).
- `BORROWER_REWARD`: Settlement reputation reward for borrower (default: `2.0`).
- `SPONSOR_REWARD`: Settlement reputation reward for sponsor (default: `1.0`).
- `CIRCUIT_BREAKER_THRESHOLD`: Cluster default rate pause threshold $\theta$ (default: `0.30`).
- `POSEIDON_PROTOCOL_SALT`: Simulated identity anchor protocol salt (`# ZK_STUB`).
- `DEMO_MODE`: Boolean flag for deterministic demo paths (default: `true`).

## Testing
Run the complete test suite:

```bash
# In backend directory with .venv activated
pytest -v

# Run individual test files
pytest tests/test_trust.py          # Out-degree conservation, hop decay, multi-anchor sum
pytest tests/test_cycles.py         # Per-path cycle absorption, Sybil ring absorption
pytest tests/test_credit.py         # Dual-axis scoring, thin vs rich file, LCB derivation
pytest tests/test_reputation.py     # Repayment yields, atomic 4-level slashing cascade
pytest tests/test_ledger.py         # Cryptographic hash chain, tamper detection, replay
pytest tests/test_models.py         # Pydantic schemas, Decimal validation
pytest tests/test_affordability.py  # D = I - E - B, buffer floors, FOIR/DTI caps
pytest tests/test_optimizer.py      # Google OR-Tools CP-SAT solver, MIN_COST & MAX_PRINCIPAL
pytest tests/test_stress_tester.py  # Seeded Monte Carlo simulations, break income, shock tolerance
pytest tests/test_explainer.py      # 4-dimension explanation engine, traceable rules
pytest tests/test_community.py      # Community vouching known answers (same as the frontend's)
pytest tests/test_protocol_routes.py # Vouch requests, decisions, defaults, community API (no OR-Tools needed)
pytest tests/test_api_routes.py     # Assessment, scenario and other REST routes (needs OR-Tools)
pytest tests/test_mathematical_framework.py # Complete mathematical framework, rank weights, and calibration invariants
```

## Notes
- **Out-Degree Conservation:** Outgoing edge weights must strictly sum to $\le C_u$. Sibling re-weighting is atomic.
- **Cycle Absorption:** Visited-set during path discovery is strictly **per-path**, never global across paths.
- **Decimal Precision:** All intermediate products, weights, and scores must use `Decimal` to avoid floating-point drift.
- **Disclaimer:** All synthetic outputs are illustrative prototype recommendations, not validated financial advice.

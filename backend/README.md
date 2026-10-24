# backend
Web-of-trust credit engine, dual-axis underwriting, and lending simulations.

## Status
- **Core Engine Complete:** User nodes, NetworkX DiGraph builder, out-degree capacity conservation, and atomic sibling re-weighting.
- **Propagation & Underwriting Complete:** Anchor path traversal, geometric hop attenuation ($\lambda = 0.5$), per-path cycle absorption, cash-flow scoring, and Lower Confidence Bound (LCB) loan limit derivation.
- **Lending & Slashing Complete:** In-memory lending service, repayment boosts, and atomic 4-level slashing cascade on default.
- **Test Suite Complete:** Unit tests covering models, vouch conservation, propagation, and slashing.

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
veritrust> login ALICE
veritrust (ALICE)> whoami
veritrust (ALICE)> vouch CHARLIE
veritrust (ALICE)> exit
```

### Mode B: Single Command Line Invocations

Run commands directly from your terminal:

```bash
python main.py users                          # List all users
python main.py signup DAVID "David Miller"    # Create a new user
python main.py login ALICE                    # Log in as Alice
python main.py whoami                         # View current session details & credit limit
python main.py check BOB                      # Check vouch status & credit limit
python main.py vouch DAVID                    # Vouch for David as Alice
python main.py borrow 15000                   # Borrow INR 15,000 within credit limit
python main.py lend CHARLIE 5000              # Peer-to-peer lend to Charlie
python main.py repay LN_00001 15000           # Repay active loan
python main.py denounce CHARLIE               # Denounce bad actor and trigger slashing
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

4. **Log in as Alice (Community Leader):**
   ```bash
   python main.py login ALICE
   python main.py whoami
   ```
   *Shows Alice's profile, $10.0$ capacity, active loans, and who she is endorsing.*

5. **Vouch for David:**
   ```bash
   python main.py vouch DAVID
   ```
   *Alice endorses David. Capacity is automatically conserved and divided equally among her vouchees.*

6. **Check David again:**
   ```bash
   python main.py check DAVID
   ```
   *Output: `VOUCHED: User 'DAVID' is actively endorsed. Approved Credit Limit: INR 321,551.28`.*

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
   *Full settlement achieved! David’s reputation is boosted ($R + 2.0$), and Alice receives sponsor yield ($R + 1.0$).*

9. **Peer-to-peer lending (Alice funds Charlie directly):**
   ```bash
   python main.py login ALICE
   python main.py vouch CHARLIE
   python main.py lend CHARLIE 5000
   ```
   *Alice funds Charlie's loan directly. The contract tracks Alice as the lender.*

10. **View the Trust Graph:**
    ```bash
    python main.py graph
    ```
    *Displays an ASCII tree of all nodes, active endorsements, and edge weights.*

11. **Denounce a bad actor / trigger default:**
    ```bash
    python main.py denounce CHARLIE --reason "Default on micro-loan"
    python main.py check CHARLIE
    ```
    *Charlie is marked `DEFAULTED`, capacity is frozen to 0, and the **atomic 4-level slashing cascade** penalizes Alice and transitive ancestors.*

12. **Reset state back to fresh seed data:**
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
| `graph` | Visualize the Web-of-Trust network |
| `denounce <id> [--reason]` | Denounce bad actor and trigger 4-level slashing cascade |
| `reset` | Reset state to clean demo seed data |

## Structure
- `localdocs/`: Architectural briefings and implementation specifications.
- `src/veritrust/`: Production engine package.
  - `models.py`: Pydantic domain entities (`User`, `Transaction`, `Vouch`, `Loan`, `CreditAssessment`).
  - `engine.py`: NetworkX graph management, user creation, vouch/unvouch, and capacity conservation.
  - `config.py`: Dynamic configuration loaded from environment or `.env` (`K`, `ALPHA`, `BETA`, `HOP_DECAY`, `GAMMA`, etc.).
  - `scoring.py`: Credibility path enumeration, hop decay, cycle absorption, and dual-axis underwriting.
  - `lending.py`: In-memory loan lifecycle, repayments, and 4-level slashing cascade.
- `tests/`: Pytest unit tests for all mathematical invariants and state transitions.
- `main.py`: End-to-end interactive CLI demonstration.
- `requirements.txt`: Python package requirements (`pydantic`, `networkx`, `pytest`).

## Interfaces
- **`TrustEngine`**: Core graph state manager exposing `create_user()`, `vouch()`, `unvouch()`.
- **`CreditScorer`**: Underwriting interface exposing `assess_credit(user_id) -> CreditAssessment`.
- **`LendingService`**: Lending lifecycle interface exposing `borrow()`, `repay()`, `default_loan()`.
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
pytest tests/test_trust.py       # Out-degree conservation, hop decay, multi-anchor sum
pytest tests/test_cycles.py      # Per-path cycle absorption, Sybil ring absorption
pytest tests/test_credit.py      # Dual-axis scoring, thin vs rich file, LCB derivation
pytest tests/test_reputation.py  # Repayment yields, atomic 4-level slashing cascade
pytest tests/test_models.py      # Pydantic schemas, Decimal validation
```

## Notes
- **Out-Degree Conservation:** Outgoing edge weights must strictly sum to $\le C_u$. Sibling re-weighting is atomic.
- **Cycle Absorption:** Visited-set during path discovery is strictly **per-path**, never global across paths.
- **Decimal Precision:** All intermediate products, weights, and scores must use `Decimal` to avoid floating-point drift.
- **Disclaimer:** All synthetic outputs are illustrative prototype recommendations, not validated financial advice.

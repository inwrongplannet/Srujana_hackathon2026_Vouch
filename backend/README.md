# backend
Web-of-trust credit engine, dual-axis underwriting, and lending simulations.

## Status
- **Core Engine Complete:** User nodes, NetworkX DiGraph builder, out-degree capacity conservation, and atomic sibling re-weighting.
- **Propagation & Underwriting Complete:** Anchor path traversal, geometric hop attenuation ($\lambda = 0.5$), per-path cycle absorption, cash-flow scoring, and Lower Confidence Bound (LCB) loan limit derivation.
- **Lending & Slashing Complete:** In-memory lending service, repayment boosts, and atomic 4-level slashing cascade on default.
- **Test Suite Complete:** Unit tests covering models, vouch conservation, propagation, and slashing.

## Run
Create and activate a virtual environment, install dependencies, and run the engine CLI:

```bash
# In the backend directory
python -m venv .venv

# On Windows PowerShell
.venv\Scripts\Activate.ps1

# On macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the CLI demo walkthrough
python main.py
```

## Structure
- `localdocs/`: Architectural briefings and implementation specifications.
- `src/veritrust/`: Production engine package.
  - `models.py`: Pydantic domain entities (`User`, `Transaction`, `Vouch`, `Loan`, `CreditAssessment`).
  - `engine.py`: NetworkX graph management, user creation, vouch/unvouch, and capacity conservation.
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
- No external secrets required for standalone in-memory mode.
- Arithmetic context: Python `decimal.Decimal` with explicit rounding.

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

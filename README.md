# VeriTrust

> PLACEHOLDER. Edit only through `/readme`, and only inside the marker sections.

<!-- BEGIN:overview -->
**Why we are building this:** Access to credit is broken for thin-file micro-entrepreneurs because traditional bureaus confuse absence of history with inability to repay. VeriTrust delivers transparent, dual-axis credit assessments combining verified cash-flow affordability ($D = I - E - B$), Google OR-Tools CP-SAT loan restructuring, a Web-of-Trust graph engine with mathematical Sybil resistance, and Monte Carlo stress testing.
<!-- END:overview -->

<!-- BEGIN:quickstart -->
```bash
# 1. Install pre-push docs gates
make hooks

# 2. Run backend and all tests
make test
make check

# 3. Start backend REST API server
python main.py serve --port 8000

# 4. View platform revenue & transaction fees
python main.py treasury
```
<!-- END:quickstart -->

<!-- BEGIN:features -->
| Feature | Status | Assignee | What it does |
|---|---|---|---|
| Assessment desk | in-progress | Reehan | The first screen on the real FastAPI backend (`/app/assess`): pick a backend applicant, run the assessment, and see bureau, Vouch Score, affordability and evidence apart, with the best plan, a stress test, cited reasons and what-if sliders re-checked by `/scenarios`; tells the presenter how to start the API when it is down |
| Borrower dashboard | in-progress | Reehan | See a two-axis score, ask for a vouch and borrow |
| Community | in-progress | Reehan | Hybrid vouching platform: borrowers post an ask and choose what strangers may see; anyone can vouch as someone who knows them (KNOWN) or as a stranger who read their verified summary (EVIDENCE, weighted by the voucher's track record and capped); vouchers stand by or step back after a setback; the backend serves the same engine and seed under `/api/v1/community` (the screens still use the in-browser store) |
| Default cascade | in-progress | Reehan | Watch a default slash sponsors and stop at two hops |
| Demo director | in-progress | Reehan | Drive the demo story from one presenter bar |
| Identity onboarding | in-progress | Reehan | Sign in with a demo Aadhaar and get a simulated identity anchor |
| Landing page | in-progress | Reehan | Vouch in one screen: a live assessment cycling three cases (no file, a shock, an endorsement ring) with bureau, Vouch, affordability and evidence shown apart; India's credit gap; three animated tests from our dataset (real Prosper loans by score band, simulated shocked borrowers split by vouch, default by vouch strength); the research for and against the idea; a business-model section (who pays whom under institution-owned and platform deployment, with each model's planning prices), each figure linked to its source; then a Vouch Score builder, a loan stress test and an explanation split into observed, reported, inferred and missing; a sticky section nav and a closing guide to the three ways in (guided story, community, Assessment desk) |
| Lender console | in-progress | Reehan | Rank applicants on both axes and read the trust graph |
| Mathematical trust framework | done | Abhijit | Chronological rank-based diminishing returns alpha_uv = 1 / 2^(r-1), hop decay delta, min-path same-source consolidation, diminishing repeat transaction minting, and atomic snapshot default penalties |
| Platform treasury and transaction fees | done | Abhijit | Collects an auditable 1.0% fee cut on all loan disbursements and repayments, tracked on every Transaction model, accumulated in a dedicated Platform Treasury, and exposed via REST and CLI |
| Dual-axis underwriting engine | done | Abhishek | Four-signal credit assessment combining rule-based cash-flow affordability (D = I - E - B), Google OR-Tools CP-SAT loan restructuring, Web-of-Trust graph credibility propagation, and Monte Carlo stress testing |
| Vouching | in-progress | Reehan | See what a vouch costs you, then hold to vouch |
<!-- END:features -->

<!-- BEGIN:architecture -->
VeriTrust evaluates creditworthiness across four transparent, orthogonal dimensions without black-box ML:

1. **Rule-Based Cash-Flow Affordability ($D = I_{\text{net}} - E_{\text{essential}} - B_{\text{floor}}$):** Evaluates verified disposable cash with strict FOIR $\le 40\%$ and DTI $\le 50\%$ policy caps.
2. **Google OR-Tools CP-SAT Loan Optimizer:** Restructures debt principal and tenure under constraint satisfaction.
3. **Web-of-Trust Credibility Graph:** Conserves capacity ($\sum W_{uv} \le C_u$), weights incoming vouches by chronological rank diminishing returns ($\alpha_{uv} = 1/2^{r_{uv}-1}$), absorbs cycles per path, and attenuates hops ($T(P) \propto \delta^{h-1}$).
4. **Monte Carlo Stress Tester:** Evaluates 5,000 forward-looking economic paths to identify income shock tolerance thresholds.
5. **Reputation Ledger & Platform Treasury:** Immutable SHA-256 chained event ledger with automatic 1.0% platform fee cut collection.

Full architectural specification and mermaid diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
<!-- END:architecture -->

<!-- BEGIN:team -->
- Abhishek: repo setup, architecture, review and merge
- Reehan: frontend app, community platform and landing page
- Abhijit: backend credit engine, mathematical framework and platform treasury
<!-- END:team -->

<!-- BEGIN:demo -->
The live demo walks through three core scenarios:
1. **Thin-file Borrower (Lakshmi):** No prior bureau history, but verified monthly cash flows and community vouches produce an approved, stress-tested working capital loan.
2. **Sybil Collusion Ring:** Demonstrates how circular voucher rings are mathematically neutralized by chronological rank weights and cycle absorption.
3. **Settlement & Default Slashing:** Timely repayments boost borrower credibility, while a default triggers an atomic, damped 4-level slashing cascade halting at hop 2.

See [docs/DEMO.md](docs/DEMO.md) for full presenter script and fallback modes.
<!-- END:demo -->

---
New to this repo? Read [docs/REPO_GUIDE.md](docs/REPO_GUIDE.md) for why every folder and file exists.

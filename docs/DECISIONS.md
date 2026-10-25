# Decisions

> Edit only via `/decide`. Newest first.

**Why this file exists:** a running log of what we chose and why (especially new dependencies). Stops repeat debates and doubles as pitch material.

## Log

<!-- ENTRIES -->

### 2026-10-25: Explainable multi-model machine learning suite and finite-sample conformal prediction
- **Decision:** (1) Introduced a multi-paradigm explainable credit-risk architecture in `backend/ml/`: Glassbox Explainable Boosting Machine (`EBMModel`, `interpret.glassbox`), GPU-accelerated XGBoost (`XGBoostGPUModel` on CUDA), PyTorch Tabular Neural Network with Monte Carlo Dropout for epistemic uncertainty (`PyTorchGPUModel`), LightGBM (`LightGBMModel`), and a Basel-style regularized linear scorecard (`LogisticScorecardModel`). (2) Ensembled via inverse-Brier held-out calibration into `GeneralizedCreditModel`, achieving 0.8892 AUC and 0.9191 PR-AUC on Option A shock evaluation. (3) Added Split and Mondrian Conformal Prediction (`backend/ml/conformal.py`) guaranteeing finite-sample 90% and 95% coverage across data completeness tiers with tri-state decisions (`ELIGIBLE`, `REVIEW`, `DECLINE_CANDIDATE`). (4) Implemented realistic synthetic noise injection (`backend/ml/noise.py`) with continuous jitter, financial rounding, MAR/MNAR missingness, fat-tailed shocks, and label noise.
- **Why:** To satisfy literature review findings and regulatory explainability requirements: avoiding ungrounded black boxes while achieving superior predictive discrimination and provable uncertainty coverage for thin-file micro-borrowers.
- **Alternatives considered:** Deep black-box neural networks without explainability (rejected for regulatory non-compliance); single standard logistic regression (insufficient discrimination on complex non-linear shock interactions).
- **Consequences:** Added dependencies (`torch`, `xgboost`, `lightgbm`, `interpret`, `scikit-learn`); fast GPU parallel training harness on CUDA; 152 unit tests passing green.
- **By:** Abhishek, Reehan, Abhijit

### 2026-10-25: Grounding endorsement design on Prosper empirical lessons: skin-in-the-game vs cheap talk
- **Decision:** (1) Forbid unbacked/cheap-talk social endorsements in the underwriting engine; require verifiable skin-in-the-game through atomic reputation slashing ($\Delta_u = q_u \cdot R_u$) and pre-application financial support (`support_before_application_minor`). (2) Enforce score-blind allocation ($w_{uv} = R_u / d_u$) and min-path provenance ($p_u(s) = \min T(P)$) to prevent rational herding feedback loops. (3) Grounded by empirical evaluation on 55,305 resolved Prosper loans (`prosper_loans.csv`) proving that pure cheap-talk recommendations increase default risk (32.81% vs 30.79% baseline), whereas endorsements with co-invested money reduce default risk to 23.71%.
- **Why:** Real P2P lending history (Prosper 2005-2014; Freedman & Jin 2017; Zhang & Liu 2012) demonstrates that unbacked social testimonials create adverse selection and herding bubbles. In contrast, requiring endorsers to allocate owned reputation subject to slashing aligns incentives and unlocks creditworthy "Invisible Primes" with 26.25% lower default rates.
- **Alternatives considered:** Displaying unbacked text recommendations (Prosper failure mode; rejected); symmetric peer voting (vulnerable to Sybil swarms and early-endorsement attacks).
- **Consequences:** All endorsements must allocate owned reputation and be backed by qualifying transaction history; early endorsements are attenuated by chronological rank discounts $\alpha_{uv} = 1/2^{r_{uv}-1}$; model ablation study (`backend/ml/ablation.py`) verifies that this design avoids Prosper's failure modes.
- **By:** Abhishek, Reehan, Abhijit

### 2026-10-25: Platform transaction fee cut and treasury tracking
- **Decision:** (1) Implemented a platform transaction fee cut on all monetary transactions (disbursements and repayments), defaulting to 1.0% (100 bps) surcharge configurable via `PLATFORM_FEE_RATE` env var. (2) Tracked `fee` and `net_amount` Decimal fields on every `Transaction` model and logged them in ledger event payloads (`LOAN_DISBURSED`, `LOAN_REPAID`). (3) Accumulated collected fees in a dedicated `PlatformTreasury` in `LendingService` persisted in `store.json`. (4) Exposed REST endpoints `GET /api/v1/transactions` and `GET /api/v1/platform/treasury`, updated `POST /api/v1/loans/repay` to report `fee_paid`, and added a `treasury` CLI command.
- **Why:** To enable platform monetization by taking a small fee cut from every transaction processed across the protocol, supporting sustainable operations and verifiable treasury auditing.
- **Alternatives considered:** Flat fixed fee per transaction (penalizes micro-borrowers disproportionately); deducting from borrower disbursement proceeds (reduces needed capital disbursement).
- **Consequences:** All transactions now carry auditable fee metadata; cumulative fees are tracked deterministically across ledger replay and state persistence without altering borrower repayment boost logic.
- **By:** Abhishek, Reehan, Abhijit

### 2026-10-25: Backend matches the story: one affordability basis, tau 3, the story cast, community API
- **Decision:** (1) Every route reads essential expenses as income minus net operating income (the `FinancialFeatures` definition, already used by `cli.py` and `audit_explorer.py`) through `affordability_input()`, and a scenario keeps the assessment's rate, tenure, principal, data and dual-axis limit unless overridden. (2) The backend Vouch Score uses tau 3, the Vouch scoring proposal's value, which the frontend already uses; this supersedes the tau 5 noted in the wiring entry below. (3) The seed is the story cast (Sahyog Microfinance; Meena, Ramesh, Anand; Lakshmi, Suresh, Imran), with a store version that reseeds older stores. (4) The community engine moves to `veritrust.community` with the frontend's known answers, plus endpoints for vouch requests, lender decisions and defaults. (5) Every endpoint declares a response model; `docs/API_CONTRACT.md` records the shapes.
- **Why:** the assessment and its what-if disagreed (the scenario route used fixed INR 12,000 expenses, INR 35,000 income and a 10% rate), the two scales of Vouch Score confused the demo, and the frontend's community maths had no server behind it.
- **Alternatives considered:** keeping NOI as expenses (contradicts the model and the contract's own example); tau 5 everywhere (the proposal and the landing page use 3).
- **Consequences:** Vouch Scores and assessment numbers change from earlier runs; an old `backend/data/store.json` is replaced on load. Community and vouch-request state is in memory and has no login. Contract changes need Abhishek's review in the PR.
- **By:** Reehan

### 2026-10-25: Frontend-backend wiring, option C (hybrid)
- **Decision:** The assessment flow runs on the real FastAPI backend: a new Assessment desk (`/app/assess`) calls `/health`, `/api/v1/users`, `/applications`, `/assessments` and `/scenarios` through `frontend/src/api/http.ts` and `backend.ts`, via a Vite dev proxy to `localhost:8000` (or `VITE_API_BASE_URL`). The mock story screens (borrower, voucher, lender, community, demo controls) stay on the in-browser mock until the backend has endpoints for them. The desk shows the backend's own Vouch Score (tau 5, `scoring.py`); the landing page keeps its illustrative tau 3.
- **Why:** the four-signal assessment is what F-04 judges, and the backend already computes it; the mock keeps the rest of the demo working if the API is down.
- **Alternatives considered:** the backend serving the mock's snapshot model (fast, but bypasses the REST contract); moving every screen to REST now (most of the endpoints they need do not exist).
- **Consequences:** `make types` (`npx openapi-typescript`, MIT, run on demand, not installed) now generates `frontend/src/types/api.d.ts` from the backend's OpenAPI; two Vouch Score scales exist until the team picks one tau; the backend still needs endpoints for vouch requests, loan decisions, default and slashing, and the community, plus `response_model`s so `make types` types every response.
- **By:** Reehan

### 2026-10-25: Community platform: hybrid known and evidence vouching
- **Decision:** Two kinds of vouch on one score (`frontend/src/mocks/engine/community.ts`). KNOWN: weight from the voucher's smoothed track record and the relationship's quality, growing over ten years known. EVIDENCE (a stranger who read the borrower's verified summary): the same proposal formula, but reliability counts only after 5 resolved outcomes, edge quality is a flat 0.6, and evidence weight counts up to 0.6 plus two-thirds of the known weight. A vouch keeps the utilisation it was staked at. Strangers see platform-verified summaries the borrower switched on, never statements. Reward on outcome = 100 x 0.1 x w x (y - p), so backing an underrated borrower who repays earns most.
- **Why:** strangers looking at the data a lender already sees add judgement, not facts (the Vouch proposal warns against double-counting a signal); weighting them by a proven record and capping their share keeps the score from being farmed or carried by strangers.
- **Alternatives considered:** known-only circles (narrower than the product the team wants); counting every vouch equally (rewards volume and popularity).
- **Consequences:** the constants are demo values to tune on outcomes; the community runs on an in-memory store with seeded, fictional members until the API contract covers it (needs Abhishek).
- **By:** Reehan

### 2026-10-25: Landing-page story values
- **Decision:** the landing page computes its figures in `frontend/src/mocks/engine/`: the Vouch Score from the Vouch scoring proposal (tau 3, lambda 1, its starting values), EMI from finance-domain, and a demo affordability rule that a plan fits while money left after essentials and EMIs stays at or above zero and DTI stays at or below 0.5. Lender pricing is a demo 24% a year; people, bureau scores and endorser factors are fictional (`src/mocks/story.ts`).
- **Why:** the page shows live, checkable arithmetic rather than hard-coded numbers.
- **Alternatives considered:** static figures (cannot be audited or varied).
- **Consequences:** the DTI cap of 0.5 and the ring penalty (edge quality 0.1) are demo values, not policy; the backend must replace them with tuned ones.
- **By:** Reehan

### 2026-10-24: Demo parameters the skills leave open
- **Decision:** base unit 10,000 INR per point of Score_final, limits rounded down to 500 INR; delta0 = principal / 5,000 INR; settlement mints 0.5 x delta0 to the borrower and 0.1 x delta0 to each direct sponsor; cash-flow normalisation DSCR 0.5 to 2.5, income CV 0 to 0.6, volatility 0 to 1; five expected data fields; pricing 24% a.p.r., 6 monthly instalments, 30-day term. A DEFAULTED identity gets a 0 limit whatever its graph trust.
- **Why:** the formulas need concrete values to run; these give the story a 6,000 INR first limit from one vouch and visible band shrinkage.
- **Alternatives considered:** the PDF's 12.5% hop-2 penalty, rejected for the slashing-cascade skill's 0.25 x delta0.
- **Consequences:** all live in `frontend/src/mocks/engine/params.ts`; the backend must copy them or log a change here.
- **By:** Reehan

### 2026-10-24: Frontend runs on a mock server until the backend exists
- **Decision:** `frontend/src/mocks/` holds an in-memory server with all protocol maths (from the graph-trust-engine, dual-axis-scoring and slashing-cascade skills), reached only through `src/api/client.ts`.
- **Why:** the demo path needs no network and the UI could be built in parallel with the backend.
- **Alternatives considered:** MSW (another dependency for no gain offline); computing in components (breaks the "maths lives in the backend" rule).
- **Consequences:** swapping to the real API touches `client.ts` only; shapes in `src/api/types.ts` must move into `docs/API_CONTRACT.md` (needs Abhishek's OK).
- **By:** Reehan

### 2026-10-24: Frontend stack and libraries
- **Decision:** Vite 8, React 19, TypeScript 6, Tailwind CSS 4, React Router 8, Motion 14 (all MIT); `@dagrejs/dagre` 3.1 (MIT) for layered graph layout; `decimal.js` 10.6 (MIT) for money; `qrcode` 1.5 (MIT); Fontsource Anek Latin, Anek Devanagari, IBM Plex Sans and Mono (OFL); React Bits components vendored into `src/components/bits/` (MIT + Commons Clause). None needs a key or network at demo time.
- **Why:** fast single-page build; dagre gives a direction-aware layout we can draw and animate ourselves; fonts are self-hosted so the demo works offline.
- **Alternatives considered:** Next.js (no server rendering needed); Cytoscape.js (harder to style to the theme and to animate the cascade).
- **Consequences:** `npm ci` in `frontend/`; CI needs a Node setup step before `make check` runs frontend tests.
- **By:** Reehan

### 2026-10-24: Visual direction "ink on ledger paper"
- **Decision:** khadi paper neutrals, one indigo ink (`#24368F`), node-state colours for meaning only, Anek for display and IBM Plex for UI, hatching for uncertainty, motion only when protocol state changes.
- **Why:** trust and community over generic fintech gradients; the kirana udhaar book is the product's origin story.
- **Alternatives considered:** dark Linear-style console (washes out on projectors).
- **Consequences:** tokens live in `frontend/src/styles/index.css`; icons are a custom SVG set.
- **By:** Reehan

2026-10-25: Added FastAPI, Uvicorn, and HTTPX for REST API layer conforming to Master Developer Documentation v2 — typed endpoints for loan applications, evidence registration, endorsements, credit assessments, and dispute recourse.
2026-10-25: Added Google OR-Tools (CP-SAT / pywraplp) for loan restructuring and tenure optimization — fast, exact constraint satisfaction under rule-based affordability bounds.
2026-10-24: Chose Python + Pydantic + Decimal for backend money arithmetic — avoids IEEE-754 float drift on trust scores; aligns with AGENTS.md finance rule.
2026-10-24: Chose NetworkX DiGraph for the trust graph — well-tested, supports attributed edges for capacity weights; no new abstraction needed.
2026-10-24: Chose SQLite (via stdlib) as the flat-file store for the CLI session — zero-dependency, deterministic, portable for the demo path.
2026-10-24: Chose pydantic v2 for domain models — coerces raw inputs to Decimal at the boundary, reducing validation boilerplate.
2026-10-25: Added robust unit test cases for lending service (borrow/repay/default guards), credit scoring (cold-start/rich-file/uncertainty invariants), and Web-of-Trust graph (out-degree conservation, per-path cycle absorption, visited-set invariant). All 67 tests pass.
2026-10-25: Added Google OR-Tools CP-SAT solver for constrained integer loan tenure and principal optimization; combined with deterministic counterfactual remedies, Monte Carlo stress testing dashboard, trust-graph attack simulation, audit explorer, and borrower recourse workflow. 87 tests passing.

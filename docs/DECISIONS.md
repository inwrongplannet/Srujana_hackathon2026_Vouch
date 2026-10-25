# Decisions

> PLACEHOLDER. Edit only via `/decide`. Newest first.

**Why this file exists:** a running log of what we chose and why (especially new dependencies). Stops repeat debates and doubles as pitch material.

## Log

<!-- ENTRIES -->

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

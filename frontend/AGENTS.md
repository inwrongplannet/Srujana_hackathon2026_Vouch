# frontend/ agent rules

Applies to any agent working in `frontend/` on top of the root `AGENTS.md`. Nearest file wins on conflict.

## Rules
- Build against the contract (`docs/API_CONTRACT.md`) and the generated types from `make types`; never hand-write API types. If the backend and contract disagree, stop and tell Abhishek.
- Money: never do arithmetic on JS numbers. Keep amounts as decimal strings and use a decimal library or integer minor units. Format only at render time with `Intl.NumberFormat` and the currency code from the data.
- Every screen on the demo path handles loading, empty and error states. Test the demo path from `docs/DEMO.md` in the browser, not only in unit tests.
- Show a visible "illustrative data, not financial advice" notice wherever figures come from seed data or a model.
- Read the API base URL from an env var listed in `.env.example`; no hard-coded hosts, keys or secrets in client code.
- Reuse existing components and patterns before adding new ones; no new UI library without a `/decide` entry. Keep components small, accessible (labels, keyboard focus, contrast) and responsive for a projector.
- UI changes are verified with a screenshot or a real run; say what you checked.
- Every new env var is in `.env.example` and the README Config section; user-visible behaviour is in the feature manifest.

## Domain rules
- **Dual-axis gauge**: show `mu_composite` (expected capacity) and `sigma2_epistem` (uncertainty) as two separate axes. Do NOT collapse them into a single credit score number — judges specifically look for both. Display `Score_final` (LCB) as the primary number with `mu ± kappa*sqrt(sigma2)` as a shaded band.
- **Graph visualisation**: directed edges, edge weight labels, node colour by state (ACTIVE=green, RESTRICTED=amber, DEFAULTED=red, cold-start=grey). Use a library that handles DAGs correctly (e.g. Cytoscape.js or D3-DAG). Do not use a general force-directed layout that ignores edge direction.
- **Illustrative data notice**: every screen showing figures derived from seed data must display "Illustrative data — not financial advice." This is non-negotiable.
- **What-if simulator**: re-fetch the score from `POST /simulate` on every slider change (debounce 300ms). Never recalculate on the client side — the math lives in the backend.
- **Uncertainty band**: a thin-file borrower's wide sigma2 band must be visually obvious. The band should shrink visibly as the user adds data in the what-if simulator.
- **ZK stub labelling**: any UI text that references identity anchoring must say "simulated identity anchor", never "zero-knowledge proof".

## Stack notes (filled by the scaffold-zone skill)
- Vite 8, React 19, TypeScript 6, Tailwind 4, React Router 8, Motion 14. Layout in `frontend/README.md` (Structure).
- One test: `npx vitest run src/mocks/engine/graph.test.ts`. Lint: `npm run lint` (tsc + ESLint; `src/components/bits/` is vendored and skipped).
- Types: import from `@/api/types` until `make types` produces `src/types/api.d.ts`. Data only through `@/api/client`.
- Maths lives in `src/mocks/engine/` (backend stand-in). Components format, never compute; `geom()` converts to numbers for drawing only.
- Screenshots: `?jump=<step>` replays the story (`request`, `vouch`, `apply`, `approve`, `advance`, `outcome`, `settled`, `defaulted`).

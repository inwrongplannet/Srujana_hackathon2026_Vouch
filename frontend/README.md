# frontend
VeriTrust demo app: onboarding, borrower, voucher and lender views over a mock protocol server.

## Status
- Works: landing, four-step onboarding (simulated identity anchor), borrower, voucher and lender views, contract-event ledger, demo director, `?jump=<step>` fallback.
- Mock: no backend yet. `src/mocks/` stands in for it and holds all protocol maths, copied from the graph-trust-engine, dual-axis-scoring and slashing-cascade skills.
- Missing: generated types from `make types` (the contract is still a placeholder), CI Node setup (needs Abhishek).

## Run
```bash
cd frontend
npm ci
make dev
```
Opens on `http://127.0.0.1:5173`. From the repo root, `make dev` starts it too.

## Structure
| Folder | What goes there |
|---|---|
| `src/api/` | `client.ts`, the only door to data; `types.ts`, response shapes |
| `src/mocks/` | mock server, seed data, and `engine/` (trust paths, scoring, slashing, nullifier stub, EMI) with tests |
| `src/routes/` | one file per screen |
| `src/features/` | screen-specific components (score, graph, borrower, voucher, lender, chain, demo, onboarding, landing) |
| `src/components/ui/` | shared primitives (button, badge, avatar, modal, card) |
| `src/components/icons/` | the custom SVG icon set; never emoji |
| `src/components/bits/` | React Bits components, vendored and restyled through props |
| `src/lib/format.ts` | presentation-only formatting and rounding |
| `src/styles/index.css` | Tailwind v4 theme tokens (ink on ledger paper) |

## Interfaces
- Consumes the shapes in `src/api/types.ts`, served by `src/mocks/server.ts` until the backend exists. `docs/API_CONTRACT.md` is not written yet.
- Calls a backend would serve: register, requestVouch, respondVouch, previewVouch, linkSource, applyLoan, decideLoan, settle, defaultLoan, simulate, restructure.
- Demo-only calls: advance, regionalShock, reset, jumpTo.

## Config
| Variable | Use |
|---|---|
| `VITE_DEMO_PROTOCOL_SALT` | Public test salt for the sha256 nullifier stub. Optional; a built-in public demo value is used when unset. |

The variable is read from the repo-root `.env` (`envDir: '..'`).

## Testing
```bash
cd frontend
npm test                                   # all unit tests (Vitest)
npx vitest run src/mocks/engine/graph.test.ts   # one file
npm run lint                               # tsc + ESLint
```
Tests cover every calculation with a known answer: trust paths, cycle absorption, weight conservation, mu, sigma2, the lower bound, EMI, the cascade, the circuit breaker, and the demo story end to end.

## Notes
- Money is a decimal string with an ISO 4217 code; `decimal.js` does all arithmetic and rounding happens only in `src/lib/format.ts`.
- Identity copy says "simulated identity anchor", never "zero-knowledge proof". Demo identity numbers start with `0000`, which no real Aadhaar does.
- Stack and parameter choices: `docs/DECISIONS.md`. Demo script: `docs/DEMO.md`.

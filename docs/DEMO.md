# Demo

**Why this file exists:** the demo is what gets judged. A written script and a fallback plan mean we can still present if the network, API or deploy fails.

## Script
Start the app with `make dev` and open `http://127.0.0.1:5173`. The dark presenter bar at the bottom shows the next step and the button for it. All figures are illustrative seed data.

0. Community (`/community`, as Meena): open Lakshmi (in your circle), vouch as a neighbour of 9 years and hold; her score moves as the preview said. Open Farida (a stranger): switch to "I read their file", tick the box, and see the smaller weight and bigger reward for backing a thin file. Open Suresh: his setback is posted; press Stand by and the lender line reads "4 of 4 stood by". "My ask" shows Lakshmi choosing what strangers may see.
1. Landing: the hero panel cycles three cases (hover pauses it). Lakshmi has no bureau file and the one-number lender declines her; Vouch shows four separate signals. Suresh's score fell 77 points after a shock while his endorsements held. Account 7731's twelve ring endorsements score 8, not 55. Scroll: the 451 million figure and the research cards (each linked to its source, with what it does not show) set up the problem; the counter-evidence card is why vouches are weighted, not counted. Below, tab 01 lets you toggle endorsers and watch diminishing returns; tab 02 opens the stress test on her worst month.
2. Sign-in (`/login`): pick Lakshmi (`0000 0000 4821`), any six-digit code, allow DigiLocker. The nullifier is revealed with its identity glyph: credibility 0, uncertainty 1.00.
3. Borrower: score -1.00 with a wide hatched band, limit 0 INR. Click "Ask someone who knows your work" and send to Meena.
4. Voucher (Meena): open the request. The meter re-splits from 0.93 to 0.70 per vouch; exposure is -0.35 if Lakshmi defaults, +0.10 if she repays; Lakshmi goes from 0 INR to 6,000 INR. Hold to vouch.
5. Borrower: limit 6,000 INR; the path table shows two anchor paths and an absorbed loop. Optionally link statements to watch the band narrow. Apply for 5,000 INR.
6. Lender: open Lakshmi's file. Hover a path row to light it in the graph; DSCR and both axes sit beside it. Approve.
7. Presenter bar: "Advance 30 days", then "Lakshmi repays" (credibility minted, Meena earns yield) or "Lakshmi defaults" (graph ripples: Lakshmi -1.00, Meena -0.35, three ancestors -0.25 each, Sahyog marked "hop 3, untouched").
8. "Regional shock": three Gadag farmers default at once, the breaker trips at above 30%, the third slash is queued. Click "Restructure and resume".
9. Anti-churn: "Reset", then sign in as Vinod (`0000 0000 0007`). The same nullifier resolves to his DEFAULTED record.
10. Live backend (optional; start it with `cd backend && python main.py serve --port 8000`, the green dot on "Assess" turns on): open `/app/assess`. It opens on Lakshmi asking for 1,50,000 INR over 12 months; Run assessment shows bureau (no file, unknown not bad), Vouch Score 63.5 from Ramesh and Anand, affordability (8,945 INR a month to spare) and evidence apart, and offers a restructured plan. Move the what-if sliders: with nothing moved, the scenario matches the assessment.

## Fallback plan
- No network is needed: fonts are self-hosted and the protocol runs in the browser (`frontend/src/mocks/`).
- Jump straight to any scene with `?jump=<step>`, for example `http://127.0.0.1:5173/app/lender/p_lakshmi?jump=approve`. Steps: `request`, `vouch`, `apply`, `approve`, `advance`, `outcome`, `settled`, `defaulted`.
- If the dev server fails, run `npm run build` then `npm run preview` in `frontend/` (serves `dist/` on port 4173).
- Backend on another machine: start the frontend with `VITE_API_BASE_URL=http://<host>:8000`. If the backend is down, skip step 10; every other step runs without it. A stale `backend/data/store.json` from the old ALICE and BOB seed is replaced automatically on start.

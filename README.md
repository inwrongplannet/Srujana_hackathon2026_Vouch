# <Project Name>

> PLACEHOLDER. Edit only through `/readme`, and only inside the marker sections.

<!-- BEGIN:overview -->
**Why we are building this:** TODO: one-liner on the problem and who it helps (fill at kickoff from docs/PROBLEM.md).
<!-- END:overview -->

<!-- BEGIN:quickstart -->
TODO: setup commands (verified against the Makefile).
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
| Vouching | in-progress | Reehan | See what a vouch costs you, then hold to vouch |
<!-- END:features -->

<!-- BEGIN:architecture -->
TODO: link to docs/ARCHITECTURE.md and a diagram.
<!-- END:architecture -->

<!-- BEGIN:team -->
- Abhishek: repo setup, planning, review and merge
- Reehan: builds with Claude Code
- Abhijit: feature development
<!-- END:team -->

<!-- BEGIN:demo -->
TODO: demo link and script summary.
<!-- END:demo -->

---
New to this repo? Read [docs/REPO_GUIDE.md](docs/REPO_GUIDE.md) for why every folder and file exists.

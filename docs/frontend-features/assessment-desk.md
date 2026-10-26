<!-- Why: a tiny, uniform record per feature that tooling can read. -->
# Feature: Assessment desk
- **Assignee:** Reehan
- **Status:** in-progress
- **One-liner:** The first screen on the real FastAPI backend (`/app/assess`): pick a backend applicant, run the assessment, and see bureau, Vouch Score, affordability and evidence apart, with the best plan, a stress test, cited reasons and what-if sliders re-checked by `/scenarios`; beside it the predictive model's view (`/predict`: decision with a 90% conformal set, default probability, reasons, missing evidence, remedy); then the lender approves or declines (`/decision`), which puts a real loan on the book; when the backend is down or a call fails it shows a recorded run of the same backend (`src/mocks/deskRecorded.ts`) under a demo-data badge instead of an error

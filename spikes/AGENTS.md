# Spikes

Applies to any AI agent working inside `spikes/` (in addition to the root `AGENTS.md`). A spike's job is to explore fast, so rules here are looser than in the rest of the repo, with one exception: findings must be written down.

## Looser rules (inside `spikes/<name>/` only)
- Messy code is fine. No tests, lint or type requirements, no contract adherence.
- Hard-coded values and throwaway scripts are fine. Still never commit secrets or real personal data.
- Dependencies may be installed freely inside the spike folder, but do not touch root-level or other folders' dependency files.

## Hard rules
- Work only in `spikes/<name>/` on a `spike/<name>` branch. Do not edit backend/, frontend/, docs/ or any other folder.
- Time-box: write the box at the top of the spike README (default 90 minutes). When it is up, stop and report, even if unfinished.
- Every spike has a `README.md` from `docs/templates/spike-readme.md` with a real Question, Findings, How to integrate and Promotion checklist. A spike without findings is not done.
- Promotion into `backend/` or `frontend/` is not done here. The spike author lists the promotion checklist; whoever the task is assigned to re-implements or ports it via a task in `docs/TASKS.md` and a normal PR.
- The spike README is the documentation: `make docs` fails when a spike's code changes without its README.
- Use the `spike` skill to run a spike.

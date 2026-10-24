# Copilot instructions

The full, authoritative instructions for every AI agent in this repo are in `/AGENTS.md`, with zone rules in `backend/AGENTS.md`, `frontend/AGENTS.md` and `spikes/AGENTS.md`. Read them first. The essentials:

- Stay inside the task's listed files; nobody owns a folder. Never push to `main`; use a branch and a PR.
- Docs ship with the code: update the docs named in the map in `AGENTS.md` in the same PR, and update `AGENTS.md` when a command, convention or structure changes. Follow `docs/STYLE.md`.
- Money is never a float: use Decimal or integer minor units, with a currency code. Do not invent finance formulas; see `.claude/skills/finance-domain/SKILL.md`.
- Never read, print or commit `.env`. Demo data is fake and deterministic (`make seed`).
- Run `make check` before finishing and report the result honestly. Log new dependencies in `docs/DECISIONS.md`.

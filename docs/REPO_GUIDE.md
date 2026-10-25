# Repo Guide: why everything is here

## Why this repo is structured this way
We are three people with different jobs and one Claude Code seat (Reehan's), working
under a hackathon clock. The structure exists to solve four problems:

1. **Collisions.** Three people editing the same files at 3am causes conflicts.
   Fix: small tasks that list their files, one branch per task, and no two in-progress tasks touching the same file.
2. **Bottlenecks.** Reehan's Claude Code usage and Abhishek's review time are
   the scarce resources. Fix: precise tasks, an automated PR review, and an
   automated fixer for trivial issues.
3. **Drift.** README, tasks and decisions rot when anyone edits them freely.
   Fix: one sanctioned way to change each (single-writer docs).
4. **Demo risk.** A broken demo loses everything. Fix: seed data, a demo
   checklist, a fallback plan, and CI on every PR.

Principle: the *process* must work without Claude (CONTRIBUTING.md, PR
template, CI). Claude skills only *automate* it.

## Team and zones
| Person | Does | Tools |
|---|---|---|
| Abhishek | Sets up the repo, plans tasks, reviews and merges | any agent |
| Reehan | Builds features and the user-facing side | Claude Code |
| Abhijit | Feature development | any agent |

A zone is a top-level folder with its own `AGENTS.md` (`backend/`, `frontend/`, `spikes/`). Nobody owns a zone: work is assigned per task, and a task's Files touched is its scope.

## Map
| Path | Why it exists | Filled in |
|---|---|---|
| `AGENTS.md` | Single source of rules for every AI agent (Claude, OpenCode, Codex, Cursor, Copilot, Gemini); `backend/`, `frontend/` and `spikes/` have their own | Before event, zone files finished after scaffolding |
| `.gemini/` | Makes Gemini CLI read `AGENTS.md` | Done |
| `docs/STYLE.md` | Canonical terms, naming and README structure (enforced by `make docs`) | Done |
| `docs/KICKSTART.md` | First-hour runbook, timeline and starter prompts | Done |
| `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` | Thin pointers so each tool finds `AGENTS.md`; tool-specific notes only | Done |
| `README.md` | Judges' first impression; marker sections keep it controlled | Overview at kickoff, rest ongoing via `/readme` |
| `CONTRIBUTING.md` | Claude-free copy of the team rules | Before event |
| `Makefile` | One command vocabulary (dev/test/check/seed/types) | Wired up when backend/frontend exist |
| `.env.example` | Documents required keys, no secrets | As keys are added |
| `.gitignore` | Keeps secrets and junk out of git | Done |
| `.github/CODEOWNERS` | Requests Abhishek's review on every PR | Before event (real username) |
| `.github/pull_request_template.md` | Same checklist on every PR | Done |
| `.github/workflows/check.yml` | Automatic gate on every PR | Wire up with scaffolding |
| `opencode.json`, `.opencode/` | OpenCode permissions, plus thin command/agent wrappers that point at `.claude/` so there is one source of truth | Done |
| `.claude/settings.json` | Pre-approved safe commands, blocks reading `.env` | Done; add hooks later |
| `.claude/commands/` | Slash-command shortcuts for repeated team actions | Before event |
| `.claude/agents/` | Reviewer and researcher subagents with clean context | Before event |
| `.claude/skills/` | Reusable how-to instructions Claude loads on demand | Before event; add problem-specific ones at kickoff |
| `docs/PROBLEM.md` | Single source of truth for the PS and judging criteria | At kickoff |
| `docs/IDEA.md` | Initial abstract technical design: web-of-trust graph, dual-axis scoring, ZK identity, slashing dynamics, hackathon scope reductions | At kickoff |
| `docs/ARCHITECTURE.md` | The agreed technical plan | At kickoff via `/kickoff` |
| `docs/API_CONTRACT.md` | Lets frontend and backend be built in parallel | At kickoff, then ongoing |
| `docs/FRONTEND_GUIDE.md` | Capabilities, data requirements, screen mappings, and request guidelines for the frontend | Ongoing |
| `docs/SYSTEM_GUIDE.md` | Plain-language guide to models, formulas, complex interactions, and empirical benchmarks | Done |
| `docs/TASKS.md` | Task board; how work is assigned | Via `/task` |
| `docs/DECISIONS.md` | Log of choices and dependencies; pitch material | Via `/decide` |
| `docs/OR_TOOLS_AND_MONTE_CARLO.md` | Technical rationale for OR-Tools optimization and Monte Carlo stress testing | Ongoing |
| `docs/DEMO.md` | Demo script and fallback plan | Mid-event, finalized in last 20% |
| `docs/frontend-features/` | One manifest per feature; feeds README table and `/status` | As features start |
| `docs/templates/` | Fixed formats for tasks, spike write-ups, feature manifests | Before event |
| `backend/` | API and finance logic, scaffolded by whoever the task is assigned to | Event day |
| `backend/ml/` | Explainable ML models (EBM, XGBoost GPU, PyTorch GPU), conformal prediction sets, noise generator and ablation engine | Done |
| `backend/localdocs/Implementation_Doc.md` | Master implementation roadmap, stages 1-9, code organization and production verification | Done |
| `backend/localdocs/BENCHMARKS_AND_METRICS.md` | Consolidated empirical benchmark evaluation, model metrics, ablation findings, and conformal coverage | Done |
| `backend/localdocs/VOUCH_DEVELOPER_MASTER_V2.md` | Master developer specification v2: architecture, graph math, scenarios, and acceptance criteria | Done |
| `backend/localdocs/FORMULAS_AND_NUMBERS.md` | Master mathematical specification: formulas, processes, constants, and calibration numbers | Done |
| `backend/localdocs/TEMPORAL_UNCERTAINTY_AND_FRESHNESS.md` | Temporal uncertainty decay model: confidence half-lives, epistemic inflation, and LCB limit derivation | Done |
| `backend/localdocs/PROSPER_AND_LITERATURE_LESSONS.md` | Empirical analysis of 55k Prosper loans, cheap-talk failure modes, and literature synthesis | Done |
| `frontend/` | User-facing app, scaffolded by whoever the task is assigned to | Event day |
| `spikes/` | Sandbox for experiments; messy is fine, findings must be written | During event |
| `data/` | Small sample and seed files | During event |
| `scripts/` | Automation behind the Makefile and skills, including the docs and agent-file gates and the pre-push hook in `scripts/hooks/` | Before/during event |

## How work flows
1. Kickoff: paste the PS into `docs/PROBLEM.md`, run `/kickoff`, trim the plan.
2. Abhishek writes the contract and tasks (`/task`).
3. Reehan and Abhijit build their assigned tasks; spikes explore unknowns in `spikes/`.
4. Everyone opens PRs. Abhishek runs `/review-pr`, then `/fix-pr` or comments, then merges.
5. Feature freeze at about 70% of the time. Last 20%: demo polish, deploy, pitch.

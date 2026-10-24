# Kickstart

**Why this file exists:** the fastest path from "clone" to "everyone, human and agent, building the right thing". Read it once before the event and once at kickoff.

## Before the event (once per person, about 15 minutes)
1. Clone the repo and run `make hooks` (installs the pre-push docs gate).
2. Copy `.env.example` to `.env` and fill the keys (never commit it).
3. Run `make check`. It must pass on a fresh clone; fix it now, not at 3am.
4. Open your agent in the repo: Claude Code, OpenCode or another. It must read `AGENTS.md` (ask it "what are the boundaries here?" to confirm).
5. Abhishek only: replace the username in `.github/CODEOWNERS`, enable branch protection on `main` with the `check` job required.

## First hour (kickoff)
| Minutes | Who | Do |
|---|---|---|
| 0-15 | Abhishek | Paste the problem statement and judging criteria into `docs/PROBLEM.md`. |
| 15-45 | Abhishek | Run `/kickoff`. Trim the plan; accept only what serves the core flow. |
| 15-45 | Abhijit | Start the riskiest unknown as a spike (`spike` skill). Time-box it. |
| 45-90 | Abhishek | Agree the contract (`api-contract` skill), then scaffold `backend/` (`scaffold-zone` skill). Write the first tasks with `/task`. |
| 45-90 | Reehan | Scaffold `frontend/` (`scaffold-zone` skill), wire `make types`, start the first task against the contract. |
| 90 | Everyone | First PR merged. From here every change is a task, a branch and a PR. |

## Timeline by percentage of the clock
| Clock | 24h event | 48h event | Goal |
|---|---|---|---|
| 0-5% | 0:00-1:15 | 0:00-2:30 | Plan agreed, tasks written |
| 5-10% | until 2:30 | until 5:00 | Skeletons run, contract agreed, seed data works |
| 10-70% | until 17:00 | until 34:00 | Build features on the demo path first |
| 70% | 17:00 | 34:00 | Feature freeze: only fixes, docs and polish |
| 70-90% | until 21:30 | until 43:00 | Demo polish, `/demo-check`, docs and README final, deploy |
| 90-100% | last 2h | last 5h | Pitch rehearsal, recording as fallback, no new code |

## Daily rhythm
- Every 2 hours Abhishek runs `/status`, clears the PR queue (`/review-pr`, `/fix-pr`) and updates tasks.
- Reehan and Abhijit start each task with `/start <your name>` in a fresh agent session and end it with `/finish`.
- Open PRs small (under about 300 changed lines) so review takes minutes.
- Stuck for 30 minutes: stop, write down what you tried, ask. Do not burn the clock or the Claude Code budget.

## Who uses which agent
| Work | Good fit |
|---|---|
| Cross-cutting design, contract, tricky finance logic, PR review | Strongest model (Claude Code, Reehan's seat) |
| Small, exactly specified tasks (a component, an endpoint, a test, docs) | Free or smaller models via OpenCode; set `Agent:` in the task |
| Research and library comparison | `researcher` subagent |

## Starter prompts
Use these as the first message of a session.

- Claude Code or OpenCode: `/start reehan` (or `abhishek`, `abhijit`).
- Any other agent: `Read AGENTS.md, the AGENTS.md of the folders your task touches, and docs/TASKS.md. Take the next task assigned to <your name> and follow the session protocol in AGENTS.md. Do not start coding until you have restated the acceptance criteria.`
- To finish: `/finish`, or "Meet the Definition of Done in AGENTS.md and give me the handoff summary."

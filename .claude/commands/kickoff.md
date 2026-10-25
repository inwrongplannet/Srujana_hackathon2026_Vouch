---
description: Read docs/PROBLEM.md and produce architecture, API contract and tasks split by teammate
---
# /kickoff

**Why this exists:** The first hours decide the hackathon, and this turns the PS into a plan in minutes so nobody codes in different directions
**Used by:** Abhishek, once, right after the PS

Extra input from the user (optional): $ARGUMENTS

1. Read `docs/PROBLEM.md`. If the PS, judging criteria or core flow are still `TODO`, ask the user for them first and fill that file in (Abhishek may edit it directly). Do not guess.
2. Read `AGENTS.md`, `docs/REPO_GUIDE.md` and `docs/templates/task.md`.
3. Propose, as a concise draft and wait for the user's go-ahead before writing files:
   - **Architecture**: the smallest stack that serves the core flow and judging criteria, with a text/mermaid diagram. Prefer boring, familiar tech. Flag anything that is a demo risk.
   - **API contract**: only the endpoints the core flow needs, with request/response shapes.
   - **Feature list**: 3-6 features max, each tagged must-have / nice-to-have, one-liners suitable for `docs/frontend-features/<feature>.md`.
   - **Task split by teammate**: Abhishek (contract, backend, seed data), Reehan (frontend, in dependency order), Abhijit (features and risky-unknown spikes first). Nobody owns a folder; give each task its Files touched and an Assignee, and keep two tasks off the same file. Each task sized for one agent session.
   - **Cut line**: what we drop first if time runs short (feature freeze at ~70% of the time).
4. After approval: write `docs/ARCHITECTURE.md` and `docs/API_CONTRACT.md`, create `docs/frontend-features/<feature>.md` from the template, append the tasks with the `task-writer` skill, and log the stack choice with the `decision-log` skill.
5. Finish by listing remaining open questions and what Reehan and Abhijit should start on first.

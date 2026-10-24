---
name: session-protocol
description: Start, work and finish an agent session at hackathon pace - sync, read the task, plan, small verified steps, Definition of Done and a five-line handoff
---
# session-protocol

**Why this exists:** the clock is the scarcest resource. A fixed start and finish routine gets an agent productive in the first minute and makes every session end in a mergeable PR with true docs.
**Used by:** Everyone, every session
**Triggered by:** `/start`, `/finish`

## When to use
At the start of every session (`/start <your name>`) and when you believe the task is done (`/finish`).

## Start (target: under 2 minutes)
1. Identify yourself: your first name is the argument (`abhishek`, `reehan` or `abhijit`), or a `TASK-NNN` id. Read root `AGENTS.md` and the `AGENTS.md` of every folder your task touches.
2. Sync: `git fetch`, then create `feat/<task-id>-<name>` (or `fix/`, `docs/`, `spike/`) from fresh `origin/main`. If a branch for your task exists, switch to it and rebase.
3. Read your next task in `docs/TASKS.md` (Assignee is you; Backlog or In progress) and every file it names. Check that no other In progress task lists the same files. No task? Say so and ask Abhishek; do not invent scope.
4. Baseline: run `make check`. Note failures that existed before you touched anything.
5. Restate the acceptance criteria in your own words in at most 5 lines, plus the docs the task must update. For multi-file or uncertain changes add a plan of at most 5 steps. Proceed unless something is ambiguous; ask one precise question when it is.

## Work
- Small steps; run the narrowest check after each (one test, one lint). Commit each working step as `<type>(<zone>): <summary>`.
- Follow existing patterns: find the nearest similar file first. Add nothing the task did not ask for.
- Keep docs moving with the code (`docs-sync` skill) instead of leaving them to the end.
- Context hygiene: one task per session. Start a fresh session (`/clear` in Claude Code, a new session elsewhere) for unrelated work, and push research into a subagent.

## Stuck rules
- The same check fails 3 times, or 30 minutes pass with no progress: stop. Write what you tried and the exact error, then ask.
- Corrected twice on the same point: restart the session with a sharper prompt that includes what you learned.

## Finish: Definition of Done
1. Each acceptance criterion is met and demonstrated (command and output).
2. `make check` is green.
3. `docs-sync` done: docs updated or a justified `Docs-Impact: none (<reason>)`; `AGENTS.md` updated if conventions changed.
4. New dependency logged; feature manifest status updated and `make readme` run.
5. `git diff --stat` reviewed: no debug code, secrets or files the task does not list.
6. PR opened with the template filled (skill: `branch-and-commit`).

## Handoff (at most 5 lines, in the PR description and your final message)
What changed; how it was verified (commands and results); docs updated; open questions or follow-up tasks; anything that could break the demo path.

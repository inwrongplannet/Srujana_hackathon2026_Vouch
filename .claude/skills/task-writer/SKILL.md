---
name: task-writer
description: Append Claude-ready tasks to docs/TASKS.md using the template
---
# task-writer

**Why this exists:** Clear specs (goal, files, acceptance criteria) are the biggest lever for fast, correct output from any teammate's agent
**Used by:** Abhishek
**Triggered by:** `/task`

## When to use
Delegating work. Each task must be executable by a fresh Claude session with no extra conversation.

## Steps
1. Read `docs/templates/task.md`, `docs/TASKS.md` (next free id, existing tasks, avoid duplicates) and `docs/API_CONTRACT.md`.
2. Fill every field of the template:
   - **Assignee**: Abhishek, Reehan or Abhijit. Check In progress tasks so the person is not overloaded.
   - **Agent**: who executes it (`claude`, `opencode:<model>`, or `any`). Give free or smaller models the well-specified, low-risk work; keep the tricky, cross-cutting tasks for the strongest model.
   - **Goal**: one or two sentences describing the user-visible outcome, not the implementation.
   - **Files touched**: real paths, and none that another In progress task already lists (two tasks must never edit the same file at once). Split a task that touches many unrelated files.
   - **Endpoint shape**: the exact method, path, request and response from the contract (or "n/a"). Add it to the contract first if missing.
   - **Docs to update**: the exact docs from the map in `AGENTS.md` that this task must change (zone README section, feature manifest, `.env.example`, ...). Always include them in the acceptance criteria.
   - **Acceptance criteria**: 3-6 checkable bullets, including `make check` passing and any demo-path behavior. Add edge cases for finance logic (zero, negative, rounding, currency).
3. Size it for one agent session (about an hour or less). For a free or smaller model make it smaller still: at most ~3 files, exact function or endpoint signatures, an example input and expected output, and no open design choices. Split anything bigger, and note dependencies on other task ids.
4. Append under `## Backlog` in `docs/TASKS.md` with the next `TASK-NNN` id. Only this skill/command edits TASKS.md; to move a task to In progress or Done, move its block between the headings and keep the text intact.
5. Show the final task text to the user.

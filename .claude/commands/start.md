---
description: Start a session fast - sync, read the task, baseline check, restate acceptance criteria
---
# /start

**Why this exists:** gets an agent productive in the first minute with the same routine every time, so no session starts by guessing.
**Used by:** Everyone, first message of every session

Your name (abhishek, reehan, abhijit) or a task id (TASK-NNN): $ARGUMENTS

Follow the Start section of the `session-protocol` skill: read root `AGENTS.md` and the `AGENTS.md` of the folders your task touches, create the branch from fresh `origin/main`, read the task in `docs/TASKS.md` and the files it names, run `make check` for a baseline, then restate the acceptance criteria and the docs to update in at most 5 lines. Ask one precise question only if something is ambiguous; otherwise begin.

---
description: Append a task to docs/TASKS.md using the template
---
# /task

**Why this exists:** Claude Code usage and review time are the bottleneck, so precise tasks stop it being wasted on guesswork
**Used by:** Abhishek

Task request: $ARGUMENTS

Follow the `task-writer` skill. In short: turn the request into a task using `docs/templates/task.md`, ground the files and endpoint shape in the real repo and `docs/API_CONTRACT.md`, assign the next `TASK-NNN` id, append it under Backlog in `docs/TASKS.md`, and show the user the final text. If the request is too vague to write testable acceptance criteria, ask one or two specific questions first.

---
description: Finish a task - Definition of Done, docs sync, make check, PR and handoff summary
---
# /finish

**Why this exists:** no task is done until it is verified, documented and reviewable; this runs the whole Definition of Done in one go.
**Used by:** Everyone, last message of a task

Notes (optional): $ARGUMENTS

Follow the Finish section of the `session-protocol` skill. In order: run the `docs-sync` skill, run `make readme` if a feature manifest changed, run `make check` and fix failures, review `git diff --stat`, then commit and open the PR with the `branch-and-commit` skill. End with the five-line handoff. Never report success on a red check, and say plainly anything you could not verify.

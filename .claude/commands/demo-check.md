---
description: Run seed, tests and a smoke test of the demo path
---
# /demo-check

**Why this exists:** A broken demo loses hackathons, so this is the pre-demo safety net
**Used by:** Abhishek, final stretch

Optional focus: $ARGUMENTS

Pre-demo safety net. Run in order, stop and report at the first failure with the exact error:
1. `make seed`, then run it a second time and confirm the data is identical (determinism).
2. `make check` (lint + tests).
3. Start the app with `make dev` (in the background) and smoke-test every step of the script in `docs/DEMO.md` against the running app, hitting real endpoints/pages rather than assuming they work.
4. Confirm the demo path works with no network access to third-party APIs (or that a fallback is wired up), and that no secrets or `TODO` / placeholder text are visible in the UI or README.
5. Stop the dev server and print a pass/fail checklist plus anything the fallback plan in `docs/DEMO.md` should cover.

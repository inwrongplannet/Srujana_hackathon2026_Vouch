---
name: spike
description: Workflow for prototyping in `spikes/<name>/` with a time-box and README findings
---
# spike

**Why this exists:** Lets anyone experiment without risking main, and the time-box stops a research rabbit hole
**Used by:** Abhijit
**Triggered by:** Starting any experiment

## When to use
Exploring an unknown: a data source, API, model, algorithm or library, before the team commits to it.

## Steps
1. **Frame it.** Agree one concrete question ("Can we get daily FX rates for 30 currencies free, without a key?") and a time-box (default 90 minutes). Create branch `spike/<name>` and folder `spikes/<name>/`.
2. **Write the README first** from `docs/templates/spike-readme.md`: Time-box and Question filled in, other fields left TODO.
3. **Explore fast.** Work only inside `spikes/<name>/`. Messy is fine. Keep secrets out of git; use `.env` and note the needed key names.
4. **Check the clock** at the half-way point and at the end. If the time-box runs out, stop and write up what you have.
5. **Finish the README**, which is mandatory: Findings (what works, what does not, with numbers: latency, limits, accuracy), How to integrate (the minimal code path and files), Promotion checklist (what must change before it can live in `backend/` or `frontend/`: tests, error handling, Decimal money, contract entry, dependency decision via `/decide`), and a clear **go / no-go / needs-more** recommendation.
6. Open a PR (see `branch-and-commit`). Do not move code into other folders: Abhishek turns the promotion checklist into a task.

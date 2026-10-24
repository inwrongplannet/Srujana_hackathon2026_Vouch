---
name: pitch-and-demo
description: Demo script structure, pitch outline and fallback plan
---
# pitch-and-demo

**Why this exists:** Hackathons are won on the demo and pitch, so reserving structure and time early avoids a last-minute scramble
**Used by:** Abhishek
**Triggered by:** Final 20% of the event

## When to use
Once features are frozen (about 70% of the time) and for writing `docs/DEMO.md`; also as the demo check before presenting.

## Pitch outline (aim ~3-5 minutes, check the event's limit)
1. **Hook (20s)**: one concrete person with one concrete pain, with a number if you have one.
2. **Problem (30s)**: why existing options fail. Use the language of the judging criteria in `docs/PROBLEM.md`.
3. **Live demo (90-120s)**: the happy path only, following the script below.
4. **How it works (30s)**: one architecture diagram, one sentence on what is technically hard or clever, sponsor tech named.
5. **Impact and market (20s)**: who benefits, size, why now, and a credible business model.
6. **What is next + ask (20s)**: roadmap in one line, what we want from judges.
Map each judging criterion to a specific moment in the pitch and tick them off.

## Demo script (write into `docs/DEMO.md`)
- Numbered steps, each: action, what the audience sees, the line to say, approximate seconds. Rehearse with a timer at least twice; cut steps instead of rushing.
- Use only seeded data (`make seed`); open with the app already running and logged in. State the illustrative-data disclaimer once.
- Assign roles: who drives, who talks, who watches the clock.

## Fallback plan (write into `docs/DEMO.md`)
- Pre-recorded 90-second screen recording of the full path, on the presenter's desktop and a USB stick.
- Local run that works offline; screenshots of each step as slides; backup hotspot or wired network; second laptop with the same build.
- Deployed URL tested from a different network the same day. Decide the trigger ("if the live step has not loaded in 5 seconds, switch to the recording") and who calls it.
- Run `/demo-check` at feature freeze, again two hours before, and 30 minutes before presenting.

## Prep checklist
README (judges open it first), repo public or accessible if required, no TODO/placeholder text visible, slide deck or none (decide), Q&A prep for the hardest 5 questions (data source, accuracy, compliance, scale, why not incumbents).

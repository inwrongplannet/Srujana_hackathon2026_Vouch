---
name: llm-guardrails
description: Rules for LLM-powered finance features: grounding, no invented numbers, disclaimers, cost and failure handling
---
# llm-guardrails

**Why this exists:** A model that confidently invents a figure or gives advice is the fastest way to lose a finance demo; one checklist keeps AI features honest and demo-safe
**Used by:** Everyone building AI features
**Triggered by:** Any feature that calls an LLM

## When to use
Building or reviewing any feature that sends data to an LLM or shows model output to a user (summaries, categorization, chat, explanations).

## Rules
1. **Numbers come from code, not the model.** Compute every amount, rate and metric with deterministic code (see `finance-domain`) and pass the results to the model as facts to explain. Never let the model do arithmetic or invent a figure. Validate any figure in the output against the inputs when feasible.
2. **Ground it.** Provide the relevant data in the prompt, tell the model to use only that, and to say "not enough information" otherwise. Ask for structured output (JSON schema) for anything the UI parses, and validate it; retry once, then fall back.
3. **No advice.** Output explains and informs; it does not recommend buying, selling or lending decisions. Show a short "illustrative, not financial advice" notice in the UI.
4. **Data hygiene.** Only send what is needed; never send real personal data or secrets. The demo uses seeded fake data only. API keys come from `.env` (`ANTHROPIC_API_KEY`), never from code or the browser; call the model from the backend.
5. **Demo safety.** Set timeouts and a token cap, handle rate limits and errors, and have a deterministic fallback (a canned or cached response for the demo path) so a network or API failure does not break the script in `docs/DEMO.md`. Cache the demo-path responses.
6. **Cost control.** Use the smallest model that does the job, keep prompts short, and note per-call cost in the feature manifest or `/decide` entry if it is meaningful. Avoid loops that call the model per row; batch instead.
7. **Test it.** Keep a handful of fixed prompts with expected properties (contains the right number, valid JSON, refuses to give advice) and run them before the demo. Log the model id and prompt version in `docs/DECISIONS.md` when it changes.
8. For current model ids, parameters or SDK usage, use the `claude-api` skill or the official docs rather than memory.

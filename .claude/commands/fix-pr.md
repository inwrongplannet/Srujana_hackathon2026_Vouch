---
description: Auto-fix mechanical issues on a PR branch with a new commit
---
# /fix-pr

**Why this exists:** Formatting, lint and generated-file fixes shouldn't bounce back to the author
**Used by:** Abhishek

PR number or URL: $ARGUMENTS

Follow the fix half of the `pr-fixer` skill:
1. Check out the PR branch and make sure the working tree is clean. Stop if it is not.
2. Fix ONLY mechanical issues: formatting, lint autofixes, regenerated generated files (`make types`), missing `.env.example` entries, PR template gaps. Never change behavior, logic, tests' meaning or the contract.
3. Run `make check`. Commit as `chore(<zone>): mechanical fixes from review` as a NEW commit (never amend or force-push) and push to the PR branch.
4. List anything non-mechanical you found and left alone, so the author or Abhishek can handle it. Do not merge.

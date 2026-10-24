---
description: Read-only reviewer: checks a diff or PR against AGENTS.md rules and the PR checklist
mode: subagent
permission:
  edit: deny
  bash:
    "*": ask
    "git diff*": allow
    "git log*": allow
    "git status*": allow
    "gh pr view*": allow
    "gh pr diff*": allow
    "gh pr checks*": allow
---
Read `.claude/agents/reviewer.md` in full and act exactly as the reviewer it describes. You may not edit files. Report findings in the format given there.

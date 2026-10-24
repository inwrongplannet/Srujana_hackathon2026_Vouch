#!/usr/bin/env python3
"""Fails when the agent instruction files drift from the repo.

Checks: size budgets, pointer files, Makefile targets vs AGENTS.md, the skills/commands table,
skill/command/agent frontmatter, OpenCode wrappers, and that REPO_GUIDE.md maps every top-level path.
"""
import json
import re
import sys

from _common import ROOT, project_files

ROOT_MAX, ZONE_MAX, POINTER_ROOT_MAX, POINTER_ZONE_MAX = 150, 80, 40, 12
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REPO_GUIDE_EXEMPT = {".gitattributes"}
errors: list[str] = []


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def frontmatter(rel: str) -> dict[str, str] | None:
    m = re.match(r"---\n(.*?)\n---\n", read(rel), re.S)
    if not m:
        return None
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in m.group(1).splitlines()) if _}


def check_sizes_and_pointers(files: list[str]) -> None:
    agents = [p for p in files if p.endswith("AGENTS.md")]
    if "AGENTS.md" not in agents:
        errors.append("AGENTS.md is missing")
        return
    for rel in agents:
        n = len(read(rel).splitlines())
        limit = ROOT_MAX if rel == "AGENTS.md" else ZONE_MAX
        if n > limit:
            errors.append(f"{rel} has {n} lines (budget {limit}); prune before adding")
        folder = rel[: -len("AGENTS.md")]
        pointer = f"{folder}CLAUDE.md"
        if not (ROOT / pointer).is_file():
            errors.append(f"{rel} needs a sibling {pointer} containing '@AGENTS.md'")
            continue
        text = read(pointer)
        cap = POINTER_ROOT_MAX if rel == "AGENTS.md" else POINTER_ZONE_MAX
        if "@AGENTS.md" not in text or len(text.splitlines()) > cap:
            errors.append(f"{pointer} must import '@AGENTS.md' and stay under {cap} lines (no rules here)")
    for zone in ("backend", "frontend", "spikes"):
        if f"{zone}/AGENTS.md" not in agents:
            errors.append(f"{zone}/AGENTS.md is missing")
    if "@AGENTS.md" not in read("GEMINI.md"):
        errors.append("GEMINI.md must import '@AGENTS.md'")
    try:
        names = json.loads(read(".gemini/settings.json"))["context"]["fileName"]
        if "AGENTS.md" not in names:
            errors.append(".gemini/settings.json context.fileName must include AGENTS.md")
    except (OSError, KeyError, json.JSONDecodeError):
        errors.append(".gemini/settings.json must set context.fileName to include AGENTS.md")
    if "AGENTS.md" not in read(".github/copilot-instructions.md"):
        errors.append(".github/copilot-instructions.md must point to AGENTS.md")


def check_make_targets() -> None:
    phony = {t for line in re.findall(r"^\.PHONY:(.*)$", read("Makefile"), re.M) for t in line.split()}
    text = read("AGENTS.md")
    mentioned = set(re.findall(r"`make ([a-z][a-z-]*)", text)) | set(re.findall(r"^make ([a-z][a-z-]*)", text, re.M))
    for target in sorted(phony - mentioned):
        errors.append(f"Makefile target '{target}' is not documented in AGENTS.md (Commands)")
    for target in sorted(mentioned - phony):
        errors.append(f"AGENTS.md mentions 'make {target}' but the Makefile has no such target")


def listing(folder: str, suffix: str = ".md") -> set[str]:
    return {p.rsplit("/", 1)[-1][: -len(suffix)] for p in project_files(suffix) if p.startswith(folder + "/") and p.count("/") == folder.count("/") + 1}


def check_skills_commands_agents() -> None:
    text = read("AGENTS.md")
    skills = sorted({p.split("/")[2] for p in project_files("SKILL.md") if p.startswith(".claude/skills/")})
    for name in skills:
        fm = frontmatter(f".claude/skills/{name}/SKILL.md")
        if not fm or fm.get("name") != name or not KEBAB.match(name) or len(name) > 64:
            errors.append(f".claude/skills/{name}/SKILL.md: frontmatter name must equal the kebab-case folder name")
        elif not 1 <= len(fm.get("description", "")) <= 1024:
            errors.append(f".claude/skills/{name}/SKILL.md: description must be 1-1024 characters")
        if not re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text):
            errors.append(f"skill '{name}' is not listed in AGENTS.md (Skills and commands table)")
    commands, agents = listing(".claude/commands"), listing(".claude/agents")
    for kind, names in (("commands", commands), ("agents", agents)):
        for name in sorted(names):
            fm = frontmatter(f".claude/{kind}/{name}.md")
            if not fm or not fm.get("description"):
                errors.append(f".claude/{kind}/{name}.md: needs a 'description:' in its frontmatter")
        wrappers = listing(f".opencode/{kind}")
        for name in sorted(names - wrappers):
            errors.append(f".opencode/{kind}/{name}.md wrapper is missing (OpenCode cannot read .claude/{kind}/)")
        for name in sorted(wrappers - names):
            errors.append(f".opencode/{kind}/{name}.md has no matching .claude/{kind}/{name}.md")
    for name in sorted(commands):
        if f"/{name}" not in text:
            errors.append(f"command /{name} is not listed in AGENTS.md (Skills and commands table)")
    for name in sorted(agents):
        if f".claude/agents/{name}.md" not in text and name not in text:
            errors.append(f"agent '{name}' is not mentioned in AGENTS.md")
    for row in re.findall(r"^\|(.+)\|$", text, re.M):
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 3 and cells[1].startswith("commands/") and not (ROOT / ".claude" / cells[1]).is_file():
            errors.append(f"AGENTS.md table points to missing {cells[1]}")
        if len(cells) >= 3 and cells[1] not in ("-", "Skill") and not cells[1].startswith(("commands/", "-")) and cells[1] != "Skill" and not set(cells[1]) <= set("-"):
            if cells[1] not in skills and cells[0] != "Situation":
                errors.append(f"AGENTS.md table lists unknown skill '{cells[1]}'")


def check_repo_guide() -> None:
    guide = read("docs/REPO_GUIDE.md")
    for top in sorted({p.split("/")[0] for p in project_files()}):
        if top not in REPO_GUIDE_EXEMPT and top not in guide:
            errors.append(f"top-level path '{top}' is not in the docs/REPO_GUIDE.md map")


def main() -> int:
    files = project_files()
    check_sizes_and_pointers(files)
    if "AGENTS.md" in files:
        check_make_targets()
        check_skills_commands_agents()
    check_repo_guide()
    if errors:
        print("agent files check FAILED:", file=sys.stderr)
        print("\n".join(f"  - {e}" for e in errors), file=sys.stderr)
        return 1
    print("agent files check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

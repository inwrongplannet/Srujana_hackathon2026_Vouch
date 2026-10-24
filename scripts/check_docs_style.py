#!/usr/bin/env python3
"""Markdown style and nomenclature gate (rules in docs/STYLE.md).

Checks every project .md file (except docs/templates/ and the PR template): one H1 first, no skipped
heading levels, fenced code has a language, relative links resolve, canonical terms, file naming.
Also checks that backend/ and frontend/ READMEs follow docs/templates/zone-readme.md and that
spike READMEs carry the spike template fields.
"""
import re
import sys
from pathlib import Path

from _common import ROOT, project_files

SKIP_PREFIXES = ("docs/templates/", ".claude/skills/")  # skill files are agent instructions, not project docs
SKIP_FILES = {".github/pull_request_template.md"}
SKIP_TERMS = {"docs/STYLE.md"}  # documents the banned terms on purpose
NO_H1_PREFIXES = (".opencode/",)  # thin wrappers: frontmatter plus a few lines
ZONES = ("backend", "frontend")
KEBAB_MD = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
UPPER_MD = re.compile(r"^[A-Z][A-Z0-9_]*\.md$")
BANNED = [
    (r"\bGithub\b", "GitHub"),
    (r"\bLead\b", "Abhishek"),
    (r"\bCoder\b", "Reehan"),
    (r"\bBuilder\b", "Abhijit"),
    (r"\b(Readme|ReadMe)\b", "README"),
    (r"\b(Opencode|Open Code)\b", "OpenCode"),
    (r"\bClaude code\b", "Claude Code"),
    (r"\bPull Requests?\b", "pull request"),
    (r"\b[Tt]ickets?\b", "task"),
    (r"\b[Pp]laybooks?\b", "skill"),
    (r"\b[Ss]ub-agents?\b", "subagent"),
    (r"\b(Agent\.md|Agents\.md|AGENT\.md)\b", "AGENTS.md"),
    (r"\b(Claude\.md|claude\.md)\b", "CLAUDE.md"),
]
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)")


def parse(text: str) -> dict:
    """Return errors found while scanning plus headings [(line, level, title)]."""
    lines = text.replace("\r\n", "\n").split("\n")
    start = 0
    if lines and lines[0] == "---" and "---" in lines[1:]:
        start = lines.index("---", 1) + 1
    errors: list[tuple[int, str]] = []
    headings: list[tuple[int, int, str]] = []
    prose: list[tuple[int, str]] = []
    fence = None
    in_comment = False
    for number, line in enumerate(lines[start:], start + 1):
        if in_comment:
            in_comment = "-->" not in line
            continue
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            if not m.group(2).strip():
                errors.append((number, "code fence without a language (use ```bash, ```text, ...)"))
            continue
        if line.lstrip().startswith("<!--"):
            in_comment = "-->" not in line
            continue
        h = HEADING.match(line)
        if h:
            headings.append((number, len(h.group(1)), h.group(2)))
        prose.append((number, re.sub(r"`[^`\n]*`", "", line)))
    return {"errors": errors, "headings": headings, "prose": prose}


def naming_error(path: str) -> str | None:
    parts = path.split("/")
    name = parts[-1]
    if len(parts) == 1:
        return None if UPPER_MD.match(name) else f"root docs use UPPERCASE names, got {name}"
    if parts[0] == "docs" and len(parts) == 2:
        return None if UPPER_MD.match(name) else f"docs/ files use UPPER_SNAKE names, got {name}"
    if parts[0] == "docs" and len(parts) == 3:
        return None if name == "README.md" or KEBAB_MD.match(name) else f"{parts[1]}/ files use kebab-case names, got {name}"
    if parts[0] in (".claude", ".opencode") and parts[1] in ("commands", "agents") and len(parts) == 3:
        return None if KEBAB_MD.match(name) else f"command/agent files use kebab-case names, got {name}"
    if parts[0] == ".claude" and parts[1] == "skills" and len(parts) == 4:
        return None if KEBAB.match(parts[2]) and name == "SKILL.md" else f"skills live at .claude/skills/<kebab-name>/SKILL.md, got {path}"
    if parts[0] == "spikes" and len(parts) > 2 and not (KEBAB.match(parts[1]) or parts[1] == "_example"):
        return f"spike folders use kebab-case, got {parts[1]}"
    return None


def lint_file(rel: str) -> list[str]:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    doc = parse(text)
    out = [f"{rel}:{n}: {msg}" for n, msg in doc["errors"]]
    heads = doc["headings"]
    pointer = text.lstrip().startswith("@AGENTS.md") and not heads
    if not pointer and not rel.startswith(NO_H1_PREFIXES) and (not heads or heads[0][1] != 1):
        out.append(f"{rel}: first heading must be the single H1 title")
    out += [f"{rel}:{n}: only one H1 per file" for n, level, _ in heads[1:] if level == 1]
    for (_, prev, _), (n, level, title) in zip(heads, heads[1:]):
        if level > prev + 1:
            out.append(f"{rel}:{n}: heading level jumps from H{prev} to H{level} ('{title}')")
    for n, line in doc["prose"]:
        for pattern, good in ([] if rel in SKIP_TERMS else BANNED):
            bad = re.search(pattern, line)
            if bad:
                out.append(f"{rel}:{n}: write '{good}' instead of '{bad.group(0)}' (docs/STYLE.md)")
        for target in LINK.findall(line):
            if re.match(r"(https?:|mailto:|#)", target) or any(c in target for c in "<>$"):
                continue
            file_part = target.split("#")[0]
            resolved = ROOT / file_part.lstrip("/") if file_part.startswith("/") else path.parent / file_part
            if file_part and not resolved.exists():
                out.append(f"{rel}:{n}: broken link {target}")
    problem = naming_error(rel)
    if problem:
        out.append(f"{rel}: {problem}")
    return out


def template_h2s() -> list[str]:
    text = (ROOT / "docs/templates/zone-readme.md").read_text(encoding="utf-8")
    return [t for _, level, t in parse(text)["headings"] if level == 2]


def zone_readme_errors(zone: str) -> list[str]:
    rel = f"{zone}/README.md"
    path = ROOT / rel
    if not path.is_file():
        return [f"{rel}: missing (copy docs/templates/zone-readme.md)"]
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    doc = parse(text)
    out = []
    heads = doc["headings"]
    if not heads or heads[0][2].rstrip("/").strip() != zone:
        out.append(f"{rel}: H1 must be the folder name '{zone}'")
    body = text.split("\n")
    after = body[heads[0][0]:] if heads else body
    desc = next((ln.strip() for ln in after if ln.strip()), "")
    if not desc or desc.startswith(("#", ">")) or len(desc) > 120:
        out.append(f"{rel}: line after the title must be a plain description of at most 120 characters")
    got = [t for _, level, t in heads if level == 2]
    if got != template_h2s():
        out.append(f"{rel}: H2 sections must be exactly {template_h2s()} in order, got {got}")
    return out


def spike_readme_errors() -> list[str]:
    template = (ROOT / "docs/templates/spike-readme.md").read_text(encoding="utf-8")
    labels = re.findall(r"^- \*\*([^*]+):\*\*", template, re.M)
    out = []
    for rel in project_files("README.md"):
        parts = rel.split("/")
        if parts[0] == "spikes" and len(parts) == 3 and not parts[1].startswith("_"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            out += [f"{rel}: missing field '- **{label}:**' from docs/templates/spike-readme.md" for label in labels if f"**{label}:**" not in text]
    return out


def lint_files(paths: list[str]) -> list[str]:
    out: list[str] = []
    touched_zones = set()
    for rel in paths:
        if rel in SKIP_FILES or rel.startswith(SKIP_PREFIXES) or not (ROOT / rel).is_file():
            continue
        out += lint_file(rel)
        if rel in {f"{z}/README.md" for z in ZONES}:
            touched_zones.add(rel.split("/")[0])
    for zone in sorted(touched_zones):
        out += zone_readme_errors(zone)
    if any(p.startswith("spikes/") and p.endswith("README.md") for p in paths):
        out += spike_readme_errors()
    return out


def main() -> int:
    paths = project_files(".md")
    errors = lint_files(paths)
    for zone in ZONES:
        if f"{zone}/README.md" not in paths:
            errors += zone_readme_errors(zone)
    if errors:
        print("docs style check FAILED (rules: docs/STYLE.md):", file=sys.stderr)
        print("\n".join(f"  - {e}" for e in dict.fromkeys(errors)), file=sys.stderr)
        return 1
    print(f"docs style check passed ({len(paths)} markdown files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Docs-sync gate: code changes must ship with their docs (rules in AGENTS.md, "Documentation rules").

Compares the working tree with the merge-base of origin/main (CHECK_BASE overrides), so it works the
same in CI, in the pre-push hook and in the Claude Code Stop hook (`--claude-stop`).
Waivers: `Docs-Impact: none (<reason>)` and `Agents-Impact: none (<reason>)` in any commit message
since the base, or in the PR description (CI passes it as PR_BODY). The reason must be real text.
"""
import fnmatch
import json
import re
import sys

from _common import changed_files, resolve_base, trailer_text

WAIVE_DOCS = re.compile(r"^\s*Docs-Impact:\s*none\s*\(([^()<>]{5,})\)", re.I | re.M)
WAIVE_AGENTS = re.compile(r"^\s*Agents-Impact:\s*none\s*\(([^()<>]{5,})\)", re.I | re.M)

ZONE_DOCS = {
    "backend": ["backend/README.md", "backend/AGENTS.md", "docs/API_CONTRACT.md", "docs/ARCHITECTURE.md", "docs/features/*.md"],
    "frontend": ["frontend/README.md", "frontend/AGENTS.md", "docs/features/*.md"],
    "scripts": ["AGENTS.md", "CONTRIBUTING.md", "docs/REPO_GUIDE.md", "docs/KICKSTART.md", "docs/STYLE.md"],
}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "bun.lock", "Cargo.lock", "Pipfile.lock"}
DEP_MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "Pipfile", "go.mod", "Cargo.toml", "pom.xml"}
SURFACE_EXACT = {"Makefile", ".env.example", "opencode.json", ".claude/settings.json", ".gemini/settings.json"}
SURFACE_ANY_STATUS = ("scripts/hooks/", ".github/workflows/")
SURFACE_ADD_DELETE = (".claude/", ".opencode/", ".github/", "scripts/")


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return bool(
        re.search(r"(^|/)(tests?|__tests__)/", path)
        or name.startswith("test_")
        or re.search(r"[._]test\.|[._]spec\.|_test\.", name)
    )


def is_code(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return not (path.endswith(".md") or name in LOCKFILES or name == ".gitkeep" or is_test(path))


def zone_of(path: str) -> str | None:
    parts = path.split("/")
    if parts[0] in ("backend", "frontend", "scripts") and len(parts) > 1:
        return parts[0]
    if parts[0] == "spikes" and len(parts) > 2 and not parts[1].startswith("_"):
        return f"spikes/{parts[1]}"
    return None


def zone_docs(zone: str) -> list[str]:
    return [f"{zone}/README.md"] if zone.startswith("spikes/") else ZONE_DOCS[zone]


def evaluate(changes: list[tuple[str, str]], text: str) -> list[str]:
    """Return the list of docs-sync problems for these (status, path) changes."""
    changed = {path for _, path in changes}
    problems: list[str] = []
    zones: dict[str, list[str]] = {}
    for path in sorted(changed):
        zone = zone_of(path)
        if zone and is_code(path):
            zones.setdefault(zone, []).append(path)

    if not WAIVE_DOCS.search(text):
        for zone, files in zones.items():
            wanted = zone_docs(zone)
            if not any(fnmatch.fnmatch(c, pattern) for c in changed for pattern in wanted):
                shown = ", ".join(files[:3]) + (" ..." if len(files) > 3 else "")
                problems.append(f"{zone}: code changed ({shown}) but none of its docs did. Update one of: {', '.join(wanted)}")
        for path in sorted(changed):
            if path.rsplit("/", 1)[-1] in DEP_MANIFESTS and path.split("/")[0] in ("backend", "frontend"):
                if "docs/DECISIONS.md" not in changed:
                    problems.append(f"{path}: dependency manifest changed but docs/DECISIONS.md did not. Log it with /decide")

    if not WAIVE_AGENTS.search(text) and "AGENTS.md" not in changed:
        surface = []
        for status, path in changes:
            if path in SURFACE_EXACT or path.startswith(SURFACE_ANY_STATUS):
                surface.append(path)
            elif path.startswith(SURFACE_ADD_DELETE) and status in ("A", "D") and not path.endswith(".md.bak"):
                surface.append(path)
        if surface:
            shown = ", ".join(sorted(set(surface))[:4]) + (" ..." if len(set(surface)) > 4 else "")
            problems.append(f"convention surface changed ({shown}) but AGENTS.md did not. Update it (commands, structure, skills table) or add 'Agents-Impact: none (<reason>)'")
    return problems


def main() -> int:
    claude_stop = "--claude-stop" in sys.argv
    if claude_stop:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        if payload.get("stop_hook_active"):
            return 0  # already blocked once this turn; never loop

    base, ref = resolve_base()
    if base is None:
        print("docs-sync: no git history yet, skipping")
        return 0
    changes = changed_files(base)
    problems = evaluate(changes, trailer_text(base))

    if claude_stop:
        from check_docs_style import lint_files
        problems += lint_files([p for s, p in changes if p.endswith(".md") and s != "D"])

    if not problems:
        print(f"docs-sync passed (base: {ref})")
        return 0
    header = "docs-sync FAILED. Docs ship with the code (AGENTS.md > Documentation rules):"
    footer = (
        "Fix the docs now. If there is genuinely nothing to document, put "
        "'Docs-Impact: none (<reason>)' (or 'Agents-Impact: none (<reason>)') in the commit message and say so."
    )
    print("\n".join([header, *[f"  - {p}" for p in problems], footer]), file=sys.stderr)
    return 2 if claude_stop else 1


if __name__ == "__main__":
    sys.exit(main())

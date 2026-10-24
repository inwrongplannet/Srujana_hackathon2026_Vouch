#!/usr/bin/env python3
"""Fails CI if README markers are missing or text outside markers changed.

Also checks: required files exist, no .env is tracked, no merge-conflict markers are
committed. Env: CHECK_BASE (default origin/main) is the ref used to compare the README
text outside markers; the comparison is skipped when that ref is unavailable.
The first heading line (the project title) may change.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ["overview", "quickstart", "features", "architecture", "team", "demo"]
REQUIRED = [
    "README.md", "AGENTS.md", "backend/AGENTS.md", "frontend/AGENTS.md", "docs/STYLE.md", "docs/KICKSTART.md", "scripts/py", ".gemini/settings.json", "opencode.json", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", "CONTRIBUTING.md", "Makefile", ".env.example", ".gitignore",
    ".github/CODEOWNERS", ".github/pull_request_template.md", ".github/workflows/check.yml",
    "docs/PROBLEM.md", "docs/ARCHITECTURE.md", "docs/API_CONTRACT.md", "docs/TASKS.md",
    "docs/DECISIONS.md", "docs/DEMO.md", "docs/REPO_GUIDE.md",
]
errors: list[str] = []


def git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def outside_markers(text: str) -> str | None:
    """README text with every marker section removed and the title line dropped."""
    pos, kept = 0, []
    for name in SECTIONS:
        begin, end = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
        if text.count(begin) != 1 or text.count(end) != 1:
            return None
        b, e = text.index(begin), text.index(end)
        if b < pos or e < b:
            return None
        kept.append(text[pos:b])
        pos = e + len(end)
    kept.append(text[pos:])
    body = "".join(kept)
    return re.sub(r"\A# .*\n", "", body, count=1)


def check_required() -> None:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")


def check_readme() -> None:
    path = ROOT / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    for name in SECTIONS:
        b, e = text.count(f"<!-- BEGIN:{name} -->"), text.count(f"<!-- END:{name} -->")
        if b != 1 or e != 1:
            errors.append(f"README.md: marker '{name}' must appear exactly once as BEGIN and END (found {b}/{e})")
    current = outside_markers(text)
    if current is None:
        errors.append("README.md: markers are missing, duplicated, misordered or unpaired")
        return
    base_ref = os.environ.get("CHECK_BASE", "origin/main")
    base = git("show", f"{base_ref}:README.md")
    if base is None:
        print(f"note: {base_ref} not available, skipping outside-marker comparison")
        return
    expected = outside_markers(base.replace("\r\n", "\n"))
    if expected is not None and current != expected:
        errors.append(f"README.md: text outside the marker sections differs from {base_ref}; edit only inside markers (/readme)")


def check_tracked_files() -> None:
    tracked = git("ls-files")
    if tracked is None:
        print("note: not a git checkout, skipping tracked-file checks")
        return
    for rel in tracked.splitlines():
        name = Path(rel).name
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            errors.append(f"secret file is tracked: {rel}")
        p = ROOT / rel
        if not p.is_file() or p.stat().st_size > 2_000_000 or p.suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico"}:
            continue
        try:
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if line.startswith(("<<<<<<< ", ">>>>>>> ")) or line == "=======":
                    errors.append(f"merge-conflict marker in {rel}:{n}")
                    break
        except (UnicodeDecodeError, OSError):
            continue


def main() -> int:
    check_required()
    check_readme()
    check_tracked_files()
    if errors:
        print("structure check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("structure check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

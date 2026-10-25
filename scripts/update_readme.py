#!/usr/bin/env python3
"""Regenerates the README features table from docs/frontend-features/*.md so it is never hand-typed.

Usage: update_readme.py          rewrite the table between BEGIN:features / END:features
       update_readme.py --check  exit 1 if the README is out of date (used by `make check`)
Each manifest is docs/frontend-features/<name>.md in the docs/templates/feature-manifest.md format.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
FEATURES = ROOT / "docs" / "frontend-features"
BLOCK = re.compile(r"(<!-- BEGIN:features -->\n)(.*?)(<!-- END:features -->)", re.S)


def field(text: str, name: str) -> str:
    m = re.search(rf"^- \*\*{name}:\*\*\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def cell(value: str) -> str:
    return (value or "-").replace("|", "\\|")


def table() -> str:
    rows = []
    for path in sorted(FEATURES.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8")
        title = re.search(r"^# Feature:\s*(.+)$", text, re.M)
        name = title.group(1).strip() if title else path.stem
        rows.append((name, field(text, "Status"), field(text, "Assignee"), field(text, "One-liner")))
    if not rows:
        return "_No features yet. Add one in `docs/frontend-features/`, then run `make readme`._\n"
    lines = ["| Feature | Status | Assignee | What it does |", "|---|---|---|---|"]
    lines += [f"| {cell(n)} | {cell(s)} | {cell(o)} | {cell(d)} |" for n, s, o, d in rows]
    return "\n".join(lines) + "\n"


def main() -> int:
    original = README.read_text(encoding="utf-8")
    if not BLOCK.search(original):
        print("README.md: BEGIN:features / END:features markers not found", file=sys.stderr)
        return 1
    updated = BLOCK.sub(lambda m: m.group(1) + table() + m.group(3), original, count=1)
    if "--check" in sys.argv:
        if updated != original:
            print("README features table is out of date. Run `make readme` and commit.", file=sys.stderr)
            return 1
        return 0
    if updated != original:
        README.write_text(updated, encoding="utf-8", newline="\n")
        print("README.md features table updated")
    else:
        print("README.md features table already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())

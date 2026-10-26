#!/usr/bin/env python3
"""Regenerates the README capabilities summary.

Usage: update_readme.py          rewrite the table between BEGIN:features / END:features
       update_readme.py --check  exit 1 if the README is out of date (used by `make check`)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
BLOCK = re.compile(r"(<!-- BEGIN:features -->\n)(.*?)(<!-- END:features -->)", re.S)


def summary() -> str:
    return "Vouch combines explainable affordability analysis, Web-of-Trust reputation, stress-tested loan restructuring, and community-backed lending for people traditional credit scores cannot see.\n"


def main() -> int:
    original = README.read_text(encoding="utf-8")
    if not BLOCK.search(original):
        print("README.md: BEGIN:features / END:features markers not found", file=sys.stderr)
        return 1
    updated = BLOCK.sub(lambda m: m.group(1) + summary() + m.group(3), original, count=1)
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

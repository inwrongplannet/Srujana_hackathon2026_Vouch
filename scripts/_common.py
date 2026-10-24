"""Shared helpers for the repo check scripts (git access, file listing, base commit)."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str | None:
    """Run git in the repo root; return stdout, or None when git fails or is missing."""
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def project_files(suffix: str = "") -> list[str]:
    """Tracked plus untracked-but-not-ignored files (repo-relative, forward slashes)."""
    out = git("ls-files", "-co", "--exclude-standard")
    if out is None:
        return []
    return sorted({p for p in out.splitlines() if p.endswith(suffix) and (ROOT / p).is_file()})


def resolve_base() -> tuple[str | None, str]:
    """Commit to diff against: merge-base with CHECK_BASE, origin/main or main, else HEAD.

    On main itself (or with no other ref) the base is HEAD, so only uncommitted work counts.
    """
    for ref in (os.environ.get("CHECK_BASE"), "origin/main", "main"):
        if not ref or git("rev-parse", "--verify", "--quiet", ref) is None:
            continue
        merge_base = git("merge-base", ref, "HEAD")
        if merge_base:
            return merge_base.strip(), ref
    head = git("rev-parse", "--verify", "--quiet", "HEAD")
    return (head.strip() if head else None), "HEAD"


def changed_files(base: str) -> list[tuple[str, str]]:
    """(status, path) for everything changed in the working tree versus base, plus untracked files."""
    seen: dict[str, str] = {}
    for line in (git("diff", "--name-status", "-M", base) or "").splitlines():
        parts = line.split("\t")
        seen[parts[-1]] = parts[0][0]
    for path in (git("ls-files", "-o", "--exclude-standard") or "").splitlines():
        seen.setdefault(path, "A")
    return sorted((status, path) for path, status in seen.items())


def trailer_text(base: str) -> str:
    """Commit messages since base plus the PR description (CI passes it as PR_BODY)."""
    log = git("log", f"{base}..HEAD", "--format=%B") or ""
    return log + "\n" + os.environ.get("PR_BODY", "")

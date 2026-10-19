"""Git metadata for Evidence: which commit a Claim was read from, and which files differ from it."""

import re
import subprocess
from pathlib import Path

from umbra_engine.guard import redact_output

GIT_TIMEOUT_S = 10
_COMMIT = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


def head_commit(root: Path) -> str | None:
    """Full id of HEAD, or None when the folder is not a git repository or has no commit yet."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    commit = redact_output(result.stdout.strip(), "git rev-parse")
    return commit if result.returncode == 0 and _COMMIT.match(commit) else None


def changed_files(root: Path) -> set[str] | None:
    """Paths that differ from HEAD (modified, added, renamed or untracked); None when git cannot tell.

    A path holding a secret comes back redacted, so it never matches: that file is then treated as
    changed, which is the safe side.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "-z", "--untracked-files=all"],
            capture_output=True,
            timeout=GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    entries = [e.decode("utf-8", errors="replace") for e in result.stdout.split(b"\0") if e]
    changed: set[str] = set()
    skip_next = False
    for entry in entries:
        if skip_next:  # the original path of a rename
            skip_next = False
            changed.add(redact_output(entry, "git status"))
            continue
        status, path = entry[:2], entry[3:]
        changed.add(redact_output(path, "git status"))
        skip_next = "R" in status or "C" in status
    return changed

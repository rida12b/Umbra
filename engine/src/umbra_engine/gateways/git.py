"""Git metadata for Evidence: which commit a Claim was read from, and which files differ from it."""

import re
import subprocess
from pathlib import Path

from umbra_engine.guard import redact_output

GIT_TIMEOUT_S = 10
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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


def head_info(root: Path) -> tuple[str, str]:
    """`(branch, date of the last commit as YYYY-MM-DD)`; empty strings when git cannot tell (a detached
    HEAD has no branch name)."""
    branch = _run(root, "rev-parse", "--abbrev-ref", "HEAD")
    date = _run(root, "log", "-1", "--format=%cs")
    name = redact_output(branch.strip(), "git rev-parse") if branch else ""
    day = redact_output(date.strip(), "git log") if date else ""
    return ("" if name == "HEAD" else name), (day if _DAY.match(day) else "")


def changed_files(root: Path) -> set[str] | None:
    """Project-relative paths that differ from HEAD (modified, added, renamed or untracked); None when
    git cannot tell, which makes every file a worktree version.

    The Project may be a sub-folder of its repository: porcelain paths are relative to the repository
    root, so they are brought back under the Project. A path that holds a secret cannot be compared
    once redacted: the whole answer is then None, the safe side.
    """
    prefix = _run(root, "rev-parse", "--show-prefix")
    status = _run(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", ".")
    if prefix is None or status is None:
        return None
    prefix = prefix.strip()
    changed: set[str] = set()
    skip_next = False
    for entry in (e for e in status.split("\0") if e):
        if skip_next:  # the original path of a rename
            skip_next, path = False, entry
        else:
            code, path = entry[:2], entry[3:]
            skip_next = "R" in code or "C" in code
        if redact_output(path, "git status") != path:
            return None
        if path.startswith(prefix):
            changed.add(path.removeprefix(prefix))
    return changed


def _run(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")

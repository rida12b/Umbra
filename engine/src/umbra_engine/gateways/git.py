"""Git metadata for Evidence: the commit a Claim was read from."""

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

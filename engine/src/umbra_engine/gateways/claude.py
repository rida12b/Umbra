"""The user's own Claude Code, in the background (ADR-0003): the only way Umbra asks an LLM anything.

The prompt goes on stdin, from an empty temporary folder, with no tools, one turn, no saved session,
and without any variable that would make `claude` use an API key instead of the user's subscription.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from umbra_engine.guard import redact_output

CLAUDE_TIMEOUT_S = 300
SCRUBBED = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")
COMMAND = [
    "claude", "-p", "--safe-mode", "--no-session-persistence", "--tools", "",
    "--max-turns", "1", "--output-format", "json",
]  # fmt: skip


class ClaudeUnavailableError(RuntimeError):
    """Claude Code is missing, not signed in with a subscription, or did not answer."""


def child_environment(environment: dict[str, str]) -> dict[str, str]:
    kept = {
        name: value
        for name, value in environment.items()
        if name not in SCRUBBED and not name.startswith("CLAUDE_CODE_USE_")
    }
    return kept | {"UMBRA_CHILD": "1"}  # Umbra's own hooks ignore the sessions it starts


def subscription_login() -> bool:
    """True only when `claude` is signed in with a claude.ai subscription (never an API key)."""
    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            env=child_environment(dict(os.environ)),
        )
        return json.loads(result.stdout).get("authMethod") == "claude.ai"
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False


STUDY_TIMEOUT_S = 40 * 60
STUDY_MAX_TURNS = 150
STUDY_COMMAND = [
    "claude", "-p", "--safe-mode", "--restricted", "--strict-mcp-config", "--no-session-persistence",
    "--tools", "Read,Grep,Glob", "--permission-prompts", "none", "--max-turns", str(STUDY_MAX_TURNS),
    "--output-format", "json",
]  # fmt: skip


def study(prompt: str, folder: Path) -> str:
    """One study session in `folder` (the guarded copy) with read-only tools: Read, Grep, Glob only.
    `--restricted` ignores every user and project settings file (a cloned Project cannot grant
    itself wider reads) and confines file tools to the folder; anything else would need a
    permission nobody can give here."""
    # The long form of the path: Windows short names (`RBOUAL~1`) make every read ask for a
    # permission that nobody can give here, so the session would see nothing.
    return _answer(_run(STUDY_COMMAND, prompt, folder.resolve(), STUDY_TIMEOUT_S))


def ask(prompt: str) -> str:
    """One answer to one prompt. The prompt must already come from the Secret Guard."""
    with tempfile.TemporaryDirectory(prefix="umbra-claude-") as empty:
        return _answer(_run(COMMAND, prompt, Path(empty), CLAUDE_TIMEOUT_S))


def _run(command: list[str], prompt: str, folder: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=folder,
            env=child_environment(dict(os.environ)),
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ClaudeUnavailableError(f"claude did not answer: {type(error).__name__}") from error


def _answer(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0:
        raise ClaudeUnavailableError(redact_output(result.stderr.strip()[:300], "claude"))
    try:
        answer = json.loads(result.stdout)
    except ValueError as error:
        raise ClaudeUnavailableError("claude returned no JSON envelope") from error
    if answer.get("is_error"):
        raise ClaudeUnavailableError(redact_output(str(answer.get("result", ""))[:300], "claude"))
    return redact_output(str(answer.get("result", "")), "claude")

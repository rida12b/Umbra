"""The user's own Claude Code, in the background (ADR-0003): the only way Umbra asks an LLM anything.

The prompt goes on stdin, from an empty temporary folder, with no tools, one turn, no saved session,
and without any variable that would make `claude` use an API key instead of the user's subscription.
"""

import json
import os
import subprocess
import tempfile

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


def ask(prompt: str) -> str:
    """One answer to one prompt. The prompt must already come from the Secret Guard."""
    with tempfile.TemporaryDirectory(prefix="umbra-claude-") as empty:
        try:
            result = subprocess.run(
                COMMAND,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=empty,
                env=child_environment(dict(os.environ)),
                timeout=CLAUDE_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ClaudeUnavailableError(f"claude did not answer: {type(error).__name__}") from error
    if result.returncode != 0:
        raise ClaudeUnavailableError(redact_output(result.stderr.strip()[:300], "claude"))
    try:
        answer = json.loads(result.stdout)
    except ValueError as error:
        raise ClaudeUnavailableError("claude returned no JSON envelope") from error
    if answer.get("is_error"):
        raise ClaudeUnavailableError(redact_output(str(answer.get("result", ""))[:300], "claude"))
    return redact_output(str(answer.get("result", "")), "claude")

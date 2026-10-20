"""Claude Code hook: report a prompt, an edited file or Claude's final message to the Umbra engine.

Runs on every UserPromptSubmit, file-editing PostToolUse and Stop (asynchronously: it never blocks
Claude). It writes one event file into Umbra's spool folder: written whole under a temporary name,
then renamed, so the engine never reads half an event, even after a power cut. The engine need not
be running; it ingests the spool when it starts. Standard library only: no import cost, no
dependency. It reads nothing of the Project and never fails Claude: any problem is ignored.
"""

import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

KINDS = {"UserPromptSubmit": "prompt", "PostToolUse": "edit", "Stop": "stop"}
MAX_TEXT = 4000


def event_from(hook: dict) -> dict | None:
    kind = KINDS.get(hook.get("hook_event_name", ""))
    if kind is None:
        return None
    event = {
        "id": uuid.uuid4().hex,
        "at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "kind": kind,
        "session": hook.get("session_id", ""),
        "prompt_id": hook.get("prompt_id", ""),
        "cwd": os.environ.get("CLAUDE_PROJECT_DIR") or hook.get("cwd", ""),
        "files": [],
        "text": "",
        "tool": hook.get("tool_name", ""),
    }
    if kind == "edit":
        tool_input = hook.get("tool_input") or {}
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not path:
            return None
        event["files"] = [path]
    elif kind == "prompt":
        event["text"] = str(hook.get("prompt", ""))[:MAX_TEXT]
    else:
        event["text"] = str(hook.get("last_assistant_message", ""))[:MAX_TEXT]
    return event


def spool(home: Path, event: dict) -> None:
    folder = home / "journal" / "spool"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{time.time_ns()}-{event['id']}"  # sortable, and no ':' (not allowed in Windows names)
    temporary = folder / f"{name}.tmp"
    temporary.write_text(json.dumps(event), encoding="utf-8")
    os.replace(temporary, folder / f"{name}.json")


def main() -> None:
    if os.environ.get("UMBRA_CHILD"):  # a session Umbra itself started: nothing to report
        return
    try:
        # Claude Code writes UTF-8; sys.stdin would decode it in the locale encoding (cp1252 on Windows)
        event = event_from(json.loads(sys.stdin.buffer.read().decode("utf-8")))
        if event is not None:
            spool(Path(os.environ.get("UMBRA_HOME") or Path.home() / ".umbra"), event)
    except Exception:  # noqa: BLE001 — a reporting hook must never disturb Claude
        return


if __name__ == "__main__":
    main()

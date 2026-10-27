"""The whole S5 chain with the real hook script: Claude Code's hook payloads → spool → live engine →
/activity shows the turn (prompt, edited files, final message)."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from secret_fixtures import write_repo

from umbra_engine.api import create_app

HOOK = Path(__file__).resolve().parents[2] / "plugin" / "scripts" / "umbra_hook.py"


def hook(home: Path, payload: dict, **env: str) -> None:
    environment = {**os.environ, "UMBRA_HOME": str(home), **env}
    if "UMBRA_CHILD" not in env:  # the test runner may itself run inside a Umbra-started session
        environment.pop("UMBRA_CHILD", None)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")  # as Claude Code sends it
    subprocess.run([sys.executable, str(HOOK)], input=raw, env=environment, check=True)


def wait_for(condition, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = condition()
        if found:
            return found
        time.sleep(0.2)
    raise AssertionError("timed out")


def test_a_claude_turn_appears_with_its_prompt_files_and_final_message(settings, auth, make_repo):
    root = write_repo(make_repo("shop"), {"app/a.py": "x = 1\n"}, git=False)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        client.post(f"/v1/projects/{project}/index", headers=auth)
        common = {"session_id": "s1", "prompt_id": "p1", "cwd": str(root)}
        hook(settings.home, {**common, "hook_event_name": "UserPromptSubmit", "prompt": "Passe x à « deux »"})
        hook(settings.home, {**common, "hook_event_name": "PostToolUse", "tool_name": "Edit",
                             "tool_input": {"file_path": str(root / "app" / "a.py")}})  # fmt: skip
        hook(settings.home, {**common, "hook_event_name": "Stop", "last_assistant_message": "x is now 2."})

        def activity():
            turns = client.get(f"/v1/projects/{project}/activity", headers=auth).json()
            return turns if turns and turns[0]["message"] else None

        [turn] = wait_for(activity)
        assert (turn["prompt"], turn["files"], turn["message"]) == (
            "Passe x à « deux »",
            ["app/a.py"],
            "x is now 2.",
        )


def test_sessions_started_by_umbra_report_nothing(settings, make_repo):
    root = write_repo(make_repo("quiet"), {"a.py": "x = 1\n"}, git=False)
    payload = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "cwd": str(root), "prompt": "study"}
    hook(settings.home, payload, UMBRA_CHILD="1")
    spool = settings.home / "journal" / "spool"
    assert not spool.exists() or not any(spool.iterdir())

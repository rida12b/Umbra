"""#114: the engine never runs `claude`. A fake `claude` first on PATH writes a marker file when anything
starts it; `start` a repo, follow a second one, open both maps, call `show`, let live mode settle: no marker.
Every other folder holding a `claude` is taken off PATH, and a spy on subprocess records any program named
`claude` and refuses to start it: a regression fails this test without ever reaching the real one."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from secret_fixtures import write_repo
from system_fixtures import TEMPLATE
from test_live import wait_for

from umbra_engine import cli

SETTLE_S = 2.0  # the removed study started within milliseconds of following a repo


def fake_claude(folder: Path, marker: Path) -> None:
    folder.mkdir()
    if sys.platform == "win32":
        (folder / "claude.cmd").write_text(f'@echo %* >> "{marker}"\r\n', encoding="utf-8")
    else:
        script = folder / "claude"
        script.write_text(f'#!/bin/sh\necho "$*" >> "{marker}"\n', encoding="utf-8")
        script.chmod(0o755)


def is_claude(argv: list[str]) -> bool:
    return Path(argv[0]).stem.lower() == "claude"


@pytest.fixture
def started(monkeypatch, tmp_path: Path) -> list[list[str]]:
    """Every program the engine starts, as its argv; a `claude` that is not the fake is never started."""
    seen: list[list[str]] = []
    real = subprocess.Popen

    class Spy(real):  # type: ignore[misc, valid-type]
        def __init__(self, args, *rest, **kwargs) -> None:
            argv = [str(a) for a in args] if isinstance(args, list | tuple) else [str(args)]
            seen.append(argv)
            if is_claude(argv) and not Path(argv[0]).is_relative_to(tmp_path):
                raise FileNotFoundError("the real claude is hidden from this test")
            super().__init__(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", Spy)
    return seen


def test_start_follow_map_and_show_never_run_claude(
    settings, auth, make_repo, monkeypatch, tmp_path, started
):
    marker = tmp_path / "claude-was-called.txt"
    fake_claude(tmp_path / "bin", marker)
    kept = [
        d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not shutil.which("claude", path=d)
    ]
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path / "bin"), *kept]))
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    probe = shutil.which("claude")  # the probe works: `claude` on this PATH is the fake, and it writes
    assert probe is not None and Path(probe).parent == tmp_path / "bin"
    subprocess.run([probe, "--version"], check=True, shell=sys.platform == "win32")
    assert marker.exists()
    marker.unlink()
    started.clear()

    first = write_repo(make_repo("full-stack-fastapi-template"), TEMPLATE)
    second = write_repo(make_repo("followed"), {"app/main.py": "def main():\n    return 1\n"})
    import uvicorn

    def serve(app, host, port, log_level) -> None:  # what the browser and Claude Code do, on the real app
        with TestClient(app, base_url="http://127.0.0.1") as client:
            ids = [p["id"] for p in client.get("/v1/projects", headers=auth).json()]
            ids.append(client.post("/v1/projects", json={"path": str(second)}, headers=auth).json()["id"])
            for project in ids:
                url = f"/v1/projects/{project}/system"
                wait_for(lambda url=url: client.get(url, headers=auth).status_code == 200)
            body = {"caption": "où est le modèle ?", "parts": ["Base"], "path": ["backend/app/models.py"]}
            lit = client.post(f"/v1/projects/{ids[0]}/show", json=body, headers=auth)
            assert lit.status_code == 200, lit.text
            assert client.get(f"/v1/projects/{ids[0]}/activity", headers=auth).status_code == 200
            time.sleep(SETTLE_S)

    monkeypatch.setattr(uvicorn, "run", serve)
    assert cli.main(["start", str(first), "--no-browser"]) == 0

    assert not marker.exists(), marker.read_text(encoding="utf-8")
    assert not [argv for argv in started if is_claude(argv)], started
    assert any(Path(argv[0]).stem.lower() == "git" for argv in started)  # the spy sees the engine's programs

"""Live mode, critical path only: a change on disk re-indexes the Project, names the changed files,
and rewrites only the cards that became out of date — through the real file watcher."""

import json
import time

from fastapi.testclient import TestClient
from secret_fixtures import write_repo

from umbra_engine.api import create_app

CARD = json.dumps({"role": "r", "etapes": [], "enfants": {}})


def wait_for(condition, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError("timed out")


def test_a_change_on_disk_reindexes_and_rewrites_only_what_changed(settings, auth, make_repo):
    files = {"app/a.py": "def a():\n    return 1\n", "app/b.py": "def b():\n    return 2\n"}
    root = write_repo(make_repo("live"), files, git=False)
    prompts: list[str] = []
    app = create_app(settings, ask=lambda prompt: prompts.append(prompt) or CARD, live=True)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        client.post(f"/v1/projects/{project}/index", headers=auth)
        for node in ("app/a.py", "app/b.py"):
            client.post(f"/v1/projects/{project}/explain", params={"node": node}, headers=auth)
        wait_for(
            lambda: any("FILE app/b.py" in p for p in prompts) and any("FILE app/a.py" in p for p in prompts)
        )
        time.sleep(1)  # let the first look (architecture, Application, folders) finish
        events = app.state.live._events  # noqa: SLF001 — read what the pages would receive
        seen = events.latest()
        before = len(prompts)

        (root / "app/a.py").write_text("def a():\n    return 42\n")
        wait_for(lambda: any(e["type"] == "indexed" for _, e in events.since(project, seen)))
        indexed = next(e for _, e in events.since(project, seen) if e["type"] == "indexed")
        assert indexed["changed"] == ["app/a.py"]

        wait_for(
            lambda: any(e == {"type": "card", "key": "app/a.py"} for _, e in events.since(project, seen))
        )
        asked_after = prompts[before:]
        assert any("return 42" in p for p in asked_after)
        assert not any("FILE app/b.py" in p for p in asked_after)  # b.py untouched: not asked again

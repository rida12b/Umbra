"""Live mode, critical path only: a change on disk re-indexes the followed Project and names the changed files
to the pages. Nothing in it runs a model (ADR-0007, #114)."""

import time

from fastapi.testclient import TestClient
from secret_fixtures import write_repo

from umbra_engine.api import create_app


def wait_for(condition, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError("timed out")


def test_a_change_on_disk_is_read_again_and_named_to_the_pages(settings, auth, make_repo):
    files = {"app/a.py": "def a():\n    return 1\n", "app/b.py": "def b():\n    return 2\n"}
    root = write_repo(make_repo("live"), files, git=False)
    app = create_app(settings, live=True)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        client.post(f"/v1/projects/{project}/index", headers=auth)  # followed from now on

        events = app.state.live._events  # noqa: SLF001 — read what the pages would receive
        seen = events.latest()
        (root / "app/a.py").write_text("def a():\n    return 42\n")
        wait_for(lambda: any(e["type"] == "indexed" for _, e in events.since(project, seen)))
        indexed = next(e for _, e in events.since(project, seen) if e["type"] == "indexed")
        assert indexed["changed"] == ["app/a.py"]
        assert {e["type"] for _, e in events.since(project, seen)} == {"indexed"}

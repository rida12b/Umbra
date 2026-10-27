"""A project added while the engine runs is read at once (#85): no restart, and no « index it again ».
Asking for the map before the index is ready gets « indexing » (409); a failed read is said (500)."""

import threading
import time

from fastapi.testclient import TestClient
from secret_fixtures import write_repo
from test_live import wait_for

import umbra_engine.api as api_module
from umbra_engine.api import create_app
from umbra_engine.api_system import INDEXING
from umbra_engine.indexer import index_project as real_index_project
from umbra_engine.registry import Registry

FILES = {"app/a.py": "def a():\n    return 1\n", "app/b.py": "def b():\n    return 2\n"}


def test_a_project_added_while_running_is_indexed_without_restart(settings, auth, make_repo):
    root = write_repo(make_repo("added"), FILES, git=False)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}/system"
        first = client.get(url, headers=auth)
        assert first.status_code in (200, 409), first.text
        if first.status_code == 409:
            assert first.json()["detail"] == INDEXING  # never « index it again »
        wait_for(lambda: client.get(url, headers=auth).status_code == 200)


def test_asking_the_map_of_a_never_indexed_project_reads_it_instead_of_failing(settings, auth, make_repo):
    root = write_repo(make_repo("never"), FILES, git=False)
    app = create_app(settings)  # not live: only the page's call can start it
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}"
        assert client.get(f"{url}/coverage", headers=auth).status_code == 409  # nothing indexed it yet
        answer = client.get(f"{url}/system", headers=auth)
        assert answer.status_code == 409 and answer.json()["detail"] == INDEXING, answer.text
        wait_for(lambda: client.get(f"{url}/system", headers=auth).status_code == 200)


def test_a_registered_but_never_indexed_project_is_read_at_startup(settings, auth, make_repo):
    root = write_repo(make_repo("startup"), FILES, git=False)
    registry = Registry(settings)
    project, _ = registry.add(str(root))  # registered by `umbra-engine add`, never indexed
    registry.close()
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        wait_for(lambda: client.get(f"/v1/projects/{project.id}/coverage", headers=auth).status_code == 200)


def test_two_index_requests_at_once_do_not_break_the_store(settings, auth, make_repo):
    root = write_repo(make_repo("twice"), FILES, git=False)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        # The background read started by the add, and an explicit one, at the same time.
        summary = client.post(f"/v1/projects/{project}/index", headers=auth)
        assert summary.status_code == 200 and summary.json()["files"] == 2, summary.text
        wait_for(lambda: client.get(f"/v1/projects/{project}/coverage", headers=auth).status_code == 200)


def test_a_failed_read_is_said_to_the_page_not_left_as_indexing(settings, auth, make_repo, monkeypatch):
    root = write_repo(make_repo("broken"), FILES, git=False)
    app = create_app(settings)

    def broken(project, store):
        raise OSError("disk unreadable")

    monkeypatch.setattr("umbra_engine.api.index_project", broken)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}/system"
        assert client.get(url, headers=auth).status_code == 409

        def said() -> bool:
            answer = client.get(url, headers=auth)
            return answer.status_code == 500 and "disk unreadable" in answer.json()["detail"]

        wait_for(said)


def test_a_transient_read_failure_recovers_without_restart(settings, auth, make_repo, monkeypatch):
    """A read fails once (a file locked by an antivirus, a folder unmounted for a moment), then the cause goes
    away: reloading the page, or adding the folder again, reads it again. No restart (review of #85)."""
    root = write_repo(make_repo("flaky"), FILES, git=False)
    calls = {"n": 0}

    def flaky(project, store):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("file locked")
        return real_index_project(project, store)

    monkeypatch.setattr("umbra_engine.api.index_project", flaky)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}/system"
        wait_for(lambda: client.get(url, headers=auth).status_code == 500)
        # The cause is gone. The user reloads the page a few times, then adds the folder again.
        for _ in range(5):
            client.get(url, headers=auth)
            time.sleep(0.2)
        again = client.post("/v1/projects", json={"path": str(root)}, headers=auth)
        assert again.status_code == 200, again.text
        wait_for(lambda: client.get(url, headers=auth).status_code == 200)


def test_shutdown_waits_at_most_the_join_budget_once(settings, auth, make_repo, monkeypatch):
    """Three slow reads at startup (after an upgrade, every project is read again): one budget for all."""
    registry = Registry(settings)
    for name in ("p1", "p2", "p3"):
        registry.add(str(write_repo(make_repo(name), FILES, git=False)))
    registry.close()
    release = threading.Event()

    def slow(project, store):
        release.wait(30)
        return real_index_project(project, store)

    monkeypatch.setattr("umbra_engine.api.index_project", slow)
    monkeypatch.setattr(api_module, "READ_JOIN_S", 1.0)
    app = create_app(settings, live=True)
    client = TestClient(app, base_url="http://127.0.0.1")
    client.__enter__()
    time.sleep(0.5)  # the three reads are running
    started = time.monotonic()
    client.__exit__(None, None, None)
    took = time.monotonic() - started
    release.set()
    assert took < 1.5, f"shutdown took {took:.2f}s (budget 1.0 s)"


def test_two_pages_opening_an_added_project_read_it_once(settings, auth, make_repo, monkeypatch):
    """Two tabs poll the map through « indexing »: the Project is read once, not once per tab."""
    root = write_repo(make_repo("once"), FILES, git=False)
    reads = {"n": 0}

    def counted(project, store):
        reads["n"] += 1
        return real_index_project(project, store)

    monkeypatch.setattr("umbra_engine.api.index_project", counted)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}/system"
        threads = [
            threading.Thread(
                target=lambda: wait_for(lambda: client.get(url, headers=auth).status_code == 200)
            )
            for _ in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert reads["n"] == 1


def test_a_read_that_keeps_failing_is_not_read_again_on_every_ask(settings, auth, make_repo, monkeypatch):
    """The page asks on every live event: a cause that stays gives one read and a steady error, not a read per
    ask; « Réessayer » (relire) reads again at once (short round of #85)."""
    root = write_repo(make_repo("locked"), FILES, git=False)
    reads = {"n": 0}

    def locked(project, store):
        reads["n"] += 1
        raise OSError("file locked")

    monkeypatch.setattr("umbra_engine.api.index_project", locked)
    app = create_app(settings, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}/system"
        wait_for(lambda: client.get(url, headers=auth).status_code == 500)
        seen = [client.get(url, headers=auth).status_code for _ in range(8)]
        assert seen == [500] * 8 and reads["n"] == 1, (seen, reads)
        retried = client.get(f"{url}?relire=true", headers=auth)
        assert retried.status_code == 409 and retried.json()["detail"] == INDEXING, retried.text
        wait_for(lambda: reads["n"] == 2)

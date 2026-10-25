"""A project added while the engine runs is read at once (#85): no restart, and no « index it again »
shown as a Claude Code failure. Asking for the model before the index is ready gets « indexing »."""

from fastapi.testclient import TestClient
from secret_fixtures import write_repo
from test_live import FakeStudy, wait_for

from umbra_engine.api import create_app
from umbra_engine.registry import Registry

FILES = {"app/a.py": "def a():\n    return 1\n", "app/b.py": "def b():\n    return 2\n"}


def test_a_project_added_while_running_is_indexed_and_studied_without_restart(settings, auth, make_repo):
    root = write_repo(make_repo("added"), FILES, git=False)
    app = create_app(settings, ask=lambda prompt: "{}", study=FakeStudy(), live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}"
        first = client.get(f"{url}/model", headers=auth)
        assert first.status_code == 200, first.text  # never the 409 « index it again »
        assert first.json()["state"] in ("indexing", "missing", "queued", "working", "ready")
        wait_for(lambda: client.get(f"{url}/coverage", headers=auth).status_code == 200)
        # The page's own call (missing → study) reaches the study, with no « index » call from anyone.
        client.post(f"{url}/model", headers=auth)
        wait_for(lambda: client.get(f"{url}/model", headers=auth).json()["state"] == "ready")


def test_asking_the_model_of_a_never_indexed_project_reads_it_instead_of_failing(settings, auth, make_repo):
    root = write_repo(make_repo("never"), FILES, git=False)
    app = create_app(
        settings, ask=lambda prompt: "{}", study=FakeStudy()
    )  # not live: only the page's call can start it
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        url = f"/v1/projects/{project}"
        assert client.get(f"{url}/coverage", headers=auth).status_code == 409  # nothing indexed it yet
        answer = client.get(f"{url}/model", headers=auth)
        assert answer.status_code == 200 and answer.json()["state"] == "indexing", answer.text
        wait_for(lambda: client.get(f"{url}/coverage", headers=auth).status_code == 200)


def test_a_registered_but_never_indexed_project_is_read_at_startup(settings, auth, make_repo):
    root = write_repo(make_repo("startup"), FILES, git=False)
    registry = Registry(settings)
    project, _ = registry.add(str(root))  # registered by `umbra-engine add`, never indexed
    registry.close()
    app = create_app(settings, ask=lambda prompt: "{}", study=FakeStudy(), live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        wait_for(lambda: client.get(f"/v1/projects/{project.id}/coverage", headers=auth).status_code == 200)


def test_two_index_requests_at_once_do_not_break_the_store(settings, auth, make_repo):
    root = write_repo(make_repo("twice"), FILES, git=False)
    app = create_app(settings, ask=lambda prompt: "{}", study=FakeStudy(), live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        # The background read started by the add, and an explicit one, at the same time.
        summary = client.post(f"/v1/projects/{project}/index", headers=auth)
        assert summary.status_code == 200 and summary.json()["files"] == 2, summary.text
        wait_for(lambda: client.get(f"/v1/projects/{project}/coverage", headers=auth).status_code == 200)



def test_a_failed_read_is_said_to_the_page_not_left_as_indexing(settings, auth, make_repo, monkeypatch):
    root = write_repo(make_repo("broken"), FILES, git=False)
    app = create_app(settings, ask=lambda prompt: "{}", study=FakeStudy())

    def broken(project, store):
        raise OSError("disk unreadable")

    monkeypatch.setattr("umbra_engine.api.index_project", broken)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        assert client.get(f"/v1/projects/{project}/model", headers=auth).json()["state"] == "indexing"

        def said() -> bool:
            answer = client.get(f"/v1/projects/{project}/model", headers=auth)
            return answer.status_code == 500 and "disk unreadable" in answer.json()["detail"]

        wait_for(said)

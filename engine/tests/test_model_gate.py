"""A new study method never spends the user's Claude subscription by itself (#78): a model written by an
older method is kept and served, and only an explicit « Relancer l'étude » starts one full study."""

import json
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient
from secret_fixtures import write_repo

from umbra_engine.analysis.runner import MODEL_KEY, MODEL_PRODUCER, file_digests
from umbra_engine.api import create_app
from umbra_engine.indexer import index_project
from umbra_engine.gateways.claude import ClaudeUnavailableError
from umbra_engine.registry import Registry

OLD = "claude-code-study@1.6"
FILES = {"app/main.py": "def main():\n    return 1\n", "app/store.py": "def save():\n    return 2\n"}
OLD_MODEL = {
    "pitch": "Une petite application.", "resume": "r", "flux": [], "composants": [], "modules": {}, "dossiers": {},
    "incertitudes": [], "blocs": [{"id": "api", "nom": "API", "type": "backend", "role": "r", "code": []}],
    "parcours": [],
}  # fmt: skip
ANSWER = {**OLD_MODEL, "modules": {"app/main.py": "démarre"}}


class CountingStudy:
    def __init__(
        self, answer: str = json.dumps(ANSWER), fail: Exception | None = None, wait: float = 0.0
    ) -> None:
        self.prompts: list[str] = []
        self.answer, self.fail, self.wait = answer, fail, wait
        self._lock = threading.Lock()

    def __call__(self, prompt: str, folder: Path) -> str:
        with self._lock:
            self.prompts.append(prompt)
        time.sleep(self.wait)
        if self.fail:
            raise self.fail
        return self.answer


def wait_until(condition, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError("timed out")


def old_project(settings, make_repo, name: str = "old") -> tuple[str, Path]:
    """A registered, indexed Project whose stored model was written by method 1.6."""
    root = write_repo(make_repo(name), FILES, git=False)

    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            digests = file_digests(store.files())
            record = {"model": OLD_MODEL, "digests": digests, "producer": OLD}
            store.save_card(MODEL_KEY, "d", json.dumps(record), OLD, "2026-10-22T00:00:00+00:00")
    return project.id, root


def test_serving_projects_studied_by_an_older_method_starts_no_session(settings, auth, make_repo):
    ids = [old_project(settings, make_repo, f"p{n}")[0] for n in range(3)]
    study = CountingStudy()
    app = create_app(settings, ask=lambda prompt: "{}", study=study, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        time.sleep(1.0)  # let the watchers start
        for project in ids:
            state = client.get(f"/v1/projects/{project}/model", headers=auth).json()
            assert (state["state"], state["methode_ancienne"], state["producer"]) == ("methode", True, OLD)
            assert state["model"] == OLD_MODEL
    print(f"study sessions: {len(study.prompts)}")
    assert study.prompts == []


def test_a_plain_request_or_a_code_change_on_an_outdated_model_starts_no_session(settings, auth, make_repo):
    project, root = old_project(settings, make_repo)
    study = CountingStudy()
    app = create_app(settings, ask=lambda prompt: "{}", study=study, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert (
            client.post(f"/v1/projects/{project}/model", headers=auth).json()["state"] == "methode"
        )  # an old tab
        events = app.state.live._events  # noqa: SLF001
        seen = events.latest()
        (root / "app/main.py").write_text("def main():\n    return 42\n")
        wait_until(lambda: any(e["type"] == "indexed" for _, e in events.since(project, seen)))
        time.sleep(1.0)
        state = client.get(f"/v1/projects/{project}/model", headers=auth).json()
        assert "app/main.py" in state["changed"] and state["state"] == "methode"
    print(f"study sessions: {len(study.prompts)}")
    assert study.prompts == []
    with Registry(settings) as registry:
        known = registry.get(project)
        assert known is not None
        with registry.open_store(known) as store:
            row = store.card(MODEL_KEY)
    assert row is not None and row[2] == OLD  # never stamped 1.7 by an update on a 1.6 base


def test_relaunch_starts_exactly_one_full_study_even_when_clicked_twice(settings, auth, make_repo):
    project, _ = old_project(settings, make_repo)
    study = CountingStudy(wait=0.5)
    app = create_app(settings, ask=lambda prompt: "{}", study=study)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        url = f"/v1/projects/{project}/model"
        first = client.post(url, json={"relancer": True}, headers=auth).json()
        client.post(url, json={"relancer": True}, headers=auth)
        assert (
            first["state"] in ("queued", "working") and first["model"] == OLD_MODEL
        )  # the old one stays visible
        wait_until(lambda: client.get(url, headers=auth).json()["state"] == "ready")
        state = client.get(url, headers=auth).json()
    print(f"study sessions: {len(study.prompts)}")
    assert len(study.prompts) == 1 and "MAP (cheap)" in study.prompts[0]  # a full study, not an update
    assert (state["producer"], state["methode_ancienne"]) == (MODEL_PRODUCER, False)


def test_a_failed_relaunch_keeps_the_old_model_and_never_retries_by_itself(settings, auth, make_repo):
    project, root = old_project(settings, make_repo)
    study = CountingStudy(fail=ClaudeUnavailableError("Claude Code n'est pas connecté."))
    app = create_app(settings, ask=lambda prompt: "{}", study=study, live=True)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        url = f"/v1/projects/{project}/model"
        client.post(url, json={"relancer": True}, headers=auth)
        wait_until(lambda: client.get(url, headers=auth).json()["state"] == "error")
        (root / "app/store.py").write_text("def save():\n    return 3\n")
        time.sleep(1.5)
        state = client.get(url, headers=auth).json()
    assert len(study.prompts) == 1
    assert (state["methode_ancienne"], state["model"]) == (True, OLD_MODEL)
    assert "Traceback" not in (state["message"] or "")


def test_a_cut_off_answer_keeps_the_previous_model(settings, auth, make_repo):
    project, _ = old_project(settings, make_repo)
    study = CountingStudy(answer=json.dumps(ANSWER)[: len(json.dumps(ANSWER)) * 6 // 10])
    app = create_app(settings, ask=lambda prompt: "{}", study=study)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        url = f"/v1/projects/{project}/model"
        client.post(url, json={"relancer": True}, headers=auth)
        wait_until(lambda: client.get(url, headers=auth).json()["state"] == "error")
        assert client.get(url, headers=auth).json()["model"] == OLD_MODEL


def test_a_project_without_model_is_still_studied_on_first_open(settings, auth, make_repo):
    root = write_repo(make_repo("fresh"), FILES, git=False)
    study = CountingStudy()
    app = create_app(settings, ask=lambda prompt: "{}", study=study)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        client.post(f"/v1/projects/{project}/index", headers=auth)
        client.post(f"/v1/projects/{project}/model", headers=auth)
        wait_until(
            lambda: client.get(f"/v1/projects/{project}/model", headers=auth).json()["state"] == "ready"
        )
        assert client.get(f"/v1/projects/{project}/model", headers=auth).json()["methode_ancienne"] is False
    assert len(study.prompts) == 1

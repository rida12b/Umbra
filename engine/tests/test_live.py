"""Live mode and study sessions, critical path only (a fake Claude Code answers):
the first look studies the guarded copy once; a change on disk re-indexes, names the changed files,
and starts an update session told only about them; the merged model keeps the rest."""

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from secret_fixtures import PLANTED, write_repo

from umbra_engine.api import create_app

MODEL = {
    "resume": "Une petite application.",
    "blocs": [{"id": "api", "nom": "API", "type": "backend", "role": "r", "code": ["app"]}],
    "flux": [],
    "composants": [],
    "parcours": [
        {"id": "p", "nom": "Appel", "declencheur": "t", "resultat": "r",
         "etapes": [{"texte": "a répond", "composant": "api", "fichier": "app/a.py", "lignes": [1, 2]},
                    {"texte": "trop loin", "composant": "api", "fichier": "app/a.py", "lignes": [1, 99]}]}
    ],
    "modules": {"app/a.py": "renvoie 1", "app/b.py": "renvoie 2", "invented.py": "x"},
    "incertitudes": [],
}  # fmt: skip


class FakeStudy:
    def __init__(self) -> None:
        self.sessions: list[tuple[str, list[str]]] = []

    def __call__(self, prompt: str, folder: Path) -> str:
        copied = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
        self.sessions.append((prompt, copied))
        assert all(PLANTED["env_file"] not in p.read_text(encoding="utf-8") for p in folder.rglob("*.*"))
        if (folder / "UMBRA_MODEL.json").exists():
            return json.dumps({"modules": {"app/a.py": "renvoie 42"}})
        return "Voici le modèle : " + json.dumps(MODEL)


def wait_for(condition, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError("timed out")


def test_study_once_then_update_only_what_changed(settings, auth, make_repo):
    files = {
        "app/a.py": "def a():\n    return 1\n",
        "app/b.py": "def b():\n    return 2\n",
        ".env": f"API_TOKEN={PLANTED['env_file']}\n",
    }
    root = write_repo(make_repo("live"), files, git=False)
    study = FakeStudy()
    app = create_app(settings, ask=lambda prompt: "{}", study=study, live=True)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
        client.post(f"/v1/projects/{project}/index", headers=auth)  # followed: the first look starts

        def model() -> dict:
            return client.get(f"/v1/projects/{project}/model", headers=auth).json()

        wait_for(lambda: model()["state"] == "ready")
        first_prompt, copied = study.sessions[0]
        assert "MAP (cheap)" in first_prompt
        assert {"app/a.py", "app/b.py", "UMBRA_INDEX.md"} <= set(copied) and ".env" not in copied
        studied = model()["model"]
        assert set(studied["modules"]) == {"app/a.py", "app/b.py"}  # invented files are dropped
        assert [s["verifie"] for s in studied["parcours"][0]["etapes"]] == [True, False]

        events = app.state.live._events  # noqa: SLF001 — read what the pages would receive
        seen = events.latest()
        (root / "app/a.py").write_text("def a():\n    return 42\n")
        wait_for(lambda: any(e["type"] == "indexed" for _, e in events.since(project, seen)))
        assert next(e for _, e in events.since(project, seen) if e["type"] == "indexed")["changed"] == [
            "app/a.py"
        ]

        wait_for(lambda: len(study.sessions) == 2 and model()["state"] == "ready")
        update_prompt, _ = study.sessions[1]
        assert "- app/a.py" in update_prompt and "app/b.py" not in update_prompt
        updated = model()["model"]
        assert updated["modules"] == {"app/a.py": "renvoie 42", "app/b.py": "renvoie 2"}
        assert updated["parcours"] == studied["parcours"]  # untouched entries are kept

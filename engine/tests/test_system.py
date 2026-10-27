"""ADR-0007 / #103: the Level 0 project map from hard signals, without any LLM, on two repo shapes."""

import os
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from secret_fixtures import write_repo
from system_fixtures import SQLITE_UTILS, TEMPLATE

from umbra_engine.analyzers import default_analyzers
from umbra_engine.analyzers.signals import SignalsAnalyzer
from umbra_engine.api import create_app
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry


def commit(root: Path, day: str) -> None:
    env = {**os.environ, "GIT_COMMITTER_DATE": f"{day}T12:00:00", "GIT_AUTHOR_DATE": f"{day}T12:00:00"}
    base = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
    subprocess.run([*base, "checkout", "-q", "-b", "main"], check=True, env=env)
    subprocess.run([*base, "add", "."], check=True, env=env)
    subprocess.run([*base, "commit", "-qm", "init"], check=True, env=env)


def no_claude(*_: object) -> str:
    raise AssertionError("the Level 0 map must never call Claude")


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings, ask=no_claude, study=no_claude), base_url="http://127.0.0.1")


def system_of(client, auth, make_repo, name: str, files: dict[str, str], day: str) -> tuple[str, dict]:
    root = write_repo(make_repo(name), files)
    commit(root, day)
    project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
    assert client.get(f"/v1/projects/{project}/system", headers=auth).status_code == 409  # not read yet
    assert client.post(f"/v1/projects/{project}/index", headers=auth).status_code == 200
    response = client.get(f"/v1/projects/{project}/system", headers=auth)
    assert response.status_code == 200, response.text
    return project, response.json()


def by_title(system: dict) -> dict[str, dict]:
    return {b["title"]: b for b in system["boxes"]}


def links(system: dict) -> set[tuple[str, str, str, str]]:
    titles = {b["id"]: b["title"] for b in system["boxes"]}
    return {(titles[x["source"]], x["verb"], x["back"], titles[x["target"]]) for x in system["links"]}


def outputs(system: dict) -> dict[str, str]:
    titles = {b["id"]: b["title"] for b in system["boxes"]}
    return {o["label"]: titles[o["box"]] for o in system["outputs"]}


def where(proofs: list[dict]) -> list[str]:
    return [f"{p['file']}:{p['start']}" for p in proofs]


def test_web_app_server_database_and_mail_from_compose_and_code(client, auth, make_repo):
    _, system = system_of(client, auth, make_repo, "full-stack-fastapi-template", TEMPLATE, "2026-04-16")

    boxes = by_title(system)
    assert set(boxes) == {"Utilisateur", "Application web", "Serveur", "Base", "Courriel"}
    assert (boxes["Application web"]["detail"], boxes["Application web"]["folder"]) == ("React", "frontend/")
    assert (boxes["Serveur"]["detail"], boxes["Serveur"]["folder"]) == ("FastAPI · Python", "backend/app/")
    assert boxes["Base"]["detail"] == "PostgreSQL"
    assert boxes["Utilisateur"]["inferred"] and not boxes["Serveur"]["inferred"]
    assert links(system) == {
        ("Utilisateur", "clique", "affiche", "Application web"),
        ("Application web", "appelle", "répond", "Serveur"),
        ("Serveur", "écrit", "", "Base"),
        ("Serveur", "envoie", "", "Courriel"),
    }
    [call] = [x for x in system["links"] if x["verb"] == "appelle"]
    assert (
        where(call["proofs"])[0] == "frontend/src/main.tsx:4"
    )  # OpenAPI.BASE, before generated or test files
    [write] = [x for x in system["links"] if x["verb"] == "écrit"]
    assert where(write["proofs"])[:2] == [
        "backend/app/api/routes/items.py:13",
        "backend/app/api/routes/items.py:14",
    ]
    assert outputs(system) == {
        "écran mis à jour": "Application web",
        "ligne enregistrée": "Base",
        "courriel envoyé": "Courriel",
    }
    around = [a["title"] for a in system["around"]]
    assert around == [
        "Suivi des erreurs",
        "Préparation au démarrage",
        "Tests",
        "Vérifications automatiques",
        "Voir la base (Adminer)",
        "Créer un projet depuis ce modèle",
        "Documentation",
    ]  # fmt: skip  (the proxy only routes: neither a box nor a tool)
    details = {a["title"]: a["detail"] for a in system["around"]}
    assert details["Suivi des erreurs"] == "Sentry, seulement si une clé est réglée"
    assert details["Préparation au démarrage"] == "crée les tables et le premier compte"
    assert details["Tests"] == "serveur (pytest) et écrans (Playwright)"
    assert details["Vérifications automatiques"] == "2 fichiers : tests"
    assert details["Documentation"] == "installer, développer"
    assert [a["short"] for a in system["around"] if a["short"]][:2] == ["tests", "CI"]
    assert {b["title"] for b in system["boxes"] if b["opens"]} == {"Application web", "Serveur"}
    assert "compose.override.yml:4" in where(boxes["Courriel"]["proofs"])  # mailcatcher: mail caught locally
    assert (system["branch"], system["last_change"], system["actions"]) == ("main", "2026-04-16", 2)
    assert (
        system["sentence"] == "Une appli web avec comptes : on se connecte, on gère ses « items »."
    )  # what it is for, not the boxes again


def test_command_and_library_over_an_sqlite_file_without_compose(client, auth, make_repo):
    _, system = system_of(client, auth, make_repo, "sqlite-utils", SQLITE_UTILS, "2026-10-10")

    boxes = by_title(system)
    assert set(boxes) == {"Personne", "Programme Python", "Commande", "Bibliothèque", "Fichier SQLite"}
    assert [b["kind"] for b in system["boxes"] if b["kind"] == "actor"] == ["actor", "actor"]  # 2 entries
    assert (boxes["Commande"]["detail"], boxes["Commande"]["folder"]) == ("3 commandes", "cli.py")
    assert where(boxes["Commande"]["proofs"]) == ["pyproject.toml:11"]  # [project.scripts], CRLF file
    assert (boxes["Bibliothèque"]["detail"], boxes["Bibliothèque"]["folder"]) == ("Database · Table", "db.py")
    assert links(system) == {
        ("Personne", "tape", "", "Commande"),
        ("Programme Python", "importe", "", "Bibliothèque"),
        ("Commande", "appelle", "", "Bibliothèque"),
        ("Bibliothèque", "lit et écrit", "", "Fichier SQLite"),
    }
    assert where(boxes["Fichier SQLite"]["proofs"]) == ["sqlite_utils/db.py:9"]  # not the database in memory
    assert outputs(system) == {"résultat affiché": "Commande", "fichier .db modifié": "Fichier SQLite"}
    [shown] = [o for o in system["outputs"] if o["label"] == "résultat affiché"]
    assert shown["detail"] == "JSON, CSV, tableau"
    assert "sqlite_utils/cli.py:29" not in where(shown["proofs"])  # a commented print is no signal
    assert [a["title"] for a in system["around"]] == [
        "Tests",
        "Documentation",
        "Vérifications automatiques",
        "Extensions",
    ]
    assert system["actions"] == 3  # the commands of the group, not a lone @click.command
    assert system["sentence"] == (
        "Un outil en ligne de commande et une bibliothèque Python"
        " pour remplir et modifier des fichiers SQLite."
    )
    assert {b["title"] for b in system["boxes"] if b["opens"]} == {"Commande", "Bibliothèque"}


def test_every_box_and_arrow_has_its_proof(client, auth, make_repo):
    for name, files in (("tpl", TEMPLATE), ("sql", SQLITE_UTILS)):
        _, system = system_of(client, auth, make_repo, name, files, "2026-01-02")
        for element in system["boxes"] + system["links"] + system["outputs"] + system["around"]:
            assert element["proofs"], element
            assert all(p["file"] for p in element["proofs"])


def test_the_layout_is_stored_and_does_not_move(client, auth, make_repo):
    project, first = system_of(client, auth, make_repo, "tpl", TEMPLATE, "2026-04-16")
    cells = {b["id"]: (b["col"], b["row"]) for b in first["boxes"]}
    assert cells == {
        "actor:user": (0, 0), "web:frontend": (1, 0), "server:backend": (2, 0), "store:db": (3, 0),
        "mail": (2, 1),
    }  # fmt: skip
    url = f"/v1/projects/{project}/system"
    again = client.get(url, headers=auth).json()
    assert {b["id"]: (b["col"], b["row"]) for b in again["boxes"]} == cells
    assert client.post(f"/v1/projects/{project}/index", headers=auth).status_code == 200
    after = client.get(url, headers=auth).json()
    assert {b["id"]: (b["col"], b["row"]) for b in after["boxes"]} == cells


def test_signals_skip_comments_and_read_crlf_manifests(tmp_path):
    root = write_repo(
        tmp_path / "r", {"pyproject.toml": SQLITE_UTILS["pyproject.toml"], "a.py": "# import smtplib\n"}
    )
    guard = SecretGuard(root)
    analyzer = SignalsAnalyzer()
    read = {p: guard.read(p) for p in ("pyproject.toml", "a.py")}
    assert all(isinstance(f, GuardedFile) for f in read.values())
    found = {
        p: [c.object for c in analyzer.analyze(f)] for p, f in read.items() if isinstance(f, GuardedFile)
    }
    assert found == {"pyproject.toml": ["signal:script:sqlite-utils=sqlite_utils.cli:cli"], "a.py": []}


NODE_API = {
    "package.json": (
        '{\n  "name": "api",\n  "main": "src/server.js",\n'
        '  "dependencies": {\n    "express": "4.21.0",\n    "pg": "8.13.0"\n  }\n}\n'
    ),
    "src/server.js": (
        "const express = require('express')\nconst { Pool } = require('pg')\n\nconst app = express()\n"
        "app.get('/users', (req, res) => res.json([]))\napp.post('/users', (req, res) => res.json({}))\n"
    ),
}


def test_a_server_alone_is_called_by_a_client_and_its_database_is_deduced(client, auth, make_repo):
    _, system = system_of(client, auth, make_repo, "node-api", NODE_API, "2026-02-03")

    boxes = by_title(system)
    assert set(boxes) == {"Client", "Serveur", "Base"}
    assert boxes["Serveur"]["detail"] == "Express · Node.js"
    assert (boxes["Base"]["detail"], boxes["Base"]["inferred"]) == ("PostgreSQL", True)  # none declared
    assert links(system) == {("Client", "appelle", "répond", "Serveur"), ("Serveur", "lit", "", "Base")}
    assert outputs(system) == {"réponse envoyée": "Serveur"}  # nothing written: no « ligne enregistrée »
    assert system["actions"] == 2
    assert system["sentence"] == "Un serveur."  # no account, no table class: nothing more is read


def test_an_index_made_by_an_older_signals_analyzer_is_read_again(client, auth, make_repo, settings):
    project, first = system_of(client, auth, make_repo, "tpl", TEMPLATE, "2026-04-16")
    with Registry(settings) as registry:
        found = registry.get(project)
        assert found is not None
        with registry.open_store(found) as store:  # as an Umbra without today's signals left it
            older = [a for a in default_analyzers() if not isinstance(a, SignalsAnalyzer)]
            index_project(found, store, older)
    url = f"/v1/projects/{project}/system"
    assert client.get(url, headers=auth).status_code == 409  # read again, not shown with old signals
    deadline = time.monotonic() + 60
    while (response := client.get(url, headers=auth)).status_code == 409 and time.monotonic() < deadline:
        time.sleep(0.2)
    assert response.status_code == 200, response.text
    assert response.json()["sentence"] == first["sentence"]

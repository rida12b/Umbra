"""#104: `show` lights a path on the map — checked against the map and the indexed files, kept as the current
highlight, cleared by « effacer ». No Claude call anywhere (the engine never runs a model for this)."""

import pytest
from fastapi.testclient import TestClient
from system_fixtures import SQLITE_UTILS, TEMPLATE
from test_system import system_of

from umbra_engine.api import create_app

PRICE = "où j'ajoute un champ prix à Item ?"


def no_claude(*_: object) -> str:
    raise AssertionError("show must never call Claude")


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings, ask=no_claude, study=no_claude), base_url="http://127.0.0.1")


@pytest.fixture
def template(client, auth, make_repo) -> str:
    return system_of(client, auth, make_repo, "tpl", TEMPLATE, "2026-04-16")[0]


def show(client, auth, project: str, **body):
    return client.post(f"/v1/projects/{project}/show", json=body, headers=auth)


def test_a_question_lights_numbered_steps_under_their_boxes(client, auth, template):
    path = [
        {"part": "frontend/src/client/", "note": "recréé automatiquement"},
        {"part": "backend/app/models.py", "note": "ajouter le champ", "why": "ItemBase décrit les champs."},
        "./backend/app/api/routes/items.py",
        {"part": "backend/app/alembic/0002_price.py", "note": "nouvelle migration"},
    ]
    response = show(client, auth, template, caption=f"  {PRICE} ", parts=["Base"], path=path)
    assert response.status_code == 200, response.text
    lit = response.json()
    assert lit["caption"] == PRICE
    assert lit["boxes"] == ["web:frontend", "server:backend", "store:db"]  # map order; Base lit unnumbered
    steps = [(s["n"], s["box"], s["label"], s["note"]) for s in lit["steps"]]
    assert steps == [
        (1, "web:frontend", "client/", "recréé automatiquement"),
        (2, "server:backend", "models.py", "ajouter le champ"),
        (3, "server:backend", "api/routes/items.py", ""),
        (
            4,
            "server:backend",
            "alembic/0002_price.py",
            "nouvelle migration",
        ),  # new file, folder exists
    ]
    assert lit["steps"][1]["why"] == "ItemBase décrit les champs."
    assert lit["files"] == [
        "frontend/src/client/",
        "backend/app/models.py",
        "backend/app/api/routes/items.py",
        "backend/app/alembic/0002_price.py",
    ]
    assert client.get(f"/v1/projects/{template}/show", headers=auth).json() == lit


def test_a_box_is_named_by_id_title_or_folder(client, auth, template):
    lit = show(
        client, auth, template, caption="le serveur", path=["server:backend", "serveur", "frontend/"]
    ).json()
    assert [(s["box"], s["label"], s["path"]) for s in lit["steps"]] == [
        ("server:backend", "Serveur", "backend/app/"),
        ("server:backend", "Serveur", "backend/app/"),
        ("web:frontend", "Application web", "frontend/"),
    ]
    assert lit["files"] == ["backend/app/", "frontend/"]


@pytest.mark.parametrize(
    ("body", "said"),
    [
        (
            {"caption": "x", "parts": ["Serveurs"]},
            "unknown part: 'Serveurs'. Valid parts: actor:user (Utilisateur)",
        ),
        ({"caption": "x", "path": ["backend/app/nowhere/x.py"]}, "server:backend (Serveur, backend/app/)"),
        ({"caption": "x", "path": ["README.md"]}, "Valid parts:"),  # around, not in a box
        (
            {"caption": "x", "path": [f"backend/app/{n}.py" for n in "abcdefg"]},
            "path has 7 steps: show 6 at most",
        ),
        ({"caption": "  ", "parts": ["Base"]}, "caption is empty"),
        ({"caption": "x" * 121, "parts": ["Base"]}, "caption is 121 characters"),
        ({"caption": "x"}, "nothing to show"),
    ],
)
def test_what_is_not_on_the_map_is_refused_with_what_is(client, auth, template, body, said):
    response = show(client, auth, template, **body)
    assert response.status_code == 422
    assert said in response.json()["detail"]
    assert client.get(f"/v1/projects/{template}/show", headers=auth).json() is None  # nothing half-lit


def test_effacer_goes_back_to_the_plain_map_and_each_show_has_its_own_serial(client, auth, template):
    first = show(client, auth, template, caption="a", parts=["Base"]).json()
    second = show(client, auth, template, caption="b", parts=["Serveur"]).json()
    assert second["serial"] > first["serial"]
    assert client.delete(f"/v1/projects/{template}/show", headers=auth).json() == {"cleared": True}
    assert client.get(f"/v1/projects/{template}/show", headers=auth).json() is None
    assert client.delete(f"/v1/projects/{template}/show", headers=auth).json() == {"cleared": False}


def test_show_needs_the_token_and_a_known_project(client, auth, template):
    assert (
        client.post(f"/v1/projects/{template}/show", json={"caption": "x", "parts": ["Base"]}).status_code
        == 401
    )
    assert show(client, auth, "nope", caption="x", parts=["Base"]).status_code == 404


def test_on_a_command_and_a_library_the_steps_are_named_as_their_boxes(client, auth, make_repo):
    project = system_of(client, auth, make_repo, "sqlite", SQLITE_UTILS, "2026-10-10")[0]
    path = [{"part": "sqlite_utils/cli.py", "note": "ajouter la commande"}, "sqlite_utils/db.py"]
    lit = show(
        client, auth, project, caption="où j'ajoute une commande ?", parts=["Fichier SQLite"], path=path
    ).json()
    assert [(s["box"], s["label"]) for s in lit["steps"]] == [
        ("cli:sqlite-utils", "cli.py"),
        ("library:sqlite_utils", "db.py"),
    ]
    assert lit["boxes"] == ["cli:sqlite-utils", "library:sqlite_utils", "sqlite-file"]

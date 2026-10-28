"""ADR-0007 / #107: « Ce qu'on peut faire » lists a Project's actions, and one action lights its static path
on the map, traced in the code without any model: who sends it, the function that answers, what it calls,
what it writes. The same lit mechanism as a `show` from Claude Code (#104), drawn inside a box (Level 1)."""

from system_fixtures import SQLITE_UTILS
from test_card import CARD, ITEMS, SERVER
from test_system import system_of

from umbra_engine.projection.action_client import client_call

DEPS = (
    "from collections.abc import Generator\n"
    "from typing import Annotated\n"
    "\n"
    "from fastapi import Depends\n"
    "from sqlmodel import Session\n"
    "\n"
    "from app.models import User\n"
    "\n"
    "reusable_oauth2 = OAuth2PasswordBearer(tokenUrl='/api/v1/login/access-token')\n"
    "\n"
    "\n"
    "def get_db() -> Generator[Session, None, None]:\n"
    "    yield Session()\n"
    "\n"
    "\n"
    "SessionDep = Annotated[Session, Depends(get_db)]\n"
    "\n"
    "\n"
    "def get_current_user(session: SessionDep, token: str) -> User:\n"
    "    return session.get(User, token)\n"
    "\n"
    "\n"
    "CurrentUser = Annotated[User, Depends(get_current_user)]\n"
)
SDK = (
    "export class ItemsService {\n"
    "    public static readItems(data: ItemsReadItemsData) {\n"
    "        return __request(OpenAPI, {\n"
    "            method: 'GET',\n"
    "            url: '/api/v1/items/',\n"
    "        });\n"
    "    }\n"
    "\n"
    "    public static createItem(data: ItemsCreateItemData) {\n"
    "        return __request(OpenAPI, {\n"
    "            method: 'POST',\n"
    "            url: '/api/v1/items/',\n"
    "        });\n"
    "    }\n"
    "}\n"
)
ADD_ITEM = (
    "import { ItemsService } from '@/client'\n"
    "\n"
    "const AddItem = () => {\n"
    "  const mutation = useMutation({\n"
    "    mutationFn: (data: ItemCreate) =>\n"
    "      ItemsService.createItem({ requestBody: data }),\n"
    "  })\n"
    "  return <form onSubmit={submit}></form>\n"
    "}\n"
)
ACTIONS = {
    **CARD,
    "backend/app/api/deps.py": DEPS,
    "frontend/src/client/sdk.gen.ts": SDK,
    "frontend/src/components/Items/AddItem.tsx": ADD_ITEM,
}
ITEMS_PY = "backend/app/api/routes/items.py"


def line_of(text: str, needle: str) -> int:
    return next(n for n, line in enumerate(text.split("\n"), 1) if needle in line)


def actions(client, auth, project: str) -> dict:
    response = client.get(f"/v1/projects/{project}/system/actions", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def light(client, auth, project: str, action: str) -> dict:
    response = client.post(f"/v1/projects/{project}/show/action", json={"action": action}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_routes_are_listed_by_file_with_plain_words_and_their_address(client, auth, make_repo):
    project, system = system_of(client, auth, make_repo, "tpl", ACTIONS, "2026-04-16")
    found = actions(client, auth, project)
    assert found["total"] == system["actions"] == 6  # the same count as the button on the map
    assert [(g["file"], len(g["actions"])) for g in found["groups"]] == [
        (ITEMS_PY, 5), ("backend/app/api/routes/login.py", 1),
    ]  # fmt: skip
    rows = [(a["verb"], a["label"], a["address"], a["name"]) for a in found["groups"][0]["actions"]]
    assert rows[2] == ("POST", "Créer un item", "/api/v1/items/", "create_item")
    assert found["groups"][1]["actions"][0]["label"] == "Se connecter"  # the common words of signing in
    assert [g["role"] for g in found["groups"]] == ["items", "connexion"]
    assert found["groups"][0]["actions"][2]["id"] == f"{ITEMS_PY}:{line_of(ITEMS, 'def create_item(')}"


def test_creer_un_item_lights_its_real_chain_inside_the_server(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", ACTIONS, "2026-04-16")
    lit = light(client, auth, project, f"{ITEMS_PY}:{line_of(ITEMS, 'def create_item(')}")
    assert (lit["kind"], lit["caption"], lit["detail"], lit["inside"]) == (
        "path", "Créer un item", "POST /api/v1/items/", SERVER,
    )  # fmt: skip
    steps = [(s["n"], s["part"], s["note"], s["label"], s["guess"]) for s in lit["steps"]]
    sdk, add = line_of(SDK, "createItem("), line_of(ADD_ITEM, "createItem(")
    create, commit = line_of(ITEMS, "def create_item("), line_of(ITEMS, "session.commit")
    user, item = line_of(DEPS, "def get_current_user"), line_of(CARD["backend/app/models.py"], "class Item(")
    assert steps == [
        (
            1,
            "stub:web:frontend",
            "le formulaire envoie POST /api/v1/items/",
            f"AddItem.tsx:{add} → sdk.gen.ts:{sdk}",
            False,
        ),
        (2, f"{SERVER}/routes", "create_item reçoit la demande", f"routes/items.py:{create}", False),
        (
            3,
            f"{SERVER}/access",
            "vérifie la connexion, retrouve le compte",
            f"deps.py:{user} get_current_user",
            False,
        ),
        (4, f"{SERVER}/models", "Item vérifie les champs", f"models.py:{item} Item", False),
        (5, "stub:store:db", "session.commit écrit la ligne", f"routes/items.py:{commit}", False),
    ]
    assert lit["steps"][1]["chip"] == ITEMS_PY  # the items.py chip lights in Routes
    assert lit["passed"] == [f"{SERVER}/entry"]  # the request goes through main.py without a number
    assert lit["files"] == [
        "frontend/src/components/Items/AddItem.tsx", "frontend/src/client/sdk.gen.ts", "backend/app/main.py",
        ITEMS_PY, "backend/app/api/deps.py", "backend/app/models.py",
    ]  # fmt: skip
    shown = client.get(f"/v1/projects/{project}/show", headers=auth).json()
    assert shown["serial"] == lit["serial"]  # the same current highlight as a `show`: every tab gets it


def test_a_command_goes_through_the_library_and_a_guess_says_so(client, auth, make_repo):
    project, system = system_of(client, auth, make_repo, "sqlite", SQLITE_UTILS, "2026-10-10")
    found = actions(client, auth, project)
    assert found["total"] == system["actions"] == 3
    assert [a["address"] for a in found["groups"][0]["actions"]] == ["tables", "insert", "rows"]
    assert [a["label"] for a in found["groups"][0]["actions"]] == [
        "Lister les tables",
        "Insérer",
        "Lister les lignes",
    ]  # from the command names alone (#108)
    insert = found["groups"][0]["actions"][1]
    lit = light(client, auth, project, insert["id"])
    assert (lit["caption"], lit["inside"]) == ("Insérer", "library:sqlite_utils")
    steps = [(s["part"], s["note"], s["label"], s["guess"]) for s in lit["steps"]]
    assert steps[0] == (
        "stub:cli:sqlite-utils",
        "insert lance la commande",
        f"sqlite_utils/cli.py:{insert['line']}",
        False,
    )
    assert steps[1][0] == "library:sqlite_utils/data" and steps[1][2].endswith("Database")
    assert steps[-1][0] == "stub:sqlite-file" and steps[-1][3] is True  # inside Database: supposé
    assert lit["steps"][-1]["why"].startswith("supposé")


def test_an_action_not_in_the_list_is_not_found(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", ACTIONS, "2026-04-16")
    response = client.post(f"/v1/projects/{project}/show/action", json={"action": "x.py:1"}, headers=auth)
    assert response.status_code == 404


def test_the_card_gives_each_route_its_action(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", ACTIONS, "2026-04-16")
    params = {"box": SERVER, "part": f"{SERVER}/routes", "file": ITEMS_PY}
    card = client.get(f"/v1/projects/{project}/system/card", params=params, headers=auth).json()
    ids = {a["id"] for g in actions(client, auth, project)["groups"] for a in g["actions"]}
    assert {f["action"] for f in card["functions"] if f["verb"]} <= ids  # « chemin → » lights a listed action


def test_show_can_name_parts_inside_a_box(client, auth, make_repo):
    """#105 deferral: Claude Code may light parts of one box (« Serveur/Contrôle d'accès »), drawn in it."""
    project, _ = system_of(client, auth, make_repo, "tpl", ACTIONS, "2026-04-16")
    path = [{"part": "Serveur/Contrôle d'accès", "note": "vérifie le jeton"}, ITEMS_PY, "Serveur/Base"]
    body = {"caption": "qui vérifie la connexion ?", "path": path}
    response = client.post(f"/v1/projects/{project}/show", json=body, headers=auth)
    assert response.status_code == 200, response.text
    lit = response.json()
    assert (lit["kind"], lit["inside"]) == ("question", SERVER)
    assert [(s["part"], s["label"]) for s in lit["steps"]] == [
        (f"{SERVER}/access", "Contrôle d'accès"), (f"{SERVER}/routes", "items.py"), ("stub:store:db", "Base"),
    ]  # fmt: skip
    wrong = client.post(f"/v1/projects/{project}/show", json={**body, "path": ["Serveur/Nope"]}, headers=auth)
    assert wrong.status_code == 422 and "Serveur/Contrôle d'accès" in wrong.json()["detail"]


def test_the_client_line_is_the_one_with_the_same_verb():
    texts = {"web/src/client/sdk.gen.ts": SDK, "web/src/components/Items/AddItem.tsx": ADD_ITEM}
    found = client_call(sorted(texts), texts.get, "POST", "/api/v1/items/")
    assert found is not None
    assert (found.file, found.line, found.name) == (
        "web/src/client/sdk.gen.ts",
        line_of(SDK, "createItem("),
        "createItem",
    )
    assert found.caller == ("web/src/components/Items/AddItem.tsx", line_of(ADD_ITEM, "createItem("))
    assert (
        client_call(sorted(texts), texts.get, "DELETE", "/api/v1/items/") is None
    )  # nothing found, nothing said

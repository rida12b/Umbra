"""ADR-0007 / #106: the card of a part or of one file (Level 2): four lines and its functions with their
line, from hard signals only. Route files are cut down from full-stack-fastapi-template (lines as there)."""

from system_fixtures import SQLITE_UTILS
from test_inside import INSIDE, inside
from test_system import system_of

from umbra_engine.projection import card_routes

ITEMS = (
    "import uuid\n"
    "from typing import Any\n"
    "\n"
    "from fastapi import APIRouter, HTTPException\n"
    "from sqlmodel import col, func, select\n"
    "\n"
    "from app.api.deps import CurrentUser, SessionDep\n"
    "from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message\n"
    "\n"
    'router = APIRouter(prefix="/items", tags=["items"])\n'
    "\n"
    "\n"
    '@router.get("/", response_model=ItemsPublic)\n'
    "def read_items(\n"
    "    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100\n"
    ") -> Any:\n"
    "    return session.exec(select(Item).where(Item.owner_id == current_user.id)).all()\n"
    "\n"
    "\n"
    '@router.get("/{id}", response_model=ItemPublic)\n'
    "def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:\n"
    "    item = session.get(Item, id)\n"
    "    if not item:\n"
    '        raise HTTPException(status_code=404, detail="Item not found")\n'
    "    return item\n"
    "\n"
    "\n"
    '@router.post("/", response_model=ItemPublic)\n'
    "def create_item(\n"
    "    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate\n"
    ") -> Any:\n"
    "    item = Item.model_validate(item_in, update={'owner_id': current_user.id})\n"
    "    session.add(item)\n"
    "    session.commit()\n"
    "    return item\n"
    "\n"
    "\n"
    '@router.put("/{id}", response_model=ItemPublic)\n'
    "def update_item(*, session: SessionDep, id: uuid.UUID, item_in: ItemUpdate) -> Any:\n"
    "    return None\n"
    "\n"
    "\n"
    '@router.delete("/{id}")\n'
    "def delete_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Message:\n"
    '    return Message(message="Item deleted successfully")\n'
)
MODELS = (
    "from sqlmodel import Field, SQLModel\n"
    "\n"
    "\n"
    "class User(SQLModel, table=True):\n    hashed_password: str\n\n\n"
    "class Item(SQLModel, table=True):\n    title: str\n\n\n"
    "class ItemCreate(SQLModel):\n    title: str\n\n\n"
    "class ItemUpdate(SQLModel):\n    title: str\n\n\n"
    "class ItemPublic(SQLModel):\n    id: int\n\n\n"
    "class ItemsPublic(SQLModel):\n    count: int\n\n\n"
    "class Message(SQLModel):\n    message: str\n"
)
CARD = {
    **INSIDE,
    "backend/app/api/routes/items.py": ITEMS,
    "backend/app/models.py": MODELS,
    "backend/app/api/deps.py": INSIDE["backend/app/api/deps.py"] + "\n\nCurrentUser = Annotated[User, 1]\n",
    "backend/app/main.py": INSIDE["backend/app/main.py"].replace(
        "prefix='/api/v1'", "prefix=settings.API_V1_STR"
    ),
    "backend/app/core/config.py": (
        "class Settings(BaseSettings):\n"
        "    model_config = SettingsConfigDict(env_file='../.env')\n"
        '    API_V1_STR: str = "/api/v1"\n'
    ),
}
SERVER = "server:backend"


def card(client, auth, project: str, box: str, part: str, file: str = "") -> dict:
    params = {"box": box, "part": part, "file": file}
    response = client.get(f"/v1/projects/{project}/system/card", params=params, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def said(found: dict) -> dict[str, str]:
    """Each line as one string: mono words in backticks, deduced words with a trailing « ~ »."""
    return {
        line["label"]: " ".join(
            (f"`{w['text']}`" if w["mono"] else w["text"]) + ("~" if w["inferred"] else "")
            for w in line["words"]
        )
        for line in found["lines"]
    }


def test_a_route_file_says_what_it_receives_returns_who_calls_it_and_its_routes(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", CARD, "2026-04-16")
    routes = next(p["id"] for p in inside(client, auth, project, SERVER)["parts"] if p["title"] == "Routes")
    found = card(client, auth, project, SERVER, routes, "backend/app/api/routes/items.py")
    assert (found["title"], found["folder"], found["path"]) == (
        "items.py", "backend/app/api/routes/", "backend/app/api/routes/items.py",
    )  # fmt: skip
    assert found["sentence"] == "Les adresses pour lister, voir, créer, modifier et supprimer ses items."
    assert [line["label"] for line in found["lines"]] == ["Reçoit", "Renvoie", "Appelé par", "Appelle"]
    assert said(found) == {
        "Reçoit": "GET · POST · PUT · DELETE `/api/v1/items/` + connexion",
        "Renvoie": "un item, une liste d'items, un message, ou une erreur",
        "Appelé par": "Application web",
        "Appelle": "Contrôle d'accès · Modèles · Base",
    }
    assert found["section"] == "Ce qu'on peut faire ici"
    assert [(f["verb"], f["label"], f["name"], f["line"], f["path"]) for f in found["functions"]] == [
        ("GET", "Lister ses items", "read_items", 14, "/api/v1/items/"),
        ("GET", "Voir un item", "read_item", 21, "/api/v1/items/{id}"),
        ("POST", "Créer un item", "create_item", 29, "/api/v1/items/"),
        ("PUT", "Modifier un item", "update_item", 39, "/api/v1/items/{id}"),
        ("DELETE", "Supprimer un item", "delete_item", 44, "/api/v1/items/{id}"),
    ]
    assert found["open_file"] == "backend/app/api/routes/items.py"


def test_a_part_card_names_the_parts_and_neighbours_it_meets_and_lists_its_functions(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", CARD, "2026-04-16")
    data = next(
        p["id"] for p in inside(client, auth, project, SERVER)["parts"] if p["title"] == "Accès aux données"
    )
    found = card(client, auth, project, SERVER, data)
    assert (found["title"], found["file"], found["path"]) == ("Accès aux données", "", "backend/app/crud.py")
    assert said(found)["Appelé par"] == "Routes"
    assert said(found)["Appelle"] == "Contrôle d'accès · Modèles · Base"
    assert said(found)["Reçoit"] == ""  # `from app import crud`: no name taken, nothing invented
    assert found["section"] == "Ses fonctions"
    assert [(f["name"], f["line"], f["verb"]) for f in found["functions"]] == [
        ("create_user", 5, ""), ("get_user_by_email", 10, ""),
    ]  # fmt: skip
    entry = card(client, auth, project, SERVER, f"{SERVER}/entry")
    assert said(entry)["Appelé par"].startswith("Application web")  # the stub that comes in, as on Level 1


def test_a_library_part_lists_its_methods_and_the_file_it_writes(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "sqlite", SQLITE_UTILS, "2026-10-10")
    found = card(client, auth, project, "library:sqlite_utils", "library:sqlite_utils/data")
    assert found["path"] == "sqlite_utils/db.py"
    assert said(found)["Reçoit"] == "appels à `Database`"
    assert said(found)["Appelé par"] == "Porte d'entrée · Commande"
    assert said(found)["Appelle"].endswith("Fichier SQLite")
    assert [(f["name"], f["line"]) for f in found["functions"]] == [
        ("Database.__init__", 5), ("Database.table_names", 11), ("Database.__getitem__", 14),
        ("Table.__init__", 23), ("Table.insert_all", 27), ("Table.rows", 32),
    ]  # fmt: skip


def test_a_part_or_file_not_drawn_is_not_found(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", CARD, "2026-04-16")
    url = f"/v1/projects/{project}/system/card"
    for params in (
        {"box": SERVER, "part": f"{SERVER}/nope"},
        {"box": SERVER, "part": f"{SERVER}/routes", "file": "backend/app/crud.py"},
        {"box": "nope", "part": "nope/routes"},
    ):
        assert client.get(url, params=params, headers=auth).status_code == 404


def test_plain_words_only_for_a_plain_shape():
    assert card_routes.label("GET", "/api/v1/items/") == "Lister les items"
    assert card_routes.label("GET", "/api/v1/items/", owned=True) == "Lister ses items"
    assert card_routes.label("DELETE", "/api/v1/items/{id}") == "Supprimer un item"
    assert card_routes.label("GET", "/api/v1/users/me") == ""  # not a plain shape: Claude names it (#108)
    assert card_routes.label("POST", "/api/v1/login/access-token") == ""
    assert card_routes.common_address(["/api/v1/login/x", "/api/v1/password-recovery/{e}"]) == "/api/v1/"
    assert (
        card_routes.answer_words(["UsersPublic"], {"UserPublic", "UsersPublic"}, False)
        == "une liste de users"
    )


def test_a_library_card_leads_with_what_others_use_most() -> None:
    """sqlite-utils: « Reçoit » opened on DEFAULT · AlterError; the classes everyone imports come first."""
    from umbra_engine.projection.card import _most_taken

    taken = ["DEFAULT", "Database", "AlterError", "Table", "Database", "Table", "Database"]
    assert _most_taken(taken) == ["Database", "Table", "DEFAULT", "AlterError"]


def test_private_helpers_come_after_the_public_functions() -> None:
    from umbra_engine.projection.card import _private

    assert [_private(n) for n in ("_check_constraint_sql", "__init__", "insert_all")] == [True, False, False]

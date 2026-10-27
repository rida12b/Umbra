"""ADR-0007 / #105: the inside of a box (Level 1), ≤ 7 parts and grey stubs, from hard signals only."""

from system_fixtures import SQLITE_UTILS, TEMPLATE
from test_system import system_of

ROUTES = (
    "from fastapi import APIRouter\n"
    "\n"
    "from app.api.deps import get_db\n"
    "from app.models import Item\n"
    "\n"
    "router = APIRouter(prefix='/items')\n"
    "\n"
    "\n"
    "@router.post('/')\n"
    "def create_item(session, item: Item):\n"
    "    session.add(item)\n"
    "    session.commit()\n"
    "    return item\n"
)
INSIDE = {
    **TEMPLATE,
    "backend/app/api/main.py": (
        "from fastapi import APIRouter\n"
        "\n"
        "from app.api.routes import items, login\n"
        "\n"
        "api_router = APIRouter()\n"
        "api_router.include_router(items.router)\n"
    ),
    "backend/app/api/routes/items.py": ROUTES,
    "backend/app/api/routes/login.py": (
        "from fastapi.security import OAuth2PasswordRequestForm\n"
        "\n"
        "from app import crud\n"
        "from app.api.deps import get_db\n"
        "from app.utils import send_email\n"
        "\n"
        "router = APIRouter()\n"
        "\n"
        "\n"
        "@router.post('/login/access-token')\n"
        "def login(form: OAuth2PasswordRequestForm):\n"
        "    send_email('a', 'b')\n"
    ),
    "backend/app/core/security.py": (
        "import jwt\n\n\ndef create_access_token(subject):\n    return jwt.encode({}, 'k')\n"
    ),
    "backend/app/crud.py": (
        "from app.core.security import create_access_token\n"
        "from app.models import User\n"
        "\n"
        "\n"
        "def create_user(session, user):\n"
        "    session.add(user)\n"
        "    session.commit()\n"
        "\n"
        "\n"
        "def get_user_by_email(session, email):\n"
        "    return None\n"
    ),
    "backend/app/core/config.py": (
        "class Settings(BaseSettings):\n    model_config = SettingsConfigDict(env_file='../.env')\n"
    ),
    "backend/app/alembic/versions/e2412789c190_initialize_models.py": "def upgrade():\n    pass\n",
    "frontend/src/main.tsx": (
        'import ReactDOM from "react-dom/client"\n'
        'import { OpenAPI } from "./client"\n'
        'import { routeTree } from "./routeTree.gen"\n'
        "\n"
        "OpenAPI.BASE = import.meta.env.VITE_API_URL\n"
        "\n"
        'ReactDOM.createRoot(document.getElementById("root")!).render(<App />)\n'
    ),
    "frontend/src/routeTree.gen.ts": (
        "import { Route as LoginRoute } from './routes/login'\n"
        "import { Route as ItemsRoute } from './routes/_layout/items'\n"
    ),
    "frontend/src/routes/login.tsx": (
        "import useAuth from '@/hooks/useAuth'\n\nexport const Route = createFileRoute('/login')({})\n"
    ),
    "frontend/src/routes/_layout/items.tsx": (
        "import AddItem from '@/components/Items/AddItem'\n\n"
        "export const Route = createFileRoute('/_layout/items')({})\n"
    ),
    "frontend/src/components/Items/AddItem.tsx": (
        "import { ItemsService } from '@/client'\nimport { Button } from '@/components/ui/button'\n"
    ),
    "frontend/src/components/Items/columns.tsx": "export const columns = []\n",
    "frontend/src/components/ui/button.tsx": "export function Button() {}\n",
    "frontend/src/hooks/useAuth.ts": (
        "import { LoginService } from '@/client'\n"
        "\n"
        "export default function useAuth() {\n"
        "  localStorage.setItem('access_token', 'x')\n"
        "}\n"
    ),
    "frontend/src/client/index.ts": "export * from './sdk.gen'\n",
}


def inside(client, auth, project: str, box: str) -> dict:
    response = client.get(f"/v1/projects/{project}/system/inside", params={"box": box}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def parts(found: dict) -> list[tuple[str, str, list[str]]]:
    return [(p["title"], p["detail"], p["folders"]) for p in found["parts"] if p["kind"] != "stub"]


def stubs(found: dict) -> dict[str, tuple[str, str, str]]:
    return {
        p["neighbour"]: (p["side"], p["title"], p["detail"]) for p in found["parts"] if p["kind"] == "stub"
    }


def arrows(found: dict) -> set[tuple[str, str, str]]:
    names = {
        p["id"]: p["title"] if p["kind"] != "stub" else p["detail"].removeprefix("◉ ") for p in found["parts"]
    }
    for p in found["parts"]:
        if p["kind"] == "stub" and p["title"].startswith("vers "):
            names[p["id"]] = p["title"].removeprefix("vers ")
    return {(names[x["source"]], x["verb"], names[x["target"]]) for x in found["links"]}


def test_inside_the_server_entry_routes_access_models_data_and_stubs(client, auth, make_repo):
    project, system = system_of(client, auth, make_repo, "tpl", INSIDE, "2026-04-16")
    assert {b["title"]: b["opens"] for b in system["boxes"]}["Serveur"] is True
    found = inside(client, auth, project, "server:backend")
    assert (found["title"], found["folder"]) == ("Serveur", "backend/app/")
    assert (
        found["sentence"]
        == "Reçoit les appels de l'application web, vérifie qui appelle, lit et écrit la base."
    )
    assert parts(found) == [
        ("Porte d'entrée", "", ["main.py"]),
        ("Routes", "", ["api/routes/"]),
        ("Contrôle d'accès", "", ["api/deps.py", "core/security.py"]),
        ("Modèles", "User · Item", ["models.py"]),
        ("Accès aux données", "comptes", ["crud.py"]),
    ]
    routes = next(p for p in found["parts"] if p["title"] == "Routes")
    assert [c["file"] for c in routes["chips"]] == [
        "backend/app/api/routes/items.py",
        "backend/app/api/routes/login.py",
    ]
    assert stubs(found) == {
        "web:frontend": ("in", "depuis", "Application web"),
        "store:db": ("out", "vers Base", "◉ ligne enregistrée"),
        "mail": ("out", "vers Courriel", "◉ courriel envoyé"),
    }
    assert arrows(found) == {
        ("Application web", "appelle", "Porte d'entrée"),
        ("Porte d'entrée", "passe", "Routes"),
        ("Routes", "vérifie la connexion", "Contrôle d'accès"),
        ("Routes", "valide", "Modèles"),
        ("Routes", "utilise", "Accès aux données"),  # `from app import crud`: the module, not the package
        ("Routes", "écrit", "Base"),
        ("Accès aux données", "écrit (comptes)", "Base"),
        ("Routes", "envoie", "Courriel"),  # through the mail helper `utils.py`, which is no part of its own
    }
    passes = next(x for x in found["links"] if x["verb"] == "passe")
    assert passes["proofs"][0] == {"file": "backend/app/main.py", "start": 11, "end": 11}
    assert [(a["title"], a["detail"]) for a in found["around"]] == [
        ("Réglages", "lit le fichier .env"),
        ("Migrations", "créent et modifient les tables, 1 fichiers"),
    ]


def test_inside_the_web_app_start_pages_screens_client_and_sign_in(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", INSIDE, "2026-04-16")
    found = inside(client, auth, project, "web:frontend")
    assert (found["folder"], found["sentence"]) == (
        "frontend/src/",
        "Les écrans dans le navigateur : ils affichent les pages et appellent le serveur.",
    )
    assert parts(found) == [
        ("Démarrage", "", ["main.tsx"]),
        ("Pages", "connexion · items", ["routes/"]),
        ("Écrans", "Items", ["components/"]),
        ("Client", "généré", ["client/"]),
        ("Connexion", "garde la preuve", ["hooks/useAuth.ts"]),
    ]
    assert arrows(found) == {
        ("Utilisateur", "ouvre", "Démarrage"),
        ("Démarrage", "branche", "Pages"),  # through the generated route tree
        ("Pages", "affiche", "Écrans"),  # `@/components/…`: the src alias
        ("Écrans", "appelle", "Client"),
        ("Pages", "qui est connecté ?", "Connexion"),
        ("Connexion", "joint la preuve", "Client"),
        ("Client", "envoie", "Serveur"),
    }
    screens = next(p["id"] for p in found["parts"] if p["title"] == "Écrans")
    assert [(o["box"], o["label"]) for o in found["outputs"]] == [(screens, "écran mis à jour")]
    assert [a["title"] for a in found["around"]] == ["Tests des écrans", "Kit d'interface"]


def test_inside_a_library_and_a_command_without_one(client, auth, make_repo):
    project, system = system_of(client, auth, make_repo, "sqlite", SQLITE_UTILS, "2026-10-10")
    opens = {b["title"]: b["opens"] for b in system["boxes"]}
    assert (opens["Bibliothèque"], opens["Commande"]) == (True, False)  # one file: nothing to zoom into
    missing = client.get(
        f"/v1/projects/{project}/system/inside", params={"box": "cli:sqlite-utils"}, headers=auth
    )
    assert missing.status_code == 404
    found = inside(client, auth, project, "library:sqlite_utils")
    assert parts(found)[:2] == [
        ("Porte d'entrée", "", ["__init__.py"]),
        ("Accès aux données", "Database · Table", ["db.py"]),
    ]
    assert stubs(found) == {
        "actor:program": ("in", "depuis", "Programme Python"),
        "cli:sqlite-utils": ("in", "depuis", "Commande"),
        "sqlite-file": ("out", "vers Fichier SQLite", "◉ fichier .db modifié"),
    }
    assert ("Accès aux données", "lit et écrit", "Fichier SQLite") in arrows(found)
    assert ("Porte d'entrée", "expose", "Accès aux données") in arrows(found)


def test_every_part_and_stub_has_its_proof_and_the_cells_never_move(client, auth, make_repo):
    project, _ = system_of(client, auth, make_repo, "tpl", INSIDE, "2026-04-16")
    first = inside(client, auth, project, "server:backend")
    assert all(p["proofs"] for p in first["parts"]) and all(x["proofs"] for x in first["links"])
    assert len([p for p in first["parts"] if p["kind"] != "stub"]) <= 7
    assert client.post(f"/v1/projects/{project}/index", headers=auth).status_code == 200
    again = inside(client, auth, project, "server:backend")
    cells = [(p["id"], p["col"], p["row"]) for p in first["parts"]]
    assert [(p["id"], p["col"], p["row"]) for p in again["parts"]] == cells
    unknown = client.get(f"/v1/projects/{project}/system/inside", params={"box": "nope"}, headers=auth)
    assert unknown.status_code == 404

"""The real engine and web app on a small fixture Project, for browser tests.

Claude Code is replaced by a fixed model (no network, no subscription): the tests check what the
web app does with a model, not what Claude writes. Writes e2e/.state.json (Project id, token file).
Usage: python ui/e2e/server.py PORT
"""

import json
import sys
import tempfile
from pathlib import Path

import uvicorn

from umbra_engine.api import create_app
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry
from umbra_engine.settings import Settings

FILES = {
    "compose.yml": "services:\n  api:\n    build: ./api\n    depends_on: [db]\n  db:\n    image: postgres:16\n",
    "api/Dockerfile": "FROM python:3.12\n",
    "api/app/main.py": "from .orders import create_order\n\n\ndef handle(request):\n    return create_order(request)\n",
    "api/app/orders.py": (
        "from .store import save\n\n\ndef validate(order):\n    return bool(order)\n\n\n"
        "def create_order(order):\n    validate(order)\n    return save(order)\n"
    ),
    "api/app/store.py": "def save(order):\n    return order\n",
    "web/src/app.ts": "export function submit(order: string) {\n  return fetch('/orders', { body: order })\n}\n",
}

MODEL = {
    "resume": "Une boutique de test : le site envoie une commande, l'API la valide et l'enregistre.",
    "blocs": [
        {"id": "user", "nom": "Client", "type": "user", "role": "Passe une commande.", "code": []},
        {"id": "web", "nom": "Site web", "type": "frontend", "role": "Envoie la commande.", "code": ["web"]},
        {"id": "api", "nom": "API commandes", "type": "backend", "role": "Valide et enregistre.", "code": ["api/app"]},
        {"id": "db", "nom": "Base PostgreSQL", "type": "database", "role": "Garde les commandes.", "code": []},
    ],
    "flux": [
        {"de": "user", "vers": "web", "quoi": "clic sur Commander"},
        {"de": "web", "vers": "api", "quoi": "POST /orders"},
        {"de": "api", "vers": "db", "quoi": "INSERT commande"},
    ],
    "composants": [
        {"id": "orders", "nom": "Commandes", "bloc": "api", "role": "Crée les commandes.",
         "expose": [{"quoi": "create_order", "fichier": "api/app/orders.py", "lignes": [8, 10]}],
         "fichiers": ["api/app/orders.py"]},
    ],
    "parcours": [
        {"id": "order", "nom": "Passer une commande", "declencheur": "Le client clique sur Commander.",
         "etapes": [
             {"texte": "Le site envoie la commande.", "composant": "web", "touche": ["api"],
              "fichier": "web/src/app.ts", "lignes": [1, 3]},
             {"texte": "L'API valide puis enregistre.", "composant": "orders", "touche": ["db"],
              "fichier": "api/app/orders.py", "lignes": [8, 10]},
         ],
         "resultat": "La commande est enregistrée."},
    ],
    "modules": {"api/app/orders.py": "Crée et valide les commandes.", "api/app/main.py": "Point d'entrée de l'API."},
    "dossiers": {"api/app": "Le code de l'API."},
    "incertitudes": [],
}  # fmt: skip


def main() -> None:
    port = int(sys.argv[1])
    work = Path(tempfile.mkdtemp(prefix="umbra-e2e-"))
    root = work / "shop"
    for rel, text in FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    settings = Settings(home=work / "home", port=port)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
    app = create_app(
        settings, ask=lambda prompt: "{}", study=lambda prompt, folder: json.dumps(MODEL)
    )
    state = {"project": project.id, "token": str(settings.home / "token")}
    (Path(__file__).parent / ".state.json").write_text(json.dumps(state), encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()

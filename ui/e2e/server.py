"""The real engine and web app on a small fixture Project, for browser tests.

Claude Code is replaced by fakes that fail (no network, no subscription): the map is built from hard
signals only, and nothing the page does may call Claude. Writes e2e/.state.json (Project id, token file).
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
    "compose.yml": (
        "services:\n  api:\n    build: ./api\n    depends_on: [db]\n  web:\n    build: ./web\n"
        "  db:\n    image: postgres:16\n"
    ),
    "api/Dockerfile": "FROM python:3.12\n",
    "api/pyproject.toml": '[project]\nname = "shop"\ndependencies = ["fastapi", "sqlalchemy"]\n',
    "api/app/main.py": (
        "from fastapi import FastAPI\n\nfrom .orders import create_order\n\napp = FastAPI()\n\n\n"
        "@app.post('/orders')\ndef post_order(order):\n    return create_order(order)\n"
    ),
    "api/app/orders.py": (
        "from sqlalchemy.orm import Session\n\n\ndef create_order(order, session: Session):\n"
        "    session.add(order)\n    session.commit()\n    return order\n\n\n"
        'class Order(Base):\n    __tablename__ = "orders"\n'
    ),
    "web/Dockerfile": "FROM node:22\n",
    "web/package.json": '{\n  "name": "web",\n  "dependencies": {\n    "react": "19.0.0"\n  }\n}\n',
    "web/src/main.tsx": "import { createRoot } from 'react-dom/client'\n\ncreateRoot(document.body).render(null)\n",
    "web/src/app.ts": "export function submit(order: string) {\n  return fetch('/orders', { body: order })\n}\n",
    "README.md": "# Shop\n",
}


def no_claude(*_: object) -> str:
    raise RuntimeError("the browser tests must never call Claude")


def write(root: Path) -> None:
    for rel, text in FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def main() -> None:
    port = int(sys.argv[1])
    work = Path(tempfile.mkdtemp(prefix="umbra-e2e-"))
    root = work / "shop"
    write(root)
    spare = (
        work / "spare"
    )  # a second copy, not registered: a test adds it while the engine runs (#85)
    write(spare)
    settings = Settings(home=work / "home", port=port)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
    app = create_app(settings, ask=no_claude, study=no_claude)
    state = {"project": project.id, "token": str(settings.home / "token"), "spare": str(spare)}
    (Path(__file__).parent / ".state.json").write_text(json.dumps(state), encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()

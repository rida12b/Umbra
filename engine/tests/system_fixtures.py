"""Two Project shapes for the Level 0 map, cut down from real repos (lines kept as written there):
full-stack-fastapi-template (compose: web app, server, database, mail) and sqlite-utils (no compose:
a command and a library over an SQLite file)."""

TEMPLATE = {
    "compose.yml": (
        "services:\n"
        "\n"
        "  db:\n"
        "    image: postgres:18\n"
        "    restart: always\n"
        "\n"
        "  adminer:\n"
        "    image: adminer\n"
        "    depends_on:\n"
        "      - db\n"
        "\n"
        "  prestart:\n"
        "    build:\n"
        "      context: .\n"
        "      dockerfile: backend/Dockerfile\n"
        "    depends_on:\n"
        "      - db\n"
        "    command: bash scripts/prestart.sh\n"
        "\n"
        "  backend:\n"
        "    build:\n"
        "      context: .\n"
        "      dockerfile: backend/Dockerfile\n"
        "    depends_on:\n"
        "      - db\n"
        "      - prestart\n"
        "\n"
        "  frontend:\n"
        "    build:\n"
        "      context: .\n"
        "      dockerfile: frontend/Dockerfile\n"
    ),
    "compose.override.yml": (
        "services:\n"
        "  proxy:\n"
        "    image: traefik:3.6\n"
        "  mailcatcher:\n"
        "    image: schickling/mailcatcher\n"
        "  playwright:\n"
        "    build:\n"
        "      context: .\n"
        "      dockerfile: frontend/Dockerfile.playwright\n"
    ),
    "package.json": '{\n  "name": "fastapi-full-stack-template",\n  "workspaces": ["frontend"]\n}\n',
    "pyproject.toml": '[tool.uv.workspace]\nmembers = ["backend"]\n',
    "copier.yml": "project_name:\n  type: str\n",
    "README.md": "# Full Stack FastAPI Template\n",
    "development.md": "# Development\n",
    ".github/workflows/test-backend.yml": "name: Test Backend\non: push\n",
    ".github/workflows/playwright.yml": "name: Playwright Tests\non: push\n",
    "backend/Dockerfile": "FROM python:3.10\nWORKDIR /app/\n",
    "backend/pyproject.toml": (
        '[project]\nname = "app"\nversion = "0.1.0"\ndependencies = [\n'
        '    "fastapi[standard]<1.0.0,>=0.114.2",\n    "emails<1.0,>=0.6",\n'
        '    "psycopg[binary]<4.0.0,>=3.1.13",\n    "sqlmodel<1.0.0,>=0.0.21",\n'
        '    "sentry-sdk[fastapi]>=2.0.0,<3.0.0",\n]\n'
    ),
    "backend/app/__init__.py": "",
    "backend/app/main.py": (
        "import sentry_sdk\n"
        "from fastapi import FastAPI\n"
        "\n"
        "from app.api.main import api_router\n"
        "\n"
        "sentry_sdk.init(dsn=None, enable_tracing=True)\n"
        "\n"
        "app = FastAPI(title='app')\n"
        "\n"
        "app.include_router(api_router, prefix='/api/v1')\n"
    ),
    "backend/app/api/__init__.py": "",
    "backend/app/api/main.py": "from fastapi import APIRouter\n\napi_router = APIRouter()\n",
    "backend/app/api/deps.py": (
        "from collections.abc import Generator\n"
        "\n"
        "from sqlmodel import Session\n"
        "\n"
        "\n"
        "def get_db() -> Generator[Session, None, None]:\n"
        "    yield Session()\n"
    ),
    "backend/app/api/routes/__init__.py": "",
    "backend/app/api/routes/items.py": (
        "from fastapi import APIRouter\n"
        "\n"
        "router = APIRouter(prefix='/items')\n"
        "\n"
        "\n"
        "@router.get('/')\n"
        "def read_items(session):\n"
        "    return []\n"
        "\n"
        "\n"
        "@router.post('/')\n"
        "def create_item(session, item):\n"
        "    session.add(item)\n"
        "    session.commit()\n"
        "    return item\n"
    ),
    "backend/app/utils.py": (
        "import logging\n"
        "\n"
        "import emails  # type: ignore[import-untyped]\n"
        "\n"
        "\n"
        "def send_email(email_to, subject):\n"
        "    message = emails.Message(subject=subject)\n"
        "    return message.send(to=email_to)\n"
    ),
    "backend/tests/conftest.py": "import pytest\n",
    "backend/tests/api/test_items.py": "def test_create_item():\n    assert True\n",
    "frontend/Dockerfile": "FROM node:24\n",
    "frontend/package.json": (
        '{\n  "name": "frontend",\n  "dependencies": {\n    "axios": "1.13.5",\n'
        '    "react": "^19.1.1",\n    "react-dom": "^19.2.3"\n  },\n'
        '  "devDependencies": {\n    "@playwright/test": "1.58.2"\n  }\n}\n'
    ),
    "frontend/playwright.config.ts": "export default { use: { baseURL: 'http://localhost:5173' } }\n",
    "frontend/src/main.tsx": (
        'import ReactDOM from "react-dom/client"\n'
        'import { OpenAPI } from "./client"\n'
        "\n"
        "OpenAPI.BASE = import.meta.env.VITE_API_URL\n"
        "\n"
        'ReactDOM.createRoot(document.getElementById("root")!).render(<App />)\n'
    ),
    "frontend/src/client/sdk.gen.ts": "export class ItemsService {}\n",
    "frontend/tests/items.spec.ts": "test('items', async () => {})\n",
}

SQLITE_UTILS = {
    "pyproject.toml": (
        "[project]\r\n"
        'name = "sqlite-utils"\r\n'
        'description = "CLI tool and Python library for manipulating SQLite databases"\r\n'
        "dependencies = [\r\n"
        '    "click>=8.3.1",\r\n'
        '    "pluggy",\r\n'
        '    "tabulate",\r\n'
        "]\r\n"
        "\r\n"
        "[project.scripts]\r\n"
        'sqlite-utils = "sqlite_utils.cli:cli"\r\n'
        "\r\n"
        "[build-system]\r\n"
        'requires = ["setuptools>=77"]\r\n'
    ),
    "README.md": "# sqlite-utils\n",
    "docs/cli.rst": "CLI\n===\n",
    ".github/workflows/test.yml": "name: Test\non: push\n",
    "sqlite_utils/__init__.py": (
        "from .db import Database\n"
        "from .utils import suggest_column_types\n"
        "\n"
        '__all__ = ["Database", "suggest_column_types"]\n'
    ),
    "sqlite_utils/__main__.py": "from .cli import cli\n\nif __name__ == '__main__':\n    cli()\n",
    "sqlite_utils/cli.py": (
        "import csv as csv_std\n"
        "import json\n"
        "\n"
        "import click\n"
        "import tabulate\n"
        "\n"
        "import sqlite_utils\n"
        "from sqlite_utils.db import Database\n"
        "\n"
        "\n"
        "@click.group()\n"
        "def cli():\n"
        '    "Commands for interacting with a SQLite database"\n'
        "\n"
        "\n"
        "@cli.command()\n"
        "def tables(path):\n"
        "    db = Database(path)\n"
        "    click.echo(json.dumps(db.table_names()))\n"
        "\n"
        "\n"
        "@cli.command()\n"
        "def insert(path, table, rows):\n"
        "    Database(path)[table].insert_all(rows)\n"
        "\n"
        "\n"
        "@cli.command(name='rows')\n"
        "def rows(path, table):\n"
        "    # print(tabulate.tabulate(rows)) is the old way\n"
        "    print(tabulate.tabulate(Database(path)[table].rows))\n"
        "\n"
        "\n"
        "@click.command()\n"
        "def helper():\n"
        "    pass\n"
    ),
    "sqlite_utils/db.py": (
        "import sqlite3\n"
        "\n"
        "\n"
        "class Database:\n"
        "    def __init__(self, filename_or_conn=None, memory=False):\n"
        "        if memory:\n"
        '            self.conn = sqlite3.connect(":memory:")\n'
        "        else:\n"
        "            self.conn = sqlite3.connect(str(filename_or_conn))\n"
        "\n"
        "    def table_names(self):\n"
        '        return [r[0] for r in self.conn.execute("select name from sqlite_master")]\n'
        "\n"
        "    def __getitem__(self, name):\n"
        "        return Table(self, name)\n"
        "\n"
        "\n"
        "class Queryable:\n"
        "    pass\n"
        "\n"
        "\n"
        "class Table(Queryable):\n"
        "    def __init__(self, db, name):\n"
        "        self.db = db\n"
        "        self.name = name\n"
        "\n"
        "    def insert_all(self, rows):\n"
        "        for row in rows:\n"
        '            self.db.conn.execute(f"INSERT INTO [{self.name}] VALUES (?)", (row,))\n'
        "\n"
        "    @property\n"
        "    def rows(self):\n"
        '        return self.db.conn.execute(f"select * from [{self.name}]").fetchall()\n'
    ),
    "sqlite_utils/utils.py": "def suggest_column_types(records):\n    return {}\n",
    "sqlite_utils/plugins.py": 'import pluggy\n\npm = pluggy.PluginManager("sqlite_utils")\n',
    "tests/conftest.py": "import pytest\n",
    "tests/test_cli.py": "def test_tables():\n    assert True\n",
}

"""Hard signals: lines that say what the code does, read without any LLM (ADR-0007, Level 0 map).

A signal is a Fact about the text: this line starts a web server, sends mail, writes rows, opens an
SQLite file, declares a command. The project map groups them into boxes, arrows and outputs; what
they mean together is decided there, never here. Comment lines are skipped. Signals that can repeat
on every other line (prints, HTTP calls) keep only their first few lines per file.
"""

import json
import posixpath
import re
import tomllib
from collections.abc import Iterable

from umbra_engine.analyzers.manifests import line_of, toml_key_line, toml_section
from umbra_engine.claims import SIGNALS, Claim
from umbra_engine.guard import GuardedFile

PYTHON = (".py",)
JAVASCRIPT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte")
REPEATED_KEPT = 5
COUNTED = {"route", "command"}  # every line kept: the map counts them
COMMENT = ("#", "//", "*", "/*")

_DRIVER_PY = r"sqlmodel|sqlalchemy|psycopg2?|asyncpg|pymysql|MySQLdb|pymongo|motor|peewee|tortoise|django\.db"
_DRIVER_JS = r"pg|mysql2|mongoose|@prisma/client|typeorm|sequelize|knex|drizzle-orm|better-sqlite3"

PY_SIGNALS: dict[str, re.Pattern[str]] = {
    "web-server:fastapi": re.compile(r"\bFastAPI\s*\("),
    "web-server:flask": re.compile(r"\bFlask\s*\(\s*__name__"),
    "web-server:django": re.compile(r"\bget_wsgi_application\(|\bget_asgi_application\("),
    "route": re.compile(r"^\s*@\w+\.(?:get|post|put|patch|delete|route)\("),
    "cli": re.compile(r"^\s*@click\.(?:group|command)\b|\bargparse\.ArgumentParser\(|\btyper\.Typer\("),
    "command": re.compile(r"^\s*@(?P<name>\w+)\.command\("),  # `command:cli`: one command of the group `cli`
    "print": re.compile(r"\bclick\.echo\(|^\s*print\(|\bsys\.stdout\.write\("),
    "db-driver": re.compile(rf"^\s*(?:from|import)\s+(?P<name>{_DRIVER_PY})\b"),
    "db-write": re.compile(
        r"\bsession\.(?:add|commit|delete|merge)\(|\bINSERT\s+(?:OR\s+\w+\s+)?INTO\b|\.insert_(?:one|many)\("
    ),
    "sqlite": re.compile(r"\bsqlite3\.connect\((?!\s*[\"']:memory:)"),  # a file, not a database in memory
    "smtp": re.compile(r"^\s*(?:import|from)\s+(?:smtplib|emails)\b|\bsmtplib\.SMTP|\bsend_mail\("),
    "sentry": re.compile(r"^\s*import\s+sentry_sdk\b|\bsentry_sdk\.init\("),
    "plugins": re.compile(r"^\s*import\s+pluggy\b|^\s*from\s+pluggy\s+import\b"),
    "format:json": re.compile(r"^\s*import\s+json\b"),
    "format:csv": re.compile(r"^\s*import\s+csv\b"),
    "format:table": re.compile(r"^\s*import\s+tabulate\b|^\s*from\s+tabulate\s+import\b"),
}
JS_SIGNALS: dict[str, re.Pattern[str]] = {
    "web-server:express": re.compile(r"\bexpress\(\s*\)"),
    "route": re.compile(r"\b(?:app|router)\.(?:get|post|put|patch|delete)\(\s*['\"`]/"),
    "ui-render": re.compile(r"\bcreateRoot\(|\bReactDOM\.render\(|\bcreateApp\(|\bhydrateRoot\("),
    "http-client": re.compile(
        r"\bOpenAPI\.BASE\s*=|\baxios\.create\(|\bbaseURL\s*:|\bfetch\(\s*[`'\"]|import\.meta\.env\.\w*API_URL"
    ),
    "cli": re.compile(r"""(?:from\s+|require\()\s*['"](?:commander|yargs|cac)['"]"""),
    "db-driver": re.compile(rf"""(?:from\s+|require\()\s*['"](?P<name>{_DRIVER_JS})['"]"""),
    "smtp": re.compile(r"""(?:from\s+|require\()\s*['"]nodemailer['"]"""),
    "sentry": re.compile(r"""(?:from\s+|require\()\s*['"]@sentry/"""),
}
_EXPORTS = re.compile(r"^__all__\s*=|^from\s+\.\w*\s+import\s+[A-Z_]")


class SignalsAnalyzer:
    producer = "signals@1.0"

    def accepts(self, file: GuardedFile) -> bool:
        name = posixpath.basename(file.rel_path).lower()
        return name in ("pyproject.toml", "package.json") or file.rel_path.lower().endswith(
            PYTHON + JAVASCRIPT
        )

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        name = posixpath.basename(file.rel_path).lower()
        if name == "pyproject.toml":
            found = _pyproject_scripts(file.text)
        elif name == "package.json":
            found = _package_entries(file.text)
        else:
            patterns = PY_SIGNALS if file.rel_path.lower().endswith(PYTHON) else JS_SIGNALS
            found = _scan(file.text, patterns)
            if name == "__init__.py":
                found += _scan(file.text, {"exports": _EXPORTS})[:1]
        return [
            Claim(file.rel_path, "module", SIGNALS, f"signal:{s}", "signal", "fact", n, n) for s, n in found
        ]

    def limits(self, file: GuardedFile) -> list[str]:
        return []


def _scan(text: str, patterns: dict[str, re.Pattern[str]]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    kept: dict[str, int] = {}
    for number, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith(COMMENT):
            continue
        for signal, pattern in patterns.items():
            match = pattern.search(line)
            if match and (signal in COUNTED or kept.get(signal, 0) < REPEATED_KEPT):
                kept[signal] = kept.get(signal, 0) + 1
                named = match.groupdict().get("name")  # which driver: `db-driver:sqlmodel`
                found.append((f"{signal}:{named}" if named else signal, number))
    return found


def _pyproject_scripts(text: str) -> list[tuple[str, int]]:
    """`[project.scripts]` and Poetry's `[tool.poetry.scripts]`: `script:<command>=<module:function>`."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    found: list[tuple[str, int]] = []
    tables = {
        "project.scripts": data.get("project", {}).get("scripts", {}),
        "tool.poetry.scripts": data.get("tool", {}).get("poetry", {}).get("scripts", {}),
    }
    for header, scripts in tables.items():
        span = toml_section(text, header)
        for command, target in scripts.items():
            line = toml_key_line(text, span, command) if span else None
            if line is not None and isinstance(target, str):
                found.append((f"script:{command}={target}", line))
    return found


def _package_entries(text: str) -> list[tuple[str, int]]:
    """`bin` (a command) and `main`/`exports` (an importable library) of a package.json."""
    try:
        data = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    found: list[tuple[str, int]] = []
    bins = data.get("bin")
    if isinstance(bins, str):
        bins = {str(data.get("name", "")): bins}
    if isinstance(bins, dict):
        for command, target in bins.items():
            at = re.search(r'"bin"\s*:', text)
            if at and isinstance(target, str):
                found.append((f"script:{command}={target}", line_of(text, at.start())))
    for key in ("main", "exports"):
        at = re.search(rf'"{key}"\s*:', text)
        if key in data and at:
            found.append(("library", line_of(text, at.start())))
            break
    return found

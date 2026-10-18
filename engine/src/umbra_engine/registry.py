"""Project registry: which folders Umbra knows, each with a stable id and an isolated store."""

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from umbra_engine import sqlite_db
from umbra_engine.project_store import ProjectStore
from umbra_engine.settings import Settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    root TEXT NOT NULL,
    root_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class ProjectPathError(ValueError):
    """The given path cannot be registered as a Project."""


class ProjectIdCollisionError(RuntimeError):
    """Two different folders produced the same Project id (should never happen with a 48-bit digest)."""


@dataclass(frozen=True)
class Project:
    id: str
    root: Path
    name: str
    created_at: str


WINDOWS_EXTENDED_PREFIX = "\\\\?\\"
WINDOWS_EXTENDED_UNC_PREFIX = "\\\\?\\UNC\\"


def resolve_root(path: str | Path) -> Path:
    """Absolute long path (never a Windows 8.3 short name), which must be an existing directory."""
    raw = str(path).strip()
    if not raw:
        raise ProjectPathError("path is empty")
    if raw.upper().startswith(WINDOWS_EXTENDED_UNC_PREFIX):
        raw = "\\\\" + raw[len(WINDOWS_EXTENDED_UNC_PREFIX) :]
    elif raw.startswith(WINDOWS_EXTENDED_PREFIX):
        raw = raw[len(WINDOWS_EXTENDED_PREFIX) :]
    resolved = Path(os.path.realpath(Path(raw).expanduser()))
    if not resolved.exists():
        raise ProjectPathError(f"path does not exist: {path}")
    if not resolved.is_dir():
        raise ProjectPathError(f"path is not a directory: {path}")
    return resolved


def root_key(root: Path) -> str:
    return os.path.normcase(str(root))


def project_id_for(root: Path) -> str:
    ascii_name = unicodedata.normalize("NFKD", root.name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "project"
    digest = hashlib.sha256(root_key(root).encode()).hexdigest()[:12]
    return f"{slug}-{digest}"


class Registry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        settings.home.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_db.connect(settings.registry_path, SCHEMA)

    def __enter__(self) -> "Registry":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def add(self, path: str | Path) -> tuple[Project, bool]:
        """Register a folder. Returns the Project and whether it was newly created (idempotent)."""
        root = resolve_root(path)
        candidate = Project(
            project_id_for(root), root, root.name, datetime.now(UTC).isoformat(timespec="seconds")
        )
        cursor = self._db.execute(
            "INSERT OR IGNORE INTO projects(id, root, root_key, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (candidate.id, str(candidate.root), root_key(root), candidate.name, candidate.created_at),
        )
        project = self._find_by_key(root_key(root))
        if project is None:
            raise ProjectIdCollisionError(f"project id {candidate.id} is already used by another folder")
        ProjectStore.create(self._settings.projects_dir / project.id).close()
        return project, cursor.rowcount == 1

    def get(self, project_id: str) -> Project | None:
        row = self._db.execute(
            "SELECT id, root, name, created_at FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return _to_project(row) if row else None

    def list(self) -> list[Project]:
        rows = self._db.execute("SELECT id, root, name, created_at FROM projects ORDER BY created_at, id")
        return [_to_project(row) for row in rows]

    def close(self) -> None:
        self._db.close()

    def _find_by_key(self, key: str) -> Project | None:
        row = self._db.execute(
            "SELECT id, root, name, created_at FROM projects WHERE root_key = ?", (key,)
        ).fetchone()
        return _to_project(row) if row else None


def _to_project(row: tuple[str, str, str, str]) -> Project:
    return Project(id=row[0], root=Path(row[1]), name=row[2], created_at=row[3])

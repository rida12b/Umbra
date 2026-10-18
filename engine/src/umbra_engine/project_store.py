"""One isolated SQLite store per Project."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from umbra_engine import sqlite_db

STORE_FILE = "store.sqlite"
SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN ('readable', 'skipped')),
    reason TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT ''
);
"""


@dataclass(frozen=True)
class FileEntry:
    path: str
    state: str
    reason: str = ""
    detail: str = ""


class ProjectStore:
    def __init__(self, path: Path, *, create: bool = False) -> None:
        self.path = path
        self._db = sqlite_db.connect(path, SCHEMA)
        if create:
            self._db.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
            )

    def __enter__(self) -> "ProjectStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @classmethod
    def create(cls, directory: Path) -> "ProjectStore":
        directory.mkdir(parents=True, exist_ok=True)
        return cls(directory / STORE_FILE, create=True)

    @classmethod
    def open_existing(cls, directory: Path) -> "ProjectStore":
        path = directory / STORE_FILE
        if not path.exists():
            raise FileNotFoundError(f"no store at {path}")
        return cls(path)

    def schema_version(self) -> int:
        row = self._db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row[0])

    def replace_files(self, entries: list[FileEntry], meta: dict[str, str]) -> None:
        """Atomically replace the file inventory of the last index run."""
        with self._transaction():
            self._db.execute("DELETE FROM files")
            self._db.executemany(
                "INSERT INTO files(path, state, reason, detail) VALUES (?, ?, ?, ?)",
                [(e.path, e.state, e.reason, e.detail) for e in entries],
            )
            self._db.executemany("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", list(meta.items()))

    def files(self) -> list[FileEntry]:
        rows = self._db.execute("SELECT path, state, reason, detail FROM files ORDER BY path")
        return [FileEntry(*row) for row in rows]

    def meta(self) -> dict[str, str]:
        return dict(self._db.execute("SELECT key, value FROM meta").fetchall())

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")

    def close(self) -> None:
        self._db.close()

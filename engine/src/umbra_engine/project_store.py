"""One isolated SQLite store per Project. Claims are added by later scenarios."""

from pathlib import Path

from umbra_engine import sqlite_db

STORE_FILE = "store.sqlite"
SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class ProjectStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._db = sqlite_db.connect(path, SCHEMA)

    def __enter__(self) -> "ProjectStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @classmethod
    def create(cls, directory: Path) -> "ProjectStore":
        directory.mkdir(parents=True, exist_ok=True)
        store = cls(directory / STORE_FILE)
        store._db.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
        )
        return store

    @classmethod
    def open(cls, directory: Path) -> "ProjectStore":
        path = directory / STORE_FILE
        if not path.exists():
            raise FileNotFoundError(f"no store at {path}")
        return cls(path)

    def schema_version(self) -> int:
        row = self._db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row[0])

    def close(self) -> None:
        self._db.close()

"""One isolated SQLite store per Project."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from umbra_engine import sqlite_db
from umbra_engine.claims import StoredClaim
from umbra_engine.store_schema import (
    CLAIM_FIELDS,
    CLAIM_FILTERS,
    FILE_FIELDS,
    INDEXED_SCHEMA,
    LIST_SEPARATOR,
    REBUILT_TABLES,
    SCHEMA,
    SCHEMA_VERSION,
    STALE_INDEX,
    placeholders,
)

STORE_FILE = "store.sqlite"
__all__ = ["INDEXED_SCHEMA", "LIST_SEPARATOR", "SCHEMA_VERSION", "STALE_INDEX", "FileEntry", "ProjectStore"]


@dataclass(frozen=True)
class FileEntry:
    path: str
    state: str
    reason: str = ""
    detail: str = ""
    analyzers: str = ""
    notes: str = ""
    version: str = ""
    digest: str = ""


class ProjectStore:
    def __init__(self, path: Path, *, create: bool = False) -> None:
        self.path = path
        self._db = sqlite_db.connect(path, SCHEMA)
        self._migrate()
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

    def replace_index(
        self, entries: list[FileEntry], claims: list[StoredClaim], meta: dict[str, str]
    ) -> None:
        """Atomically replace the inventory and every Claim with the result of one index run."""
        with self._transaction():
            self._db.execute("DELETE FROM files")
            self._db.execute("DELETE FROM claims")
            self._db.executemany(
                f"INSERT INTO files({', '.join(FILE_FIELDS)}) VALUES ({placeholders(FILE_FIELDS)})",
                [
                    (e.path, e.state, e.reason, e.detail, e.analyzers, e.notes, e.version, e.digest)
                    for e in entries
                ],
            )
            self._db.executemany(
                f"INSERT INTO claims({', '.join(CLAIM_FIELDS)}) VALUES ({placeholders(CLAIM_FIELDS)})",
                [
                    (
                        c.key,
                        c.file,
                        c.subject,
                        c.subject_kind,
                        c.relation,
                        c.object,
                        c.object_kind,
                        c.status,
                        c.line_start,
                        c.line_end,
                        c.producer,
                        c.evidence_version,
                    )
                    for c in claims
                ],  # fmt: skip
            )
            self._db.executemany("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", list(meta.items()))

    def file(self, path: str) -> FileEntry | None:
        row = self._db.execute(
            f"SELECT {', '.join(FILE_FIELDS)} FROM files WHERE path = ?", (path,)
        ).fetchone()
        return FileEntry(*row) if row else None

    def files(self) -> list[FileEntry]:
        rows = self._db.execute(f"SELECT {', '.join(FILE_FIELDS)} FROM files ORDER BY path")
        return [FileEntry(*row) for row in rows]

    def claims(self, limit: int = 1000, offset: int = 0, **filters: str | None) -> list[StoredClaim]:
        """Claims matching every given filter (`file`, `subject`, `object`, `relation`, `status`), by key."""
        where, values = self._where(filters)
        rows = self._db.execute(
            f"SELECT {', '.join(CLAIM_FIELDS)} FROM claims WHERE {where} ORDER BY key LIMIT ? OFFSET ?",
            (*values, limit, offset),
        )
        return [StoredClaim(*row) for row in rows]

    def claim_keys(self, **filters: str | None) -> list[str]:
        where, values = self._where(filters)
        return [
            row[0] for row in self._db.execute(f"SELECT key FROM claims WHERE {where} ORDER BY key", values)
        ]

    def claims_by_key(self, keys: list[str]) -> list[StoredClaim]:
        query = f"SELECT {', '.join(CLAIM_FIELDS)} FROM claims WHERE key = ?"
        rows = [self._db.execute(query, (key,)).fetchone() for key in keys]
        return [StoredClaim(*row) for row in rows if row]

    def count_claims_matching(self, **filters: str | None) -> int:
        where, values = self._where(filters)
        return self._db.execute(f"SELECT COUNT(*) FROM claims WHERE {where}", values).fetchone()[0]

    def count_claims(self) -> dict[str, int]:
        return dict(self._db.execute("SELECT status, COUNT(*) FROM claims GROUP BY status").fetchall())

    def index_is_current(self) -> bool:
        """False when the Project was never indexed, or indexed by an older Umbra: its rows would be
        read with the wrong meaning, so callers must ask for a new index instead."""
        row = self._db.execute("SELECT value FROM meta WHERE key = ?", (INDEXED_SCHEMA,)).fetchone()
        return row is not None and row[0] == str(SCHEMA_VERSION)

    def meta(self) -> dict[str, str]:
        return dict(self._db.execute("SELECT key, value FROM meta").fetchall())

    @staticmethod
    def _where(filters: dict[str, str | None]) -> tuple[str, tuple[str, ...]]:
        active = {key: value for key, value in filters.items() if value is not None}
        unknown = set(active) - set(CLAIM_FILTERS)
        if unknown:
            raise ValueError(f"unknown claim filters: {sorted(unknown)}")
        return " AND ".join(f"{key} = ?" for key in active) or "1 = 1", tuple(active.values())

    def _migrate(self) -> None:
        """A table whose columns differ from this version is rebuilt empty; its index is then stale."""
        for table, fields in REBUILT_TABLES.items():
            columns = [row[1] for row in self._db.execute(f"PRAGMA table_info({table})")]
            if columns and set(columns) != set(fields):
                self._db.execute(f"DROP TABLE {table}")
                self._db.execute("DELETE FROM meta WHERE key = ?", (INDEXED_SCHEMA,))
        self._db.executescript(SCHEMA)
        if self._db.execute("SELECT 1 FROM meta WHERE key = 'schema_version'").fetchone():
            self._db.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(SCHEMA_VERSION),))

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

"""One isolated SQLite store per Project."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from umbra_engine import sqlite_db
from umbra_engine.claims import Claim, StoredClaim

STORE_FILE = "store.sqlite"
LIST_SEPARATOR = "\n"  # several analyzers, failures or notes in one column
INDEXED_SCHEMA = "indexed_schema"  # schema of the store when the last index run wrote it
STALE_INDEX = "this Project is not indexed, or was indexed by an older Umbra: index it again"
SCHEMA_VERSION = 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN ('readable', 'skipped')),
    reason TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    analyzers TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY,
    file TEXT NOT NULL,
    subject TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    relation TEXT NOT NULL,
    object TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('fact', 'hypothesis', 'observation')),
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    producer TEXT NOT NULL,
    git_commit TEXT
);
CREATE INDEX IF NOT EXISTS claims_by_file ON claims(file);
CREATE INDEX IF NOT EXISTS claims_by_subject ON claims(subject);
CREATE INDEX IF NOT EXISTS claims_by_object ON claims(object);
"""
FILE_FIELDS = ("path", "state", "reason", "detail", "analyzers", "notes")
CLAIM_FIELDS = (
    "file", "subject", "subject_kind", "relation", "object", "object_kind", "status",
    "line_start", "line_end", "producer", "git_commit",
)  # fmt: skip
CLAIM_COLUMNS = ", ".join(("id", *CLAIM_FIELDS))
INSERT_CLAIM = f"INSERT INTO claims({', '.join(CLAIM_FIELDS)}) VALUES ({', '.join('?' * len(CLAIM_FIELDS))})"
CLAIM_FILTERS = ("file", "subject", "object", "relation", "status")


@dataclass(frozen=True)
class FileEntry:
    path: str
    state: str
    reason: str = ""
    detail: str = ""
    analyzers: str = ""
    notes: str = ""


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
        self,
        entries: list[FileEntry],
        claims: list[tuple[str, Claim, str]],
        git_commit: str | None,
        meta: dict[str, str],
    ) -> None:
        """Atomically replace the inventory and every Claim with the result of one index run.

        `claims` holds `(file, claim, producer)`; the file is the Claim's Evidence location.
        """
        with self._transaction():
            self._db.execute("DELETE FROM files")
            self._db.execute("DELETE FROM claims")
            self._db.executemany(
                f"INSERT INTO files({', '.join(FILE_FIELDS)}) VALUES ({', '.join('?' * len(FILE_FIELDS))})",
                [(e.path, e.state, e.reason, e.detail, e.analyzers, e.notes) for e in entries],
            )
            self._db.executemany(
                INSERT_CLAIM,
                [
                    (file, c.subject, c.subject_kind, c.relation, c.object, c.object_kind, c.status,
                     c.line_start, c.line_end, producer, git_commit)
                    for file, c, producer in claims
                ],
            )  # fmt: skip
            self._db.executemany("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", list(meta.items()))

    def files(self) -> list[FileEntry]:
        rows = self._db.execute(f"SELECT {', '.join(FILE_FIELDS)} FROM files ORDER BY path")
        return [FileEntry(*row) for row in rows]

    def claims(self, limit: int = 1000, offset: int = 0, **filters: str | None) -> list[StoredClaim]:
        """Claims matching every given filter (`file`, `subject`, `relation`, `status`), in id order."""
        active = self._filters(filters)
        where = " AND ".join(f"{key} = ?" for key in active) or "1 = 1"
        rows = self._db.execute(
            f"SELECT {CLAIM_COLUMNS} FROM claims WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
            (*active.values(), limit, offset),
        )
        return [StoredClaim(*row) for row in rows]

    def claim_ids(self, **filters: str | None) -> list[int]:
        active = self._filters(filters)
        where = " AND ".join(f"{key} = ?" for key in active) or "1 = 1"
        return [
            row[0] for row in self._db.execute(f"SELECT id FROM claims WHERE {where}", tuple(active.values()))
        ]

    def claims_by_id(self, ids: list[int]) -> list[StoredClaim]:
        rows = [
            self._db.execute(f"SELECT {CLAIM_COLUMNS} FROM claims WHERE id = ?", (i,)).fetchone() for i in ids
        ]
        return [StoredClaim(*row) for row in rows if row]

    def count_claims_matching(self, **filters: str | None) -> int:
        active = self._filters(filters)
        where = " AND ".join(f"{key} = ?" for key in active) or "1 = 1"
        return self._db.execute(
            f"SELECT COUNT(*) FROM claims WHERE {where}", tuple(active.values())
        ).fetchone()[0]

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
    def _filters(filters: dict[str, str | None]) -> dict[str, str]:
        active = {key: value for key, value in filters.items() if value is not None}
        unknown = set(active) - set(CLAIM_FILTERS)
        if unknown:
            raise ValueError(f"unknown claim filters: {sorted(unknown)}")
        return active

    def _migrate(self) -> None:
        """Older stores lack later `files` columns; add them and record the version."""
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(files)")}
        for column in ("analyzers", "notes"):
            if column not in columns:
                self._db.execute(f"ALTER TABLE files ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
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

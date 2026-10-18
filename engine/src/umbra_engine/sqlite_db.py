"""SQLite connections shared by the registry and the Project stores."""

import sqlite3
import time
from pathlib import Path

BUSY_TIMEOUT_S = 10
OPEN_RETRY_S = 10


def connect(path: Path, schema: str) -> sqlite3.Connection:
    """Open in WAL mode and apply the schema, retrying while another process holds the first-start lock.

    Switching to WAL can fail with "database is locked" without going through the busy handler,
    so the busy timeout alone is not enough when several processes open a new database at once.
    """
    deadline = time.monotonic() + OPEN_RETRY_S
    while True:
        db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=BUSY_TIMEOUT_S)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(schema)
            return db
        except sqlite3.OperationalError as error:
            db.close()
            if "locked" not in str(error) or time.monotonic() > deadline:
                raise
            time.sleep(0.05)

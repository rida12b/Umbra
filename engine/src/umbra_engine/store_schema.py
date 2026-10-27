"""Schema of a Project store. Bump SCHEMA_VERSION whenever the meaning of a column changes: an index
written by another version is then refused until the Project is indexed again."""

SCHEMA_VERSION = 5
INDEXED_SCHEMA = "indexed_schema"  # schema of the store when the last index run wrote it
INDEX_ID = "index_id"  # unique per index run
STALE_INDEX = "this Project is not indexed, or was indexed by an older Umbra: index it again"
LIST_SEPARATOR = "\n"  # several analyzers, failures or notes in one column

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
    notes TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    digest TEXT NOT NULL DEFAULT '',
    fingerprint TEXT NOT NULL DEFAULT '',
    redactions INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS claims (
    key TEXT PRIMARY KEY,
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
    evidence_version TEXT NOT NULL
);
-- What Claude Code did in the Project, as its hooks reported it: kept across re-indexing.
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    session TEXT NOT NULL,
    cwd TEXT NOT NULL,
    files TEXT NOT NULL,
    text TEXT NOT NULL,
    tool TEXT NOT NULL,
    prompt_id TEXT NOT NULL DEFAULT ''
);
-- Where each box of a map level sits (column, row): placed once, kept across index runs and days (ADR-0007).
CREATE TABLE IF NOT EXISTS layout (
    level TEXT NOT NULL,
    element TEXT NOT NULL,
    col INTEGER NOT NULL,
    row INTEGER NOT NULL,
    PRIMARY KEY (level, element)
);
CREATE INDEX IF NOT EXISTS events_by_time ON events(at);
CREATE INDEX IF NOT EXISTS claims_by_file ON claims(file);
CREATE INDEX IF NOT EXISTS claims_by_subject ON claims(subject);
CREATE INDEX IF NOT EXISTS claims_by_object ON claims(object);
CREATE INDEX IF NOT EXISTS claims_by_relation ON claims(relation);
"""

FILE_FIELDS = (
    "path", "state", "reason", "detail", "analyzers", "notes", "version", "digest",
    "fingerprint", "redactions",
)  # fmt: skip
CLAIM_FIELDS = (
    "key", "file", "subject", "subject_kind", "relation", "object", "object_kind", "status",
    "line_start", "line_end", "producer", "evidence_version",
)  # fmt: skip
CLAIM_FILTERS = ("file", "subject", "object", "relation", "status")

# Tables whose columns changed meaning across versions: rebuilt (their rows are refused anyway).
REBUILT_TABLES = {"files": FILE_FIELDS, "claims": CLAIM_FIELDS}
# Tables an older Umbra wrote and nothing reads any more: dropped on open (`cards`: Claude's studies, #114).
DROPPED_TABLES = ("cards",)


def placeholders(fields: tuple[str, ...]) -> str:
    return ", ".join("?" * len(fields))

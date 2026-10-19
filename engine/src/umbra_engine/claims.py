"""Claims: what Umbra asserts about a Project, each with one knowledge status and its Evidence (ADR-0001)."""

from dataclasses import dataclass
from typing import Literal

Status = Literal["fact", "hypothesis", "observation"]
Kind = Literal["module", "function", "class", "method", "type", "namespace", "symbol", "import"]
Relation = Literal["defines", "imports", "calls"]

DEFINES = "defines"
IMPORTS = "imports"
CALLS = "calls"


@dataclass(frozen=True)
class Claim:
    """`subject --relation--> object`, proven by lines `line_start..line_end` of the file it was read from.

    Subjects and objects are keys: a Module is its path, a definition is `path::Qualified.name`.
    """

    subject: str
    subject_kind: Kind
    relation: str
    object: str
    object_kind: Kind
    status: Status
    line_start: int
    line_end: int


@dataclass(frozen=True)
class StoredClaim:
    """A Claim as kept in the store, with its full Evidence and provenance."""

    id: int
    file: str
    subject: str
    subject_kind: str
    relation: str
    object: str
    object_kind: str
    status: str
    line_start: int
    line_end: int
    producer: str
    git_commit: str | None

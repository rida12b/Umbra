"""Claims: what Umbra asserts about a Project, each with one knowledge status and its Evidence (ADR-0001)."""

from dataclasses import dataclass
from typing import Literal

Status = Literal["fact", "hypothesis", "observation"]
Kind = Literal[
    "module", "function", "class", "method", "type", "namespace", "symbol", "import",
    "service", "image", "port", "directory", "workload", "k8s-service", "ingress", "labels", "resource",
]  # fmt: skip
Relation = Literal[
    "defines", "imports", "calls",
    "declares", "uses_image", "built_from", "depends_on", "exposes", "based_on",
    "has_labels", "selects", "routes_to", "mounts", "imports_module", "targets", "code_root",
]  # fmt: skip

DEFINES = "defines"
IMPORTS = "imports"
CALLS = "calls"
# Declarations (Facts about what configuration says, never proof that anything runs):
DECLARES = "declares"
USES_IMAGE = "uses_image"
BUILT_FROM = "built_from"
DEPENDS_ON = "depends_on"
EXPOSES = "exposes"
BASED_ON = "based_on"
HAS_LABELS = "has_labels"
SELECTS = "selects"
ROUTES_TO = "routes_to"
MOUNTS = "mounts"
# Links computed across files once every file is analyzed:
IMPORTS_MODULE = "imports_module"  # a Module's import resolved to another Module (or package directory)
TARGETS = "targets"  # a Kubernetes Service reaches a workload (its selector is a subset of the labels)
CODE_ROOT = "code_root"  # a service is built from the code under this directory


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
    """A Claim as kept in the store, with its full Evidence and provenance.

    `key` is stable across index runs: it is derived from the Claim itself, never from a row id.
    `evidence_version` says which text the lines refer to: the commit for an unmodified file,
    `worktree:<content hash>` for a modified or untracked one.
    """

    key: str
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
    evidence_version: str

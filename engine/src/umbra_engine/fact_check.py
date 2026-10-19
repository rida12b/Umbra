"""Check a random sample of Facts against the code they cite (SPEC S1: 30 Facts, 100 % correct).

The check is independent of the extractors and strict: the cited lines, read again through the
Secret Guard, must hold the definition header of the named symbol, or an import statement naming
exactly the cited target (quoted where the language quotes module names).
"""

import random
import re
from dataclasses import dataclass

from umbra_engine.analyzers.code import language_of
from umbra_engine.analyzers.imports import JS_LIKE
from umbra_engine.claims import (
    BASED_ON,
    BUILD_CONTEXT,
    BUILT_FROM,
    DECLARES,
    DEFINES,
    DEPENDS_ON,
    EXPOSES,
    HAS_LABELS,
    IMPORTS,
    MOUNTS,
    REFERENCES,
    REQUIRES,
    ROUTES_TO,
    SELECTS,
    SOURCES,
    USES_IMAGE,
    StoredClaim,
)
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.registry import Project

DECLARATION_RELATIONS = (
    DECLARES,
    USES_IMAGE,
    EXPOSES,
    BASED_ON,
    DEPENDS_ON,
    HAS_LABELS,
    SELECTS,
    ROUTES_TO,
    BUILT_FROM,
    BUILD_CONTEXT,
    MOUNTS,
    REQUIRES,
    REFERENCES,
    SOURCES,
)
CHECKED_RELATIONS = (DEFINES, IMPORTS, *DECLARATION_RELATIONS)
HEADER_LINES = 15  # decorators, attributes and multi-line signatures before the name
QUOTED_MODULE_LANGUAGES = JS_LIKE | {"go", "ruby", "c", "cpp"}
DEFINITION_WORDS = re.compile(
    r"\b(def|defp|defmodule|class|function|func|fn|interface|struct|enum|trait|type|module|namespace|"
    r"record|object|impl|async|const|let|var|export|public|private|protected|internal|static|override)\b"
)
IMPORT_WORDS = re.compile(r"\b(import|from|use|using|alias|require|require_relative|load|include)\b")


@dataclass(frozen=True)
class FactCheck:
    claim: StoredClaim
    correct: bool
    cited_line: str


def check_facts(project: Project, store: ProjectStore, sample: int = 30, seed: int = 0) -> list[FactCheck]:
    keys = [k for relation in CHECKED_RELATIONS for k in store.claim_keys(relation=relation, status="fact")]
    chosen = sorted(random.Random(seed).sample(keys, min(sample, len(keys))))
    guard = SecretGuard(project.root)
    return [_check(guard, claim) for claim in store.claims_by_key(chosen)]


def _check(guard: SecretGuard, claim: StoredClaim) -> FactCheck:
    released = guard.read(claim.file)
    if not isinstance(released, GuardedFile):
        return FactCheck(claim, False, f"<file now skipped: {released.reason}>")
    lines = [line.rstrip("\r") for line in released.text.split("\n")]
    if not 1 <= claim.line_start <= claim.line_end <= len(lines):
        return FactCheck(claim, False, "<lines out of range>")
    if claim.relation == DEFINES:
        return _check_definition(claim, lines)
    if claim.relation == IMPORTS:
        return _check_import(claim, lines)
    return _check_declaration(claim, lines)


def _build_evidence(cited: list[str], target: str) -> str:
    """A build entry names its context or its Dockerfile; with defaults it may only say `build: .`."""
    parts = target.split("/")
    for candidate in (parts[-1], parts[-2] if len(parts) > 1 else "", "context"):
        if candidate and candidate != "Dockerfile" and any(candidate in line for line in cited):
            return candidate
    return "build:"


def _check_declaration(claim: StoredClaim, lines: list[str]) -> FactCheck:
    """The cited lines must hold the declared value: the service, resource name, image, port, labels."""
    cited = lines[claim.line_start - 1 : claim.line_end]
    value = claim.object.split(":", 1)[1]
    if claim.relation == DECLARES and claim.object.startswith("tf:"):
        value = value.rsplit("/", 1)[-1].rsplit(".", 1)[-1]  # `tf:net/aws_vpc.main`: block named "main"
    elif claim.relation == DECLARES:
        value = value.rsplit("/", 1)[-1]  # `k8s:Deployment/cart` is named `cart` in the manifest
    elif claim.relation == REQUIRES:
        value = value.split("/", 1)[1]  # `package:npm/react`: the name as written
    elif claim.relation == REFERENCES:
        value = value.rsplit("/", 1)[-1]  # the address as written: `aws_s3_bucket.logs`
    elif claim.relation == BUILT_FROM:
        value = _build_evidence(cited, value)
    elif claim.relation == BUILD_CONTEXT:
        name = value.rsplit("/", 1)[-1]
        value = (
            name
            if name not in (".", "..")
            else ("context" if any("context" in c for c in cited) else "build")
        )
    elif claim.relation in (HAS_LABELS, SELECTS):
        value = value.split("=", 1)[0]
    hit = next((line for line in cited if value in line), None)
    return FactCheck(claim, hit is not None and bool(cited[0].strip()), (hit or cited[0]).strip()[:160])


def _check_definition(claim: StoredClaim, lines: list[str]) -> FactCheck:
    name = claim.object.rsplit("::", 1)[-1].split("~", 1)[0].rsplit(".", 1)[-1]
    word = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
    header = lines[claim.line_start - 1 : min(claim.line_end, claim.line_start + HEADER_LINES - 1)]
    for line in header:
        if word.search(line) and (
            DEFINITION_WORDS.search(line) or re.search(rf"{re.escape(name)}\s*[(<]", line)
        ):
            return FactCheck(claim, True, line.strip()[:160])
    return FactCheck(claim, False, header[0].strip()[:160] if header else "")


def _check_import(claim: StoredClaim, lines: list[str]) -> FactCheck:
    statement = "\n".join(lines[claim.line_start - 1 : claim.line_end])
    target = re.escape(claim.object)
    if not lines[claim.line_start - 1].strip() or not lines[claim.line_end - 1].strip():
        correct = False  # the cited range must start and end on the statement, not on blank lines
    elif language_of(claim.file) in QUOTED_MODULE_LANGUAGES:
        correct = re.search(rf"""[\"'`<]{target}[\"'`>]""", statement) is not None
    else:
        correct = (
            bool(IMPORT_WORDS.search(statement))
            and re.search(rf"(?<![\w.]){target}(?![\w])", statement) is not None
        )
    return FactCheck(claim, correct, statement.strip().replace("\n", " ")[:160])

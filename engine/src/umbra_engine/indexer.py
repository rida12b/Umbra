"""Index a Project: every file goes through the Secret Guard, then through every Analyzer that accepts it;
then Linkers add the Claims that need the whole Project."""

import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.analyzers import Analyzer, default_analyzers
from umbra_engine.claim_keys import WORKTREE, content_digest, evidence_version, keyed
from umbra_engine.claims import StoredClaim
from umbra_engine.gateways.git import changed_files, head_commit
from umbra_engine.guard import BINARY, TOO_LARGE, GuardedFile, SecretGuard
from umbra_engine.linkers import PRODUCER as LINKER
from umbra_engine.linkers import link
from umbra_engine.project_store import INDEXED_SCHEMA, LIST_SEPARATOR, SCHEMA_VERSION, FileEntry, ProjectStore
from umbra_engine.registry import Project
from umbra_engine.store_schema import INDEX_ID

RACY_WINDOW_NS = 3_000_000_000
LASTING_SKIPS = {BINARY, TOO_LARGE}  # decided by the content itself: unchanged content, same verdict
ANALYZERS = "analyzers"  # meta: which Analyzers (and versions) produced the stored Claims


@dataclass(frozen=True)
class IndexSummary:
    files: int
    readable: int
    redacted_secrets: int
    claims: dict[str, int]
    git_commit: str | None
    uncommitted_changes: bool | None
    skipped: dict[str, int] = field(default_factory=dict)


def index_project(
    project: Project, store: ProjectStore, analyzers: list[Analyzer] | None = None
) -> IndexSummary:
    """Index the Project again. A file whose fingerprint (size, modification time) did not change
    since the last run is not read again: its entry and Claims are reused, re-versioned. Everything is
    read again when the Secret Guard's rules or the Analyzers changed."""
    started = time.time_ns()
    commit = head_commit(project.root)
    changed = changed_files(project.root) if commit else None
    guard = SecretGuard(project.root)
    analyzers = default_analyzers() if analyzers is None else analyzers
    signature = LIST_SEPARATOR.join(sorted(a.producer for a in analyzers))
    previous, previous_claims = _reusable(store, guard.rules_version, signature)
    entries: list[FileEntry] = []
    claims: list[StoredClaim] = []
    versions: dict[str, str] = {}
    for rel_path in guard.paths():
        verdict = guard.check(rel_path)
        if verdict is not None:
            entries.append(FileEntry(verdict.rel_path, "skipped", verdict.reason, verdict.detail))
            continue
        fingerprint = guard.fingerprint(rel_path)
        old = previous.get(rel_path)
        if old is not None and fingerprint is not None and old.fingerprint == fingerprint and not old.detail:
            if old.state == "readable":
                version = versions[rel_path] = _version(commit, changed, rel_path, old.digest)
                claims += [_reversioned(c, version) for c in previous_claims.get(rel_path, [])]
                entries.append(_entry(old, version))
                continue
            if old.reason in LASTING_SKIPS:  # a lock or a race passes: those files are read again
                entries.append(old)
                continue
        result = guard.read(rel_path)
        if not isinstance(result, GuardedFile):
            entries.append(
                FileEntry(
                    result.rel_path,
                    "skipped",
                    result.reason,
                    result.detail,
                    fingerprint=_trusted(fingerprint, started),
                )
            )
            continue
        version = versions[result.rel_path] = evidence_version(commit, changed, result.rel_path, result.text)
        used, failures, notes = [], [], []
        for analyzer in (a for a in analyzers if a.accepts(result)):
            try:
                produced = list(analyzer.analyze(result))
            except Exception as error:  # one broken grammar or parser must not stop the whole index
                failures.append(f"{analyzer.producer} failed: {type(error).__name__}")
                continue
            claims += keyed(result.rel_path, produced, analyzer.producer, version)
            used.append(analyzer.producer)
            notes += analyzer.limits(result)
        entries.append(
            FileEntry(
                path=result.rel_path,
                state="readable",
                detail=LIST_SEPARATOR.join(failures),
                analyzers=LIST_SEPARATOR.join(used),
                notes=LIST_SEPARATOR.join(notes),
                version=version,
                digest=content_digest(result.text),
                fingerprint=_trusted(fingerprint, started),
                redactions=len(result.redacted),
            )
        )

    # Links are ranked in input order: give them the same order whether Claims were read or reused.
    claims.sort(key=lambda c: (c.file, c.line_start, c.line_end, c.key))
    by_file: dict[str, list] = {}
    for file, derived in link(claims, set(versions)):
        by_file.setdefault(file, []).append(derived)
    for file, derived_claims in sorted(by_file.items()):
        claims += keyed(file, derived_claims, LINKER, versions[file])

    meta = {
        INDEX_ID: uuid.uuid4().hex,  # names this run: readers cache what they derive from it
        "indexed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "guard_rules": guard.rules_version,
        ANALYZERS: signature,
        "git_commit": commit or "",
        "uncommitted_changes": str(bool(changed) if changed is not None else None),
        INDEXED_SCHEMA: str(SCHEMA_VERSION),
    }
    store.replace_index(entries, claims, meta)
    return IndexSummary(
        files=len(entries),
        readable=len(versions),
        redacted_secrets=sum(e.redactions for e in entries),
        claims=dict(sorted(Counter(claim.status for claim in claims).items())),
        git_commit=commit,
        uncommitted_changes=bool(changed) if changed is not None else None,
        skipped=dict(sorted(Counter(e.reason for e in entries if e.state == "skipped").items())),
    )


def _reusable(
    store: ProjectStore, rules_version: str, analyzers: str
) -> tuple[dict[str, FileEntry], dict[str, list[StoredClaim]]]:
    """What the last run knew, when it can be trusted: same schema, Guard rules and Analyzers."""
    meta = store.meta()
    if (
        not store.index_is_current()
        or meta.get("guard_rules") != rules_version
        or meta.get(ANALYZERS) != analyzers
    ):
        return {}, {}
    by_file: dict[str, list[StoredClaim]] = {}
    for claim in store.claims_not_from(LINKER):
        by_file.setdefault(claim.file, []).append(claim)
    return {e.path: e for e in store.files() if e.fingerprint}, by_file


def _trusted(fingerprint: str | None, started_ns: int) -> str:
    """A fingerprint modified around this run's start is not kept: a same-size edit within the clock's
    resolution (2 s on FAT) would keep it, and the file would never be read again ("racily clean")."""
    if fingerprint is None:
        return ""
    modified_ns = int(fingerprint.split(":")[1])
    return "" if modified_ns >= started_ns - RACY_WINDOW_NS else fingerprint


def _version(commit: str | None, changed: set[str] | None, path: str, digest: str) -> str:
    """`evidence_version` without the text: the commit when clean, else the stored content digest."""
    if commit is not None and changed is not None and path not in changed:
        return commit
    return f"{WORKTREE}:{digest}"


def _reversioned(claim: StoredClaim, version: str) -> StoredClaim:
    return StoredClaim(
        claim.key, claim.file, claim.subject, claim.subject_kind, claim.relation, claim.object,
        claim.object_kind, claim.status, claim.line_start, claim.line_end, claim.producer, version,
    )  # fmt: skip


def _entry(old: FileEntry, version: str) -> FileEntry:
    return FileEntry(
        old.path, old.state, old.reason, old.detail, old.analyzers, old.notes, version, old.digest,
        old.fingerprint, old.redactions,
    )  # fmt: skip

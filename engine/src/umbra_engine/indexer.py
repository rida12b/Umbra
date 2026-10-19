"""Index a Project: every file goes through the Secret Guard, then through every Analyzer that accepts it."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.analyzers import Analyzer, default_analyzers
from umbra_engine.claims import Claim
from umbra_engine.gateways.git import has_uncommitted_changes, head_commit
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import INDEXED_SCHEMA, LIST_SEPARATOR, SCHEMA_VERSION, FileEntry, ProjectStore
from umbra_engine.registry import Project


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
    commit = head_commit(project.root)
    dirty = has_uncommitted_changes(project.root) if commit else None
    guard = SecretGuard(project.root)
    analyzers = default_analyzers() if analyzers is None else analyzers
    entries: list[FileEntry] = []
    claims: list[tuple[str, Claim, str]] = []
    redacted = 0
    for result in guard.files():
        if not isinstance(result, GuardedFile):
            entries.append(FileEntry(result.rel_path, "skipped", result.reason, result.detail))
            continue
        redacted += len(result.redacted)
        used, failures, notes = [], [], []
        for analyzer in (a for a in analyzers if a.accepts(result)):
            try:
                produced = [(result.rel_path, claim, analyzer.producer) for claim in analyzer.analyze(result)]
            except Exception as error:  # one broken grammar or parser must not stop the whole index
                failures.append(f"{analyzer.producer} failed: {type(error).__name__}")
                continue
            claims += produced
            used.append(analyzer.producer)
            notes += analyzer.limits(result)
        entries.append(
            FileEntry(
                path=result.rel_path,
                state="readable",
                detail=LIST_SEPARATOR.join(failures),
                analyzers=LIST_SEPARATOR.join(used),
                notes=LIST_SEPARATOR.join(notes),
            )
        )

    meta = {
        "indexed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "guard_rules": guard.rules_version,
        "uncommitted_changes": str(dirty),
        INDEXED_SCHEMA: str(SCHEMA_VERSION),
    }
    # A Claim names a commit only when the files it was read from are exactly that commit.
    store.replace_index(entries, claims, commit if dirty is False else None, meta)
    return IndexSummary(
        files=len(entries),
        readable=sum(e.state == "readable" for e in entries),
        redacted_secrets=redacted,
        claims=dict(sorted(Counter(claim.status for _, claim, _ in claims).items())),
        git_commit=commit,
        uncommitted_changes=dirty,
        skipped=dict(sorted(Counter(e.reason for e in entries if e.state == "skipped").items())),
    )

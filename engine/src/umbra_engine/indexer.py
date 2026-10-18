"""Index a Project: every file goes through the Secret Guard, then through every Analyzer that accepts it."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.analyzers import Analyzer, default_analyzers
from umbra_engine.claims import Claim
from umbra_engine.gateways.git import head_commit
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import FileEntry, ProjectStore
from umbra_engine.registry import Project


@dataclass(frozen=True)
class IndexSummary:
    files: int
    readable: int
    redacted_secrets: int
    claims: dict[str, int]
    git_commit: str | None
    skipped: dict[str, int] = field(default_factory=dict)


def index_project(
    project: Project, store: ProjectStore, analyzers: list[Analyzer] | None = None
) -> IndexSummary:
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
        used = [a for a in analyzers if a.accepts(result)]
        for analyzer in used:
            claims += [(result.rel_path, claim, analyzer.producer) for claim in analyzer.analyze(result)]
        entries.append(FileEntry(result.rel_path, "readable", analyzers=",".join(a.producer for a in used)))

    commit = head_commit(project.root)
    meta = {"indexed_at": datetime.now(UTC).isoformat(timespec="seconds"), "guard_rules": guard.rules_version}
    store.replace_index(entries, claims, commit, meta)
    return IndexSummary(
        files=len(entries),
        readable=sum(e.state == "readable" for e in entries),
        redacted_secrets=redacted,
        claims=dict(sorted(Counter(claim.status for _, claim, _ in claims).items())),
        git_commit=commit,
        skipped=dict(sorted(Counter(e.reason for e in entries if e.state == "skipped").items())),
    )

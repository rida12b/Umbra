"""Index a Project: every file goes through the Secret Guard before anything about it is kept."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import FileEntry, ProjectStore
from umbra_engine.registry import Project


@dataclass(frozen=True)
class IndexSummary:
    files: int
    readable: int
    redacted_secrets: int
    skipped: dict[str, int] = field(default_factory=dict)


def index_project(project: Project, store: ProjectStore) -> IndexSummary:
    guard = SecretGuard(project.root)
    entries: list[FileEntry] = []
    redacted = 0
    for result in guard.files():
        if isinstance(result, GuardedFile):
            entries.append(FileEntry(result.rel_path, "readable"))
            redacted += len(result.redacted)
        else:
            entries.append(FileEntry(result.rel_path, "skipped", result.reason, result.detail))
    store.replace_files(
        entries,
        {"indexed_at": datetime.now(UTC).isoformat(timespec="seconds"), "guard_rules": guard.rules_version},
    )
    skipped_reasons = Counter(e.reason for e in entries if e.state == "skipped")
    return IndexSummary(
        files=len(entries),
        readable=sum(e.state == "readable" for e in entries),
        redacted_secrets=redacted,
        skipped=dict(sorted(skipped_reasons.items())),
    )

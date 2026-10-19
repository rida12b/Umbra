"""Index a Project: every file goes through the Secret Guard, then through every Analyzer that accepts it;
then Linkers add the Claims that need the whole Project."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.analyzers import Analyzer, default_analyzers
from umbra_engine.claim_keys import content_digest, evidence_version, keyed
from umbra_engine.claims import StoredClaim
from umbra_engine.gateways.git import changed_files, head_commit
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.linkers import PRODUCER as LINKER
from umbra_engine.linkers import link
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
    changed = changed_files(project.root) if commit else None
    guard = SecretGuard(project.root)
    analyzers = default_analyzers() if analyzers is None else analyzers
    entries: list[FileEntry] = []
    claims: list[StoredClaim] = []
    versions: dict[str, str] = {}
    redacted = 0
    for result in guard.files():
        if not isinstance(result, GuardedFile):
            entries.append(FileEntry(result.rel_path, "skipped", result.reason, result.detail))
            continue
        redacted += len(result.redacted)
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
            )
        )

    by_file: dict[str, list] = {}
    for file, derived in link(claims, set(versions)):
        by_file.setdefault(file, []).append(derived)
    for file, derived_claims in sorted(by_file.items()):
        claims += keyed(file, derived_claims, LINKER, versions[file])

    meta = {
        "indexed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "guard_rules": guard.rules_version,
        "git_commit": commit or "",
        "uncommitted_changes": str(bool(changed) if changed is not None else None),
        INDEXED_SCHEMA: str(SCHEMA_VERSION),
    }
    store.replace_index(entries, claims, meta)
    return IndexSummary(
        files=len(entries),
        readable=len(versions),
        redacted_secrets=redacted,
        claims=dict(sorted(Counter(claim.status for claim in claims).items())),
        git_commit=commit,
        uncommitted_changes=bool(changed) if changed is not None else None,
        skipped=dict(sorted(Counter(e.reason for e in entries if e.state == "skipped").items())),
    )

"""Stable identities for Claims and Evidence versions, independent of database row ids."""

import hashlib
from collections import Counter

from umbra_engine.claims import Claim, StoredClaim

WORKTREE = "worktree"


def evidence_version(commit: str | None, changed: set[str] | None, path: str, text: str) -> str:
    """The commit when the file is exactly as committed, else `worktree:<hash of its released text>`."""
    if commit is not None and changed is not None and path not in changed:
        return commit
    return f"{WORKTREE}:{content_digest(text)}"


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def keyed(file: str, claims: list[Claim], producer: str, version: str) -> list[StoredClaim]:
    """Each Claim keyed by who says it (producer name, without version), what it says (file, subject,
    relation, object) and its rank among identical ones in that file: the key survives re-indexing
    and edits elsewhere in the Project."""
    seen: Counter[tuple[str, str, str]] = Counter()
    stored = []
    for claim in claims:
        identity = (claim.subject, claim.relation, claim.object)
        seen[identity] += 1
        parts = (producer.split("@", 1)[0], file, *identity, str(seen[identity]))
        digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()
        stored.append(
            StoredClaim(
                key=digest[:24],
                file=file,
                subject=claim.subject,
                subject_kind=claim.subject_kind,
                relation=claim.relation,
                object=claim.object,
                object_kind=claim.object_kind,
                status=claim.status,
                line_start=claim.line_start,
                line_end=claim.line_end,
                producer=producer,
                evidence_version=version,
            )
        )
    return stored

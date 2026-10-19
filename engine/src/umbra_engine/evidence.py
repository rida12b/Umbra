"""Evidence excerpts: the cited lines of a file, read again through the Secret Guard, with their version."""

from dataclasses import dataclass

from umbra_engine.claim_keys import content_digest
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import FileEntry

CONTEXT_LINES = 3
MAX_EXCERPT_LINES = 120


@dataclass(frozen=True)
class EvidenceExcerpt:
    file: str
    version: str
    start: int
    end: int
    first_line: int  # line number of `lines[0]` (context included)
    lines: list[str]
    current: bool  # False when the file changed since it was indexed: line numbers may have moved


class EvidenceUnavailableError(LookupError):
    """The file is not readable through the Secret Guard (excluded, binary, gone...)."""


def excerpt(guard: SecretGuard, entry: FileEntry, start: int, end: int) -> EvidenceExcerpt:
    """`entry` is the file as indexed: its version names the text, its digest tells if it changed since."""
    released = guard.read(entry.path)
    if not isinstance(released, GuardedFile):
        raise EvidenceUnavailableError(f"{entry.path}: {released.reason}")
    lines = [line.rstrip("\r") for line in released.text.split("\n")]
    first = max(1, start - CONTEXT_LINES)
    last = min(len(lines), end + CONTEXT_LINES, first + MAX_EXCERPT_LINES - 1)
    current = content_digest(released.text) == entry.digest
    return EvidenceExcerpt(entry.path, entry.version, start, end, first, lines[first - 1 : last], current)

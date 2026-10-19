"""Coverage: every file of a Project is accounted for, never silently ignored (SPEC S1).

- `covered`: at least one Analyzer read it and nothing it should give is missing;
- `partial`: analyzed, but some Claims cannot be extracted (e.g. no definitions for C++);
- `gap`: a Coverage Gap — skipped by the Secret Guard, or no Analyzer could read it.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from umbra_engine.analyzers.code import language_of
from umbra_engine.project_store import LIST_SEPARATOR, FileEntry

State = Literal["covered", "partial", "gap"]
MISDETECTED = {"vimdoc"}  # tree-sitter-language-pack labels any *.txt as Vim help


@dataclass(frozen=True)
class FileCoverage:
    path: str
    state: State
    reasons: list[str]
    analyzers: list[str]


@dataclass(frozen=True)
class CoverageReport:
    total: int
    covered: int
    partial: int
    gap: int
    gap_reasons: dict[str, int]
    files: list[FileCoverage]


def file_coverage(entry: FileEntry) -> FileCoverage:
    analyzers = [a for a in entry.analyzers.split(LIST_SEPARATOR) if a]
    if entry.state == "skipped":
        return FileCoverage(entry.path, "gap", [_join(entry.reason, entry.detail)], [])
    failures = [f for f in entry.detail.split(LIST_SEPARATOR) if f]
    if not analyzers:
        return FileCoverage(entry.path, "gap", failures or [f"no analyzer for {_kind(entry.path)}"], [])
    notes = [n for n in entry.notes.split(LIST_SEPARATOR) if n]
    return FileCoverage(
        entry.path, "partial" if failures or notes else "covered", failures + notes, analyzers
    )


def coverage_report(
    entries: list[FileEntry], only: State | None = None, limit: int | None = None, offset: int = 0
) -> CoverageReport:
    """Counts cover every file; `only`, `limit` and `offset` narrow the listed files."""
    files = [file_coverage(entry) for entry in entries]
    states = Counter(f.state for f in files)
    gap_reasons = Counter(reason for f in files if f.state == "gap" for reason in f.reasons)
    return CoverageReport(
        total=len(files),
        covered=states["covered"],
        partial=states["partial"],
        gap=states["gap"],
        gap_reasons=dict(gap_reasons.most_common()),
        files=[f for f in files if only is None or f.state == only][
            offset : None if limit is None else offset + limit
        ],
    )


def _kind(path: str) -> str:
    """The language when detection is reliable, else the file extension or name."""
    language = language_of(path)
    if language and language not in MISDETECTED:
        return language
    name = path.rsplit("/", 1)[-1]
    return f"*.{name.rsplit('.', 1)[-1]}" if "." in name else name


def _join(reason: str, detail: str) -> str:
    return f"{reason} ({detail})" if detail else reason

"""Coverage: every file of a Project is accounted for, never silently ignored (SPEC S1).

- `covered`: at least one Analyzer read it and nothing it should give is missing;
- `partial`: analyzed, but some Claims cannot be extracted (e.g. no definitions for C++);
- `gap`: a Coverage Gap — skipped by the Secret Guard, or no Analyzer could read it.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from umbra_engine.analyzers.code import language_of
from umbra_engine.project_store import FileEntry

State = Literal["covered", "partial", "gap"]


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
    analyzers = [a for a in entry.analyzers.split(",") if a]
    if entry.state == "skipped":
        return FileCoverage(entry.path, "gap", [_join(entry.reason, entry.detail)], [])
    failures = [f for f in entry.detail.split("; ") if f]
    if not analyzers:
        return FileCoverage(entry.path, "gap", failures or [f"no analyzer for {_kind(entry.path)}"], [])
    notes = [n for n in entry.notes.split("; ") if n]
    return FileCoverage(
        entry.path, "partial" if failures or notes else "covered", failures + notes, analyzers
    )


def coverage_report(entries: list[FileEntry], only: State | None = None) -> CoverageReport:
    """Counts cover every file; `only` narrows the listed files to one state."""
    files = [file_coverage(entry) for entry in entries]
    states = Counter(f.state for f in files)
    gap_reasons = Counter(reason for f in files if f.state == "gap" for reason in f.reasons)
    return CoverageReport(
        total=len(files),
        covered=states["covered"],
        partial=states["partial"],
        gap=states["gap"],
        gap_reasons=dict(gap_reasons.most_common()),
        files=[f for f in files if only is None or f.state == only],
    )


def _kind(path: str) -> str:
    language = language_of(path)
    if language:
        return language
    name = path.rsplit("/", 1)[-1]
    return f"*.{name.rsplit('.', 1)[-1]}" if "." in name else name


def _join(reason: str, detail: str) -> str:
    return f"{reason} ({detail})" if detail else reason

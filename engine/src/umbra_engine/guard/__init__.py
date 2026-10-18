"""Secret Guard: the only reader of Project files (ADR-0004).

A file is either skipped (never read: sensitive path, `.umbraignore`, outside the Project, a secret in
its own path, binary, too large, unreadable) or released as a `GuardedFile` whose secrets are replaced
by asterisks of the same length. Only this package can list Project files or build a `GuardedFile`.
"""

import codecs
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from umbra_engine.guard._listing import UNDECODABLE, list_files
from umbra_engine.guard.content import RULES_VERSION, Finding, RuleSet, default_rules, redact
from umbra_engine.guard.paths import load_umbraignore, sensitive_reason

MAX_SCAN_BYTES = 2_000_000
BINARY_SNIFF_BYTES = 8192
UTF16_BOMS = (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)

EXCLUDED_SENSITIVE = "excluded: sensitive"
EXCLUDED_UMBRAIGNORE = "excluded: .umbraignore"
EXCLUDED_OUTSIDE = "excluded: outside project"
SECRET_IN_PATH = "secret in path"
TOO_LARGE = "too large"
BINARY = "binary"
UNREADABLE = "unreadable"
UNREADABLE_NAME = "unreadable name"
CHANGED_DURING_READ = "changed during read"

_SEAL = object()


@dataclass(frozen=True)
class GuardedFile:
    """Text an Analyzer may use. Secrets are already redacted; only the Secret Guard can create one."""

    rel_path: str
    text: str
    redacted: tuple[Finding, ...]
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise TypeError("a GuardedFile can only be created by the Secret Guard")


@dataclass(frozen=True)
class Skipped:
    """A file that is not read. `rel_path` is safe to store: a secret in the path is redacted."""

    rel_path: str
    reason: str
    detail: str = ""


class SecretGuard:
    rules_version = RULES_VERSION

    def __init__(self, root: Path, rules: RuleSet | None = None) -> None:
        self._root = Path(os.path.realpath(root))
        self._rules = rules or default_rules()
        self._umbraignore = load_umbraignore(self._root)

    def files(self) -> Iterator[GuardedFile | Skipped]:
        """Every file of the Project, each one already decided: released or skipped."""
        for rel_path in list_files(self._root):
            yield self.read(rel_path)

    def check(self, rel_path: str) -> Skipped | None:
        """Path-only verdict: why this file must never be read, or None if it may be read.

        A link is judged on both its own path and its target, so `docs/notes.txt -> ../.env` is excluded.
        """
        verdict, _ = self._check(rel_path)
        return verdict

    def read(self, rel_path: str) -> GuardedFile | Skipped:
        skipped, target_before = self._check(rel_path)
        if skipped is not None:
            return skipped
        path = self._root / rel_path
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                return Skipped(rel_path, TOO_LARGE)
            data = path.read_bytes()
        except OSError as error:
            return Skipped(rel_path, UNREADABLE, type(error).__name__)
        if self._target(rel_path) != target_before:
            return Skipped(rel_path, CHANGED_DURING_READ)
        text = _decode(data)
        if text is None:
            return Skipped(rel_path, BINARY)
        findings = self._rules.scan(rel_path, text)
        released = redact(text, findings) if findings else text
        return GuardedFile(rel_path, released, tuple(findings), _seal=_SEAL)

    def _check(self, rel_path: str) -> tuple[Skipped | None, str | None]:
        path_secrets = self._rules.scan(rel_path, rel_path)
        if path_secrets:
            return Skipped(redact(rel_path, path_secrets), EXCLUDED_SENSITIVE, SECRET_IN_PATH), None
        if UNDECODABLE in rel_path:
            return Skipped(rel_path, UNREADABLE_NAME), None
        target = self._target(rel_path)
        if target is None:
            return Skipped(rel_path, EXCLUDED_OUTSIDE), None
        for candidate in dict.fromkeys((rel_path, target)):
            verdict = self._path_rules(candidate)
            if verdict is not None:
                return Skipped(rel_path, verdict.reason, verdict.detail), target
        return None, target

    def _target(self, rel_path: str) -> str | None:
        """Path of what `rel_path` really points to, relative to the root; None when outside the Project."""
        absolute = Path(os.path.realpath(self._root / rel_path))
        if not absolute.is_relative_to(self._root):
            return None
        return absolute.relative_to(self._root).as_posix()

    def _path_rules(self, rel_path: str) -> Skipped | None:
        if self._umbraignore.match_file(rel_path.lower()):
            return Skipped(rel_path, EXCLUDED_UMBRAIGNORE)
        reason = sensitive_reason(rel_path)
        if reason is not None:
            return Skipped(rel_path, EXCLUDED_SENSITIVE, reason)
        rule = self._rules.path_is_sensitive(rel_path)
        if rule is not None:
            return Skipped(rel_path, EXCLUDED_SENSITIVE, rule)
        return None


def path_has_secret(path: str) -> bool:
    """True when a path (e.g. a folder about to be registered as a Project) itself contains a secret."""
    return bool(default_rules().scan(path, path))


def _decode(data: bytes) -> str | None:
    """Text of the file, or None when it is binary. UTF-16 files (with a BOM) are text, not binary."""
    if data.startswith(UTF16_BOMS):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data[:BINARY_SNIFF_BYTES]:
        return None
    return data.decode("utf-8", errors="replace")

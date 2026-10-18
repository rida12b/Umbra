"""Secret guard: the only way the engine reads Project files.

A file is either excluded (never read: sensitive path, `.umbraignore`, outside the Project, a secret
in its own path) or returned with every detected secret replaced by asterisks of the same length.
"""

import codecs
import os
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class GuardedFile:
    """Text an analyzer may use. Secrets are already redacted; the raw content never leaves the guard."""

    rel_path: str
    text: str
    redacted: tuple[Finding, ...]


@dataclass(frozen=True)
class Skipped:
    """A file that is not read. `rel_path` is safe to store: a secret in the path is redacted."""

    rel_path: str
    reason: str
    detail: str = ""


class SecretGuard:
    rules_version = RULES_VERSION

    def __init__(self, root: Path, rules: RuleSet | None = None) -> None:
        self.root = Path(os.path.realpath(root))
        self._rules = rules or default_rules()
        self._umbraignore = load_umbraignore(self.root)

    def check(self, rel_path: str) -> Skipped | None:
        """Path-only verdict: why this file must never be read, or None if it may be read.

        A link is judged on both its own path and its target, so `docs/notes.txt -> ../.env` is excluded.
        """
        path_secrets = self._rules.scan(rel_path, rel_path)
        if path_secrets:
            return Skipped(redact(rel_path, path_secrets), EXCLUDED_SENSITIVE, SECRET_IN_PATH)
        absolute = Path(os.path.realpath(self.root / rel_path))
        if not absolute.is_relative_to(self.root):
            return Skipped(rel_path, EXCLUDED_OUTSIDE)
        target = absolute.relative_to(self.root).as_posix()
        for candidate in dict.fromkeys((rel_path, target)):
            verdict = self._path_rules(candidate)
            if verdict is not None:
                return Skipped(rel_path, verdict.reason, verdict.detail)
        return None

    def read(self, rel_path: str) -> GuardedFile | Skipped:
        skipped = self.check(rel_path)
        if skipped is not None:
            return skipped
        path = self.root / rel_path
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                return Skipped(rel_path, TOO_LARGE)
            data = path.read_bytes()
        except OSError as error:
            return Skipped(rel_path, UNREADABLE, type(error).__name__)
        text = _decode(data)
        if text is None:
            return Skipped(rel_path, BINARY)
        findings = self._rules.scan(rel_path, text)
        return GuardedFile(rel_path, redact(text, findings) if findings else text, tuple(findings))

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


def _decode(data: bytes) -> str | None:
    """Text of the file, or None when it is binary. UTF-16 files (with a BOM) are text, not binary."""
    if data.startswith(UTF16_BOMS):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data[:BINARY_SNIFF_BYTES]:
        return None
    return data.decode("utf-8", errors="replace")

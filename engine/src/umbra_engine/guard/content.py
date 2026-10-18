"""Secret detection in file content, using the gitleaks default rule set (vendored, MIT).

Rules are compiled with RE2 (`google-re2`), the engine gitleaks uses through Go: same syntax and
linear-time matching. Python's backtracking engines take minutes on some real files (e.g. a
`requirements.txt` full of hashes).

Supported rule fields: `regex`, `keywords`, `entropy`, `secretGroup`, `path`, rule allowlists
(regexes with target secret / match / line, stopwords, paths; OR or AND condition) and the
global allowlist.
"""

import math
import tomllib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Protocol, cast

import re2  # pyright: ignore[reportMissingTypeStubs]


class Match(Protocol):
    def group(self, index: int = 0, /) -> str | None: ...
    def span(self, index: int = 0, /) -> tuple[int, int]: ...


class Pattern(Protocol):
    @property
    def groups(self) -> int: ...
    def search(self, text: str, /) -> Match | None: ...
    def finditer(self, text: str, /) -> Iterator[Match]: ...


RULES_FILES = ("gitleaks.toml", "umbra.toml")
RULES_VERSION = "gitleaks-v8.30.1+umbra-2"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    line: int
    start: int
    end: int


@dataclass(frozen=True)
class _Allowlist:
    regexes: tuple[Pattern, ...]
    target: str
    stopwords: tuple[str, ...]
    paths: tuple[Pattern, ...]
    require_all: bool

    def allows(self, secret: str, match: str, line: str, path: str) -> bool:
        target = {"match": match, "line": line}.get(self.target, secret)
        checks = []
        if self.regexes:
            checks.append(any(r.search(target) for r in self.regexes))
        if self.stopwords:
            checks.append(any(word in secret.lower() for word in self.stopwords))
        if self.paths:
            checks.append(any(p.search(path) for p in self.paths))
        if not checks:
            return False
        return all(checks) if self.require_all else any(checks)


@dataclass(frozen=True)
class _Rule:
    id: str
    pattern: Pattern | None
    path: Pattern | None
    keywords: tuple[str, ...]
    entropy: float | None
    secret_group: int | None
    allowlists: tuple[_Allowlist, ...]
    groups: int


@dataclass(frozen=True)
class RuleSet:
    rules: tuple[_Rule, ...]
    global_allowlist: _Allowlist

    def path_is_sensitive(self, path: str) -> str | None:
        """Id of a path-only rule matching this path (e.g. PKCS#12 files), if any."""
        for rule in self.rules:
            if rule.pattern is None and rule.path is not None and rule.path.search(path):
                return rule.id
        return None

    def scan(self, path: str, text: str) -> list[Finding]:
        """Scan the text as is, then a same-length normalised copy (CRLF and JSON-escaped quotes),
        which the gitleaks patterns do not expect. Offsets are valid in the original text."""
        findings: dict[tuple[str, int, int], Finding] = {}
        for variant in dict.fromkeys((text, _normalised(text))):
            for finding in self._scan(path, variant):
                findings.setdefault((finding.rule_id, finding.start, finding.end), finding)
        return list(findings.values())

    def _scan(self, path: str, text: str) -> list[Finding]:
        lowered = text.lower()
        findings: list[Finding] = []
        for rule in self.rules:
            if rule.pattern is None:
                continue
            if rule.keywords and not any(keyword in lowered for keyword in rule.keywords):
                continue
            if rule.path is not None and not rule.path.search(path):
                continue
            for match in rule.pattern.finditer(text):
                finding = self._finding(rule, match, text, path)
                if finding is not None:
                    findings.append(finding)
        return findings

    def _finding(self, rule: _Rule, match: Match, text: str, path: str) -> Finding | None:
        group = rule.secret_group or next((i for i in range(1, rule.groups + 1) if match.group(i)), 0)
        secret = match.group(group) or match.group(0) or ""
        start, end = match.span(group) if match.group(group) else match.span(0)
        if rule.entropy is not None and _shannon_entropy(secret) < rule.entropy:
            return None
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line = text[line_start : line_end if line_end != -1 else len(text)]
        for allowlist in (*rule.allowlists, self.global_allowlist):
            if allowlist.allows(secret, match.group(0) or "", line, path):
                return None
        return Finding(rule.id, text.count("\n", 0, start) + 1, start, end)


def _normalised(text: str) -> str:
    return text.replace("\r", " ").replace('\\"', ' "').replace("\\'", " '")


def redact(text: str, findings: list[Finding]) -> str:
    """Replace every secret by asterisks of the same length, so lines and offsets stay valid."""
    chars = list(text)
    for finding in findings:
        for index in range(finding.start, finding.end):
            if chars[index] not in "\r\n":
                chars[index] = "*"
    return "".join(chars)


@cache
def default_rules() -> RuleSet:
    package = resources.files(__package__)
    gitleaks, umbra = (tomllib.loads(package.joinpath(f).read_text(encoding="utf-8")) for f in RULES_FILES)
    rules = tuple(_rule(entry) for entry in [*gitleaks["rules"], *umbra["rules"]])
    # gitleaks' global path allowlist skips whole files (lock files, vendor/, images) to cut CI noise.
    # Umbra drops it: any text file that is read must be scanned.
    global_allowlist = {k: v for k, v in gitleaks.get("allowlist", {}).items() if k != "paths"}
    return RuleSet(rules=rules, global_allowlist=_allowlist(global_allowlist))


def _compile(pattern: str) -> Pattern:
    return cast(Pattern, re2.compile(pattern))


def _rule(entry: dict) -> _Rule:
    pattern = _compile(entry["regex"]) if "regex" in entry else None
    return _Rule(
        id=entry["id"],
        pattern=pattern,
        path=_compile(entry["path"]) if "path" in entry else None,
        keywords=tuple(k.lower() for k in entry.get("keywords", [])),
        entropy=entry.get("entropy"),
        secret_group=entry.get("secretGroup"),
        allowlists=tuple(_allowlist(a) for a in entry.get("allowlists", [])),
        groups=pattern.groups if pattern is not None else 0,
    )


def _allowlist(entry: dict) -> _Allowlist:
    return _Allowlist(
        regexes=tuple(_compile(r) for r in entry.get("regexes", [])),
        target=entry.get("regexTarget", "secret"),
        stopwords=tuple(w.lower() for w in entry.get("stopwords", [])),
        paths=tuple(_compile(p) for p in entry.get("paths", [])),
        require_all=entry.get("condition") == "AND",
    )


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    return -sum(n / len(value) * math.log2(n / len(value)) for n in counts.values())

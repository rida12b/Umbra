"""Source code Analyzer for every language with a tree-sitter grammar.

Facts: the Module defines each Function / class / method (from the syntax tree) and imports what its
import statements name. Hypotheses: calls, because tree-sitter matches callee names without resolving
which definition they reach (ADR-0001).
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import tree_sitter as ts
import tree_sitter_language_pack as tslp

from umbra_engine.claims import CALLS, DEFINES, IMPORTS, Claim, Kind
from umbra_engine.guard import GuardedFile

# Languages handled by configuration Analyzers (or reported as Coverage Gaps), not as code.
DATA_LANGUAGES = {
    "json", "jsonc", "yaml", "toml", "ini", "dotenv", "markdown", "html", "css", "scss", "xml", "csv",
    "properties", "requirements", "gitignore", "gitattributes", "vimdoc", "po", "diff", "sql",
}  # fmt: skip
# The upstream TypeScript tags query only adds TS-specific rules on top of the JavaScript one.
INHERITED_TAGS = {"typescript": ("javascript",), "tsx": ("javascript",)}
KINDS: dict[str, Kind] = {"Function": "function", "Method": "method", "Class": "class"}

_IMPORT_TARGET = re.compile(
    r"""["'`]([^"'`]+)["'`]"""  # JS/TS/Go/Rust/... quoted module
    r"""|^\s*from\s+([\w.]+)\s+import"""  # Python from-import
    r"""|^\s*(?:import|use|using|require)\s+([\w.:/\\]+)""",  # import x / use x / using x
    re.MULTILINE,
)


@dataclass(frozen=True)
class _Definition:
    key: str
    kind: Kind
    start: int
    end: int


class CodeAnalyzer:
    producer = f"code-tree-sitter@1.0+tslp-{tslp.__version__}"

    def __init__(self) -> None:
        self._queries: dict[str, ts.Query | None] = {}

    def accepts(self, file: GuardedFile) -> bool:
        language = _language(file.rel_path)
        return language is not None and language not in DATA_LANGUAGES

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        language = _language(file.rel_path)
        if language is None:
            return []
        result = tslp.process(file.text, tslp.ProcessConfig(language, structure=True, imports=True))
        definitions = list(_flatten(file.rel_path, result.structure, prefix=""))
        claims = [
            Claim(file.rel_path, "module", DEFINES, d.key, d.kind, "fact", d.start + 1, d.end + 1)
            for d in definitions
        ]
        for imported in result.imports:
            target = _import_target(imported.source)
            if target and imported.span is not None:
                start, end = imported.span.start_line + 1, imported.span.end_line + 1
                claims.append(Claim(file.rel_path, "module", IMPORTS, target, "import", "fact", start, end))
        claims += self._calls(language, file, definitions)
        return claims

    def _calls(self, language: str, file: GuardedFile, definitions: list[_Definition]) -> list[Claim]:
        query = self._query(language)
        if query is None:
            return []
        tree = tslp.get_parser(language).parse(file.text.encode("utf-8"))
        claims = []
        for _, captures in ts.QueryCursor(query).matches(tree.root_node):
            names, calls = captures.get("name"), captures.get("reference.call")
            if not names or not calls:
                continue
            callee = (names[0].text or b"").decode(errors="replace")
            start, end = calls[0].start_point[0], calls[0].end_point[0]
            caller = _innermost(definitions, start)
            subject, kind = (caller.key, caller.kind) if caller else (file.rel_path, "module")
            claims.append(Claim(subject, kind, CALLS, callee, "symbol", "hypothesis", start + 1, end + 1))
        return claims

    def _query(self, language: str) -> ts.Query | None:
        if language not in self._queries:
            parts = [tslp.get_tags_query(lang) for lang in (*INHERITED_TAGS.get(language, ()), language)]
            source = "\n".join(part for part in parts if part)
            try:
                self._queries[language] = ts.Query(tslp.get_language(language), source) if source else None
            except Exception:
                self._queries[language] = None
        return self._queries[language]


def _language(rel_path: str) -> str | None:
    try:
        return tslp.detect_language_from_path(rel_path)
    except Exception:
        return None


def _flatten(path: str, items: Iterable[tslp.StructureItem], prefix: str) -> Iterator[_Definition]:
    for item in items:
        kind = KINDS.get(str(item.kind).rsplit(".", 1)[-1])
        name = f"{prefix}{item.name}" if item.name else None
        if kind is not None and name and item.span is not None:
            yield _Definition(f"{path}::{name}", kind, item.span.start_line, item.span.end_line)
        yield from _flatten(path, item.children, prefix=f"{name}." if name else prefix)


def _innermost(definitions: list[_Definition], line: int) -> _Definition | None:
    enclosing = [d for d in definitions if d.start <= line <= d.end]
    return min(enclosing, key=lambda d: d.end - d.start, default=None)


def _import_target(statement: str) -> str | None:
    match = _IMPORT_TARGET.search(statement)
    if match is None:
        return None
    return next(group for group in match.groups() if group)

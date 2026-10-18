"""Source code Analyzer for every language with a tree-sitter grammar.

- Definitions: Facts for verified languages, Hypotheses otherwise (see `definitions.py`).
- Imports: Facts, only where an explicit per-language rule reads the statement (see `imports.py`).
- Calls: always Hypotheses, because tree-sitter matches callee names without resolving which
  definition they reach (ADR-0001).
"""

import re
from collections.abc import Iterable

import tree_sitter as ts
import tree_sitter_language_pack as tslp

from umbra_engine.analyzers.definitions import Definition, definition_status, definitions, innermost
from umbra_engine.analyzers.imports import import_targets
from umbra_engine.claims import CALLS, DEFINES, IMPORTS, Claim
from umbra_engine.guard import GuardedFile

# Languages handled by configuration Analyzers (or reported as Coverage Gaps), not as code.
DATA_LANGUAGES = {
    "json", "jsonc", "yaml", "toml", "ini", "dotenv", "markdown", "html", "css", "scss", "xml", "csv",
    "properties", "requirements", "gitignore", "gitattributes", "vimdoc", "po", "diff", "sql",
}  # fmt: skip
# The upstream TypeScript tags query only adds TS-specific rules on top of the JavaScript one.
INHERITED_TAGS = {"typescript": ("javascript",), "tsx": ("javascript",)}
# Languages whose import statements tree-sitter-language-pack does not report: read line by line.
LINE_IMPORTS = {
    # `[ \t]*`, not `\s*`: a leading `\s*` would swallow blank lines and shift the cited line.
    "csharp": re.compile(r"^[ \t]*(?:global[ \t]+)?using[ \t]+[^;(\n]+;", re.MULTILINE),
    "c": re.compile(r"^[ \t]*#[ \t]*include[ \t]*[<\"][^>\"\n]+[>\"]", re.MULTILINE),
    "cpp": re.compile(r"^[ \t]*#[ \t]*include[ \t]*[<\"][^>\"\n]+[>\"]", re.MULTILINE),
    "ruby": re.compile(r"""^[ \t]*(?:require|require_relative|load)\b[^\n]*""", re.MULTILINE),
    "kotlin": re.compile(r"^[ \t]*import[ \t]+[\w.*]+", re.MULTILINE),
}
NOT_CALLS = {"elixir": {"def", "defp", "defmodule", "defmacro", "alias", "import", "use", "require"}}


class CodeAnalyzer:
    producer = f"code-tree-sitter@1.1+tslp-{tslp.__version__}"

    def __init__(self) -> None:
        self._queries: dict[str, ts.Query | None] = {}

    def accepts(self, file: GuardedFile) -> bool:
        language = language_of(file.rel_path)
        return language is not None and language not in DATA_LANGUAGES

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        language = language_of(file.rel_path)
        if language is None:
            return []
        result = tslp.process(file.text, tslp.ProcessConfig(language, structure=True, imports=True))
        found = definitions(file.rel_path, result.structure, language)
        status = definition_status(language)
        claims = []
        if status is not None:
            claims += [
                Claim(file.rel_path, "module", DEFINES, d.key, d.kind, status, d.start + 1, d.end + 1)
                for d in found
            ]
        claims += self._imports(language, file, result.imports)
        claims += self._calls(language, file, found if status is not None else [])
        return claims

    def _imports(self, language: str, file: GuardedFile, reported: list[tslp.ImportInfo]) -> list[Claim]:
        statements = [(i.source, i.span.start_line, i.span.end_line) for i in reported if i.span is not None]
        if language in LINE_IMPORTS:
            text = file.text
            statements = [
                (m.group(0), text.count("\n", 0, m.start()), text.count("\n", 0, m.end()))
                for m in LINE_IMPORTS[language].finditer(text)
            ]
        return [
            Claim(file.rel_path, "module", IMPORTS, target, "import", "fact", start + 1, end + 1)
            for statement, start, end in statements
            for target in import_targets(language, statement)
        ]

    def _calls(self, language: str, file: GuardedFile, found: list[Definition]) -> list[Claim]:
        query = self._query(language)
        if query is None:
            return []
        tree = tslp.get_parser(language).parse(file.text.encode("utf-8"))
        ignored = NOT_CALLS.get(language, set())
        claims = []
        for _, captures in ts.QueryCursor(query).matches(tree.root_node):
            names, calls = captures.get("name"), captures.get("reference.call")
            if not names or not calls:
                continue
            callee = (names[0].text or b"").decode(errors="replace")
            if callee in ignored:
                continue
            start, end = calls[0].start_point[0], calls[0].end_point[0]
            caller = innermost(found, start)
            subject, kind = (caller.key, caller.kind) if caller else (file.rel_path, "module")
            claims.append(Claim(subject, kind, CALLS, callee, "symbol", "hypothesis", start + 1, end + 1))
        return claims

    def _query(self, language: str) -> ts.Query | None:
        if language not in self._queries:
            parts = [tslp.get_tags_query(lang) for lang in (*INHERITED_TAGS.get(language, ()), language)]
            source = "\n".join(part for part in parts if part)
            self._queries[language] = ts.Query(tslp.get_language(language), source) if source else None
        return self._queries[language]


def language_of(rel_path: str) -> str | None:
    try:
        return tslp.detect_language_from_path(rel_path)
    except tslp.LanguageNotFoundError:
        return None

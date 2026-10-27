"""Source code Analyzer for every language with a tree-sitter grammar.

- Definitions: Facts for verified languages, Hypotheses otherwise (see `definitions.py`).
- Imports: Facts, only where an explicit per-language rule reads the statement (see `imports.py`).
- Calls: always Hypotheses, because tree-sitter matches callee names without resolving which
  definition they reach (ADR-0001).
"""

from collections.abc import Iterable, Iterator

import tree_sitter as ts
import tree_sitter_language_pack as tslp

from umbra_engine.analyzers.definitions import (
    CODE_LANGUAGES,
    Definition,
    definition_status,
    definitions,
    innermost,
)
from umbra_engine.analyzers.imports import JS_LIKE, has_import_rule, import_targets, imported_names
from umbra_engine.claims import CALLS, DEFINES, IMPORTED_NAME, IMPORTS, Claim
from umbra_engine.guard import GuardedFile

# The upstream TypeScript tags query only adds TS-specific rules on top of the JavaScript one.
INHERITED_TAGS = {"typescript": ("javascript",), "tsx": ("javascript",)}
# Languages whose import statements tree-sitter-language-pack does not report: taken from the syntax
# tree, so that an import inside a comment or a string is never mistaken for a real one.
TREE_IMPORTS = {
    "csharp": {"using_directive"},
    "c": {"preproc_include"},
    "cpp": {"preproc_include"},
    "kotlin": {"import_header"},
    # JS/TS: the pack misses `export ... from "m"` and `require("m")`.
    "javascript": {"import_statement", "export_statement"},
    "typescript": {"import_statement", "export_statement"},
    "tsx": {"import_statement", "export_statement"},
}
JS_LOADERS = {"require"}
RUBY_LOADERS = {"require", "require_relative", "load"}
NOT_CALLS = {"elixir": {"def", "defp", "defmodule", "defmacro", "alias", "import", "use", "require"}}


class CodeAnalyzer:
    producer = f"code-tree-sitter@1.3+tslp-{tslp.__version__}"

    def __init__(self) -> None:
        self._queries: dict[str, ts.Query | None] = {}

    def accepts(self, file: GuardedFile) -> bool:
        return language_of(file.rel_path) in CODE_LANGUAGES

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
        tree = tslp.get_parser(language).parse(file.text.encode("utf-8"))
        claims += self._imports(language, tree, result.imports, file.rel_path)
        claims += self._calls(language, tree, found if status is not None else [], file.rel_path)
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        language = language_of(file.rel_path)
        if language is None:
            return []
        notes = []
        status = definition_status(language)
        if status is None:
            notes.append(f"definitions not extracted for {language}")
        elif status == "hypothesis":
            notes.append(f"definitions unverified for {language} (Hypotheses)")
        if not has_import_rule(language):
            notes.append(f"imports not extracted for {language}")
        if self._query(language) is None:
            notes.append(f"calls not extracted for {language}")
        return notes

    def _imports(
        self, language: str, tree: ts.Tree, reported: list[tslp.ImportInfo], path: str
    ) -> list[Claim]:
        if language in TREE_IMPORTS or language == "ruby":
            statements = [(_text(n), *_rows(n)) for n in _import_nodes(tree.root_node, language)]
        else:
            statements = [
                (i.source, i.span.start_line, i.span.end_line) for i in reported if i.span is not None
            ]
        return [
            Claim(path, "module", IMPORTS, target, "import", "fact", start + 1, end + 1)
            for statement, start, end in statements
            for target in import_targets(language, statement)
        ] + [  # `from app import crud`: maybe the module `app.crud` (#105: links between the parts of a box)
            Claim(path, "module", IMPORTS, name, IMPORTED_NAME, "hypothesis", start + 1, end + 1)
            for statement, start, end in statements
            for name in imported_names(language, statement)
        ]

    def _calls(self, language: str, tree: ts.Tree, found: list[Definition], path: str) -> list[Claim]:
        query = self._query(language)
        if query is None:
            return []
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
            subject, kind = (caller.key, caller.kind) if caller else (path, "module")
            target = _with_receiver(names[0], callee)
            claims.append(Claim(subject, kind, CALLS, target, "symbol", "hypothesis", start + 1, end + 1))
        return claims

    def _query(self, language: str) -> ts.Query | None:
        if language not in self._queries:
            parts = [tslp.get_tags_query(lang) for lang in (*INHERITED_TAGS.get(language, ()), language)]
            source = "\n".join(part for part in parts if part)
            self._queries[language] = ts.Query(tslp.get_language(language), source) if source else None
        return self._queries[language]


MEMBER_ACCESS = {
    "attribute", "member_expression", "field_expression", "selector_expression", "navigation_expression",
    "method_invocation", "scoped_identifier", "call", "member_access_expression",
}  # fmt: skip
SELF = {"self", "cls", "this", "@"}


def _with_receiver(name: ts.Node, callee: str) -> str:
    """`save` for a bare call, `self.save` on the caller's own object, `.save` on anything else: a
    method of an unknown object (`d.get()`) must never be taken for a local function `get`."""
    parent = name.parent
    if (
        parent is None
        or parent.type not in MEMBER_ACCESS
        or parent.child_count < 2
        or parent.children[0] == name
    ):
        return callee
    receiver = (
        parent.child_by_field_name("object") or parent.child_by_field_name("receiver") or parent.children[0]
    )
    return f"self.{callee}" if _text(receiver) in SELF else f".{callee}"


def _import_nodes(node: ts.Node, language: str) -> Iterator[ts.Node]:
    if language == "ruby":
        method = node.child_by_field_name("method") if node.type == "call" else None
        if (
            method is not None
            and _text(method) in RUBY_LOADERS
            and node.child_by_field_name("receiver") is None
        ):
            yield node
            return
    elif node.type in TREE_IMPORTS[language] and not _plain_export(node):
        yield node
        return
    elif node.type == "call_expression" and language in JS_LIKE:
        function = node.child_by_field_name("function")
        if function is not None and _text(function) in JS_LOADERS:
            yield node
            return
    for child in node.children:
        yield from _import_nodes(child, language)


def _plain_export(node: ts.Node) -> bool:
    """`export function f() {...}` is not an import: look inside it (a `require()` keeps its own line)."""
    return node.type == "export_statement" and node.child_by_field_name("source") is None


def _text(node: ts.Node) -> str:
    return (node.text or b"").decode("utf-8", errors="replace")


def _rows(node: ts.Node) -> tuple[int, int]:
    """First and last row holding the node's text (a trailing newline ends on the next row, column 0)."""
    end_row, end_col = node.end_point
    return node.start_point[0], end_row - 1 if end_col == 0 and end_row > node.start_point[0] else end_row


def language_of(rel_path: str) -> str | None:
    try:
        return tslp.detect_language_from_path(rel_path)
    except tslp.LanguageNotFoundError:
        return None

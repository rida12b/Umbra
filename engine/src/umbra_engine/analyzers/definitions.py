"""Definitions (functions, classes, methods, types) from the tree-sitter structure, with stable keys.

The status of a definition depends on how far the extractor has been verified for the language
(independent strict check on real repositories): verified languages give Facts, the others give
Hypotheses, and languages where it is known to be wrong give nothing.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import tree_sitter_language_pack as tslp

from umbra_engine.claims import Kind, Status

VERIFIED = {"python", "javascript", "typescript", "tsx", "go", "java", "csharp", "elixir"}
# tree-sitter-language-pack 1.22 mislabels C/C++ definitions (macros and return types as names) and
# yields no Kotlin names: better no claim than a wrong one.
UNSUPPORTED = {"c", "cpp", "kotlin"}
# Languages whose extraction was looked at on real code: definitions are Hypotheses until verified.
EXPLORED = {"rust", "ruby", "php", "swift", "scala", "lua", "bash", "dart"}
# The Code Analyzer only claims to understand these; any other language is a Coverage Gap.
CODE_LANGUAGES = VERIFIED | UNSUPPORTED | EXPLORED

KINDS: dict[str, Kind] = {
    "Function": "function",
    "Method": "method",
    "Class": "class",
    "Struct": "type",
    "Enum": "type",
    "Interface": "type",
    "Trait": "type",
    "Module": "namespace",
    "Namespace": "namespace",
}
CONTAINERS: set[Kind] = {"class", "type"}
# A `package x;` line declares membership, not a definition: those items are transparent.
PACKAGE_LANGUAGES = {"java", "kotlin", "scala", "go"}


@dataclass(frozen=True)
class Definition:
    key: str
    kind: Kind
    start: int
    end: int


def definition_status(language: str) -> Status | None:
    if language in UNSUPPORTED:
        return None
    return "fact" if language in VERIFIED else "hypothesis"


def definitions(path: str, structure: Iterable[tslp.StructureItem], language: str) -> list[Definition]:
    """Every named definition, keyed `path::Qualified.name`; a repeated name gets `~2`, `~3`, ... in order."""
    seen: Counter[str] = Counter()
    result = []
    transparent = {"namespace"} if language in PACKAGE_LANGUAGES else set()
    for name, kind, start, end in _walk(structure, prefix="", parent=None, transparent=transparent):
        seen[name] += 1
        suffix = f"~{seen[name]}" if seen[name] > 1 else ""
        result.append(Definition(f"{path}::{name}{suffix}", kind, start, end))
    return result


def _walk(
    items: Iterable[tslp.StructureItem], prefix: str, parent: Kind | None, transparent: set[str]
) -> Iterator[tuple]:
    for item in items:
        kind = KINDS.get(str(item.kind).rsplit(".", 1)[-1])
        if kind in transparent:
            yield from _walk(item.children, prefix, parent, transparent)
            continue
        if kind == "function" and parent in CONTAINERS:
            kind = "method"
        name = f"{prefix}{item.name}" if item.name else None
        if kind is not None and name and item.span is not None:
            yield name, kind, item.span.start_line, item.span.end_line
        yield from _walk(item.children, f"{name}." if name else prefix, kind or parent, transparent)


def innermost(found: list[Definition], line: int) -> Definition | None:
    enclosing = [d for d in found if d.start <= line <= d.end]
    return min(enclosing, key=lambda d: d.end - d.start, default=None)

"""What Claude is shown to explain one map element: always text released by the Secret Guard,
plus the map's own structure. The same material gives the same digest, so a card is reused until
the code it was written from changes."""

import hashlib
import posixpath
import re
from dataclasses import dataclass

from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.projection.graph import DOCUMENTS, ProjectGraph
from umbra_engine.projection.model import APPLICATION
from umbra_engine.projection.tree import DIR, children, files_under, label
from umbra_engine.projection.view import map_view

MAX_FILE_LINES = 700
MAX_CONTEXT_CHARS = 90_000
DEFINITIONS_PER_MODULE = 12
TEST_FILE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|Tests?\.)")
README_NAMES = ("README.md", "readme.md", "README.rst", "README.txt", "README")


@dataclass(frozen=True)
class Material:
    level: str  # "application", "group" (service/component) or "code" (module/definition)
    title: str
    text: str
    child_keys: list[str]

    @property
    def digest(self) -> str:
        return hashlib.sha256(f"{self.level}\0{self.text}".encode()).hexdigest()[:24]


def material(graph: ProjectGraph, guard: SecretGuard, key: str) -> Material:
    view = map_view(graph, key, expand=True)  # raises UnknownElementError for an unknown key
    title = " / ".join(c.label for c in view.breadcrumbs)
    if key in graph.definitions:
        return Material("code", title, _definition(graph, guard, key), [])
    if view.parent.kind == "module":
        return Material(_file_level(key), title, numbered_file(guard, key, 1, MAX_FILE_LINES), [])
    level = "application" if key == APPLICATION else "group"
    return Material(level, title, _structure(graph, guard, key, view), children(graph, key))


def _file_level(path: str) -> str:
    """Code, a document or tests: each is explained in its own terms."""
    if posixpath.splitext(path)[1].lower() in DOCUMENTS:
        return "doc"
    name = posixpath.basename(path)
    if TEST_FILE.search(name) or "/tests/" in f"/{path}" or "/test/" in f"/{path}":
        return "test"
    return "code"


def _definition(graph: ProjectGraph, guard: SecretGuard, key: str) -> str:
    definition = graph.definitions[key]
    start, end = definition.lines
    header = numbered_file(guard, definition.file, 1, 25)  # imports: where names come from
    body = numbered_file(guard, definition.file, start, min(end, start + MAX_FILE_LINES))
    return f"FILE {definition.file} (top of file)\n{header}\n\nDEFINITION {key}\n{body}"


def numbered_file(guard: SecretGuard, path: str, start: int, end: int) -> str:
    released = guard.read(path)
    if not isinstance(released, GuardedFile):
        return f"({path}: not readable: {released.reason})"
    lines = released.text.split("\n")
    shown = lines[start - 1 : end]
    numbered = "\n".join(f"{start + i:5} {line.rstrip()}" for i, line in enumerate(shown))
    cut = f"\n... ({len(lines) - end} more lines not shown)" if end < len(lines) else ""
    return f"FILE {path}\n{numbered}{cut}"


def _structure(graph: ProjectGraph, guard: SecretGuard, key: str, view) -> str:
    """Children with what is known of each, the links between them, and the nearest README."""
    parts = []
    for node in view.nodes:
        files = files_under(graph, node.key)
        line = f"- [{node.key}] {node.kind} '{label(graph, key, node.key)}', {len(files)} files"
        if node.details:
            line += "; " + "; ".join(f"{k}: {', '.join(v)}" for k, v in node.details.items() if v)
        parts.append(line)
        for module in files[:6]:
            names = [d.split("::", 1)[1] for d in graph.top_definitions.get(module, [])][
                :DEFINITIONS_PER_MODULE
            ]
            parts.append(f"    {module}: {', '.join(names) if names else '(no definitions read)'}")
    links = [f"- {e.source} --{e.relation} x{e.count} ({e.status})--> {e.target}" for e in view.edges]
    text = "ELEMENTS\n" + "\n".join(parts) + "\n\nLINKS\n" + ("\n".join(links) or "(none found)")
    directory = _directory(graph, key)
    for name in README_NAMES:
        readme = f"{directory}/{name}" if directory else name
        if isinstance(guard.read(readme), GuardedFile):
            text += "\n\nREADME\n" + numbered_file(guard, readme, 1, 150)
            break
    return text[:MAX_CONTEXT_CHARS]


def _directory(graph: ProjectGraph, key: str) -> str:
    if key in graph.services:
        return graph.services[key].code_root or ""
    return key.removeprefix(DIR) if key.startswith(DIR) else ""

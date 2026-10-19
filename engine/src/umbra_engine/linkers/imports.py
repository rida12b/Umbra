"""Resolve import Claims to the Project's own Modules.

A relative import that names exactly one existing file is a Fact. An absolute import matched by its
path suffix to exactly one Module is a Hypothesis: the language's search path is not known. An
import matching nothing is external (a library) and links nowhere; one matching several Modules is
left unresolved rather than guessed.
"""

import posixpath
from collections import defaultdict

from umbra_engine.claims import IMPORTS, IMPORTS_MODULE, Claim, Kind, Status, StoredClaim

JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
JS_SOURCES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")
# TypeScript ESM imports name the emitted file: `./util.js` is `util.ts` in the sources.
TS_SOURCE_OF = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}
JVM_EXTENSIONS = (".java", ".kt", ".scala")


class ModuleIndex:
    """The Project's readable files, for exact and suffix lookups."""

    def __init__(self, files: set[str]) -> None:
        self.files = files
        self._by_suffix = _suffixes(files)
        self._directories_by_suffix = _suffixes({posixpath.dirname(f) for f in files} - {""})

    def suffix(self, candidate: str) -> list[str]:
        return self._by_suffix.get(candidate, [])

    def directory_suffix(self, candidate: str) -> list[str]:
        return self._directories_by_suffix.get(candidate, [])


def _suffixes(paths: set[str]) -> dict[str, list[str]]:
    """Every path under each of its suffixes: `a/b/c.py` under `c.py`, `b/c.py` and `a/b/c.py`."""
    by_suffix: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        parts = path.split("/")
        for start in range(len(parts)):
            by_suffix["/".join(parts[start:])].add(path)
    return {suffix: sorted(found) for suffix, found in by_suffix.items()}


def resolve_imports(claims: list[StoredClaim], modules: ModuleIndex) -> list[tuple[str, Claim]]:
    """`(file, link)` for every import that resolves to one Module (or one Go package directory)."""
    links = []
    for claim in claims:
        if claim.relation != IMPORTS:
            continue
        resolved = _resolve(claim.file, claim.object, modules)
        if resolved is None:
            continue
        target, kind, status = resolved
        if target != claim.file:
            links.append(
                (
                    claim.file,
                    Claim(
                        claim.file,
                        "module",
                        IMPORTS_MODULE,
                        target,
                        kind,
                        status,
                        claim.line_start,
                        claim.line_end,
                    ),
                )
            )
    return links


def _resolve(file: str, target: str, modules: ModuleIndex) -> tuple[str, Kind, Status] | None:
    if file.endswith(".py"):
        return _python(file, target, modules)
    if file.endswith(JS_SOURCES):
        return _javascript(file, target, modules)
    if file.endswith(".go"):
        return _go(target, modules)
    if file.endswith(JVM_EXTENSIONS):
        stem = target.removesuffix(".*").replace(".", "/")
        return _unique([m for e in JVM_EXTENSIONS for m in modules.suffix(stem + e)], "hypothesis")
    if file.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".hh")):
        return _relative(file, target, modules, ("",), ()) or _unique(modules.suffix(target), "hypothesis")
    if file.endswith(".rb") and target.startswith("."):
        return _relative(file, target, modules, (".rb", ""), ())
    return None


def _python(file: str, target: str, modules: ModuleIndex) -> tuple[str, Kind, Status] | None:
    level = len(target) - len(target.lstrip("."))
    path = target.lstrip(".").replace(".", "/")
    candidates = [f"{path}.py", f"{path}/__init__.py"] if path else ["__init__.py"]
    if level:
        package = posixpath.dirname(file).split("/") if posixpath.dirname(file) else []
        if level - 1 > len(package):
            return None  # climbs above the Project: Python refuses it, so it names no Module here
        base = "/".join(package[: len(package) - (level - 1)])
        exact = [posixpath.normpath(posixpath.join(base, c)) for c in candidates]
        return _unique([c for c in exact if c in modules.files], "fact")
    return _unique([m for c in candidates for m in modules.suffix(c)], "hypothesis")


def _javascript(file: str, target: str, modules: ModuleIndex) -> tuple[str, Kind, Status] | None:
    """Node and bundler order: the file as written, then with an extension, then a folder's index."""
    stem, extension = posixpath.splitext(target)
    if extension in TS_SOURCE_OF:
        found = _relative(file, stem, modules, TS_SOURCE_OF[extension], ())
        if found:
            return found
    return _relative(file, target, modules, ("", *JS_EXTENSIONS), ["/index" + e for e in JS_EXTENSIONS])


def _relative(
    file: str, target: str, modules: ModuleIndex, extensions, index_files
) -> tuple[str, Kind, Status] | None:
    """A `./` or `../` target, tried with the language's extensions in its own resolution order."""
    if not target.startswith((".", "/")):
        return None
    base = posixpath.normpath(posixpath.join(posixpath.dirname(file), target))
    for candidate in [base + e for e in extensions] + [base + i for i in index_files]:
        if candidate in modules.files:
            return candidate, "module", "fact"
    return None


def _go(target: str, modules: ModuleIndex) -> tuple[str, Kind, Status] | None:
    """A Go import names a package (a directory); only the Project's own module path can match it."""
    parts = target.split("/")
    for start in range(1, len(parts)):
        found = modules.directory_suffix("/".join(parts[start:]))
        if len(found) == 1:
            return f"dir:{found[0]}", "directory", "hypothesis"
        if len(found) > 1:
            return None
    return None


def _unique(matches: list[str], status: Status) -> tuple[str, Kind, Status] | None:
    unique = sorted(set(matches))
    return (unique[0], "module", status) if len(unique) == 1 else None

"""The parts of a Project that run, found from hard signals: compose services built from code, then
manifests, then top folders. Each gets one role: web app, server, command, library, or plain folder."""

import posixpath
from dataclasses import dataclass, field
from typing import Literal

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.system_facts import Facts, under

Role = Literal["web", "server", "cli", "library", "folder"]

WEB_FRAMEWORKS = {
    "react": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular", "preact": "Preact",
    "solid-js": "Solid", "next": "Next.js", "nuxt": "Nuxt",
}  # fmt: skip
SERVERS = {"fastapi": "FastAPI", "flask": "Flask", "django": "Django", "express": "Express"}
TOOLING_SERVICE = ("prestart", "migrate", "init", "seed", "setup")
TEST_SERVICE = ("playwright", "cypress", "selenium", "test", "e2e")
CODE = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".go", ".rs", ".java", ".rb")
NOT_RUNTIME = {
    "tests",
    "test",
    "docs",
    "doc",
    "scripts",
    "examples",
    "e2e",
    "hooks",
    "img",
    "assets",
    "benchmarks",
}


@dataclass
class Unit:
    id: str
    role: Role
    root: str  # its directory ("" = the Project root)
    files: set[str]
    proofs: list[StoredClaim]
    detail: str = ""
    folder: str = ""
    services: list[str] = field(default_factory=list)  # compose services built from it
    inferred: bool = False


def tooling_service(name: str) -> bool:
    return name.lower().startswith(TOOLING_SERVICE) or test_service(name)


def test_service(name: str) -> bool:
    return any(word in name.lower() for word in TEST_SERVICE)


def find_units(facts: Facts) -> list[Unit]:
    roots: dict[str, list[str]] = {}
    for service in facts.services.values():
        if service.code_root is not None:
            roots.setdefault(service.code_root, []).append(service.name)
    manifests = [d for d in facts.manifest_dirs() if not _not_runtime(d)]
    for directory in manifests:
        nested = [m for m in manifests + list(roots) if m != directory and under(directory, m)]
        if not nested and not any(under(r, directory) for r in roots):
            roots.setdefault(directory, [])
    if not roots:
        roots = {top: [] for top in _code_folders(facts.files)}
    owned = _owners(facts.files, list(roots))
    units: list[Unit] = []
    for root, services in sorted(roots.items()):
        files = {f for f, owner in owned.items() if owner == root}
        units += _classify(facts, root, files, [s for s in services if not tooling_service(s)])
    return units


def _owners(files: list[str], roots: list[str]) -> dict[str, str]:
    """Each file to the most specific root it is under (files under no root belong to none)."""
    deepest = sorted(roots, key=lambda r: -len(r))
    return {f: next(r for r in deepest if under(r, f)) for f in files if any(under(r, f) for r in deepest)}


def _not_runtime(directory: str) -> bool:
    parts = directory.split("/")
    return any(p in NOT_RUNTIME or p.startswith(".") for p in parts if p)


def _code_folders(files: list[str]) -> list[str]:
    tops = {f.split("/", 1)[0] for f in files if "/" in f and f.endswith(CODE)}
    return sorted(t for t in tops if not _not_runtime(t))


def _classify(facts: Facts, root: str, files: set[str], services: list[str]) -> list[Unit]:
    deps = facts.deps(root)
    label = root or facts.name
    web = [deps[d] for d in WEB_FRAMEWORKS if d in deps] + facts.signal("ui-render", files)
    if web:
        framework = next((WEB_FRAMEWORKS[d] for d in WEB_FRAMEWORKS if d in deps), "")
        return [Unit(f"web:{label}", "web", root, files, web, framework, _slash(root), services)]
    servers = facts.signals_starting("web-server:", files)
    if servers:
        kind = servers[0].object.rsplit(":", 1)[1]
        language = "Python" if servers[0].file.endswith(".py") else "Node.js"
        detail = f"{SERVERS.get(kind, kind)} · {language}"
        folder = _slash(posixpath.dirname(servers[0].file))
        return [Unit(f"server:{label}", "server", root, files, servers, detail, folder, services)]
    return _command_and_library(facts, root, files, services) or [
        Unit(f"folder:{label}", "folder", root, files, [], "dossier", _slash(root), services, inferred=True)
    ]


def _command_and_library(facts: Facts, root: str, files: set[str], services: list[str]) -> list[Unit]:
    scripts = [c for c in facts.signals_starting("script:", files) if posixpath.dirname(c.file) == root]
    exports = [
        c
        for c in facts.signal("exports", files) + facts.signal("library", files)
        if not _not_runtime(posixpath.dirname(c.file))  # a test package exporting helpers is no library
    ]
    exports.sort(key=lambda c: c.file.count("/"))  # the top package, not one of its sub-packages
    units: list[Unit] = []
    cli_files: set[str] = set()
    if scripts:
        target = scripts[0].object.split("=", 1)[1].split(":", 1)[0]
        cli_files = _module_files(root, target, files) or files
        commands = facts.commands(cli_files)
        names = [c.object.split(":", 2)[2].split("=", 1)[0] for c in scripts]
        detail = f"{len(commands)} commandes" if len(commands) > 1 else " · ".join(names)
        folder = posixpath.basename(sorted(cli_files)[0]) if len(cli_files) == 1 else _slash(root)
        units.append(Unit(f"cli:{names[0]}", "cli", root, cli_files, scripts, detail, folder, services))
    if exports:
        package = posixpath.dirname(exports[0].file)
        lib_files = {f for f in files if under(package, f)} - cli_files
        detail, main = _main_classes(facts, lib_files)
        name = posixpath.basename(package) or facts.name
        folder = posixpath.basename(main) if main else _slash(package)
        units.append(Unit(f"library:{name}", "library", package, lib_files, exports, detail or name, folder))
    return units


def _module_files(root: str, target: str, files: set[str]) -> set[str]:
    """`sqlite_utils.cli` → the file of that module in the unit (`src/` layouts included); a path such as
    `./bin/cli.js` (package.json `bin`) → that file."""
    if "/" in target or target.endswith((".js", ".mjs", ".cjs", ".ts")):
        path = posixpath.normpath(posixpath.join(root, target))
        return {path} & files
    module = target.replace(".", "/")
    return {
        f
        for f in files
        if f.endswith((f"{module}.py", f"{module}/__init__.py", f"{module}.js", f"{module}.ts"))
    }


def _main_classes(facts: Facts, files: set[str]) -> tuple[str, str]:
    """The two largest classes of the library's file holding the most class lines, and that file."""
    sizes: dict[str, list[tuple[int, int, str]]] = {}
    for claim in facts.classes:
        if claim.file in files:
            name = claim.object.split("::", 1)[1]
            if "." not in name and not name.startswith("_"):
                size = claim.line_end - claim.line_start
                sizes.setdefault(claim.file, []).append((size, claim.line_start, name))
    if not sizes:
        return "", ""
    main = max(sorted(sizes), key=lambda f: sum(size for size, _, _ in sizes[f]))
    largest = sorted(sizes[main], key=lambda s: (-s[0], s[1]))[:2]
    return " · ".join(name for _, _, name in sorted(largest, key=lambda s: s[1])), main


def _slash(directory: str) -> str:
    return f"{directory}/" if directory else ""

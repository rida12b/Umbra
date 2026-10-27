"""ADR-0004: the Secret Guard is the only reader of Project files.

Parses every engine module outside `umbra_engine/guard/` and fails on a fixed list of ways to read
files, list directories, use introspection or dynamic code, reach guard internals or copy a
GuardedFile. External programs (git, a Project's test run) are legitimate but may only be
started from `umbra_engine/gateways/`, whose outputs must pass through the guard before use.
It catches mistakes, not deliberate obfuscation; review covers intent.
"""

import ast
from pathlib import Path

import pytest
from secret_fixtures import write_repo

import umbra_engine
from umbra_engine.guard import GuardedFile, SecretGuard

ENGINE = Path(str(umbra_engine.__file__)).parent
GUARD = ENGINE / "guard"
GATEWAYS = "gateways/"

# Builtins that read files or defeat the static check, banned as bare names (called or referenced).
BANNED_BUILTINS = {"open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr", "vars"}
# Methods that read or list the filesystem, banned on any object.
BANNED_METHODS = {
    "read_text",
    "read_bytes",
    "open",
    "fdopen",
    "iterdir",
    "glob",
    "rglob",
    "scandir",
    "listdir",
}
# Dunder access that forges objects or reaches internals.
BANNED_DUNDERS = {"__dict__", "__new__", "__setattr__", "__getattribute__", "__reduce__"}
# Functions banned only on a given module (the same name is fine elsewhere: `ast.walk`, `tree.walk()`).
BANNED_ON = {
    "os": {
        "walk",
        "system",
        "popen",
        "startfile",
        "read",
        "posix_spawn",
        "execv",
        "execve",
        "execvp",
        "spawnv",
    },
    "dataclasses": {"replace"},
    "copy": {"replace"},
}
BANNED_MODULES = {
    "mmap", "glob", "shutil", "fileinput", "linecache", "zipfile", "tarfile", "builtins", "importlib",
    "pickle", "marshal", "sqlite3", "ctypes", "pty", "runpy",
}  # fmt: skip
GATEWAY_ONLY_MODULES = {"subprocess"}

# module (relative to the package) -> banned names or modules it may use, with the reason.
ALLOWED: dict[str, set[str]] = {
    "settings.py": {"open", "fdopen", "read_text"},  # Umbra's own token file under UMBRA_HOME
    "sqlite_db.py": {"sqlite3"},  # Umbra's own stores under UMBRA_HOME
    "cli.py": {"sqlite3", "getattr"},  # catch sqlite3.Error; optional stream.reconfigure()
    "journal.py": {"iterdir", "read_text"},  # Umbra's own event spool under UMBRA_HOME, never a Project
}


def violations(source: str, module: str) -> list[str]:
    allowed = ALLOWED.get(module, set())
    found = []
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Name) and node.id in BANNED_BUILTINS - allowed:
            found.append(f"{module}:{line} uses {node.id}")
        elif isinstance(node, ast.Attribute):
            found += _attribute_problems(node, allowed, module, line)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found += _module_problems(alias.name, set(), allowed, module, line)
        elif isinstance(node, ast.ImportFrom):
            found += _module_problems(node.module or "", {a.name for a in node.names}, allowed, module, line)
    return found


def _attribute_problems(node: ast.Attribute, allowed: set[str], module: str, line: int) -> list[str]:
    name, owner = node.attr, getattr(node.value, "id", None)
    if name in (BANNED_METHODS | BANNED_DUNDERS) - allowed:
        return [f"{module}:{line} uses .{name}"]
    if owner in BANNED_ON and name in BANNED_ON[owner]:
        return [f"{module}:{line} uses {owner}.{name}"]
    if _is_private(name) and owner not in {"self", "cls"}:
        return [f"{module}:{line} touches private attribute {name} of another object"]
    return []


def _module_problems(imported: str, names: set[str], allowed: set[str], module: str, line: int) -> list[str]:
    top = imported.split(".")[0]
    problems = []
    if top in BANNED_MODULES - allowed:
        problems.append(f"{module}:{line} imports {imported}")
    if top in GATEWAY_ONLY_MODULES and not module.startswith(GATEWAYS):
        problems.append(f"{module}:{line} imports {imported} outside {GATEWAYS}")
    if top in BANNED_ON and names & BANNED_ON[top]:
        problems.append(f"{module}:{line} imports {sorted(names & BANNED_ON[top])} from {top}")
    if imported.startswith("umbra_engine.guard."):
        problems.append(f"{module}:{line} imports guard internals from {imported}")
    if imported == "umbra_engine.guard" and any(n.startswith("_") for n in names):
        problems.append(f"{module}:{line} imports private guard names {sorted(names)}")
    return problems


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def test_no_engine_module_reads_project_files_outside_the_guard():
    problems = []
    for path in ENGINE.rglob("*.py"):
        if not path.is_relative_to(GUARD):
            problems += violations(path.read_text(encoding="utf-8"), path.relative_to(ENGINE).as_posix())
    assert problems == []


BAD_ANALYZER = """\
import subprocess, builtins, importlib
from pathlib import Path
from dataclasses import replace
from umbra_engine.guard._listing import list_files
from umbra_engine.guard.content import RuleSet
from umbra_engine.guard import _SEAL, GuardedFile
def analyze(root, guarded, guard, os, copy):
    open(root / "a.py")
    reader = Path.read_text
    getattr(Path, "read_" + "text")(root)
    os.system("cat x")
    __import__("subprocess")
    exec("x")
    GuardedFile.__new__(GuardedFile)
    vars(guarded)["_seal"]
    guard._rules = None
    os.walk(root), copy.replace(guarded, text="raw")
    return guarded._seal, guard.__dict__
"""


def test_the_boundary_check_catches_every_kind_of_bypass():
    """A deliberately bad Analyzer: if this stops failing, the boundary test above protects nothing."""
    found = violations(BAD_ANALYZER, "analyzers/bad.py")
    flagged_lines = {int(problem.split(":")[1].split()[0]) for problem in found}
    assert flagged_lines == set(range(1, 19)) - {2, 7}, found


GOOD_ANALYZER = """\
import ast, copy, io, json, re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from umbra_engine.guard import GuardedFile

@dataclass(frozen=True)
class Route:
    name: str
    tags: list[str] = field(default_factory=list)

def analyze(files: list[GuardedFile], tree):
    pattern = re.compile(r"@app\\.(get|post)")
    for guarded in files:
        suffix = PurePosixPath(guarded.rel_path).suffix
        nodes = list(ast.walk(ast.parse(guarded.text)))
        cursor = tree.walk()
        data = json.loads(guarded.text) if suffix == ".json" else {}
        buffer = io.StringIO(guarded.text)
        snapshot = copy.copy(data)
        yield Route(pattern.pattern), nodes, cursor, buffer, snapshot
"""


def test_ordinary_analyzer_code_is_not_flagged():
    """Parsing, regexes, path arithmetic, AST and tree-sitter walks must stay possible."""
    assert violations(GOOD_ANALYZER, "analyzers/good.py") == []


def test_external_programs_are_allowed_only_from_gateways():
    process = "import subprocess\nsubprocess.run(['git', 'rev-parse', 'HEAD'])\n"
    assert violations(process, "gateways/git.py") == []
    assert violations(process, "analyzers/syft.py") != []
    assert violations(process, "watcher.py") != []


def test_the_allowlist_stays_minimal():
    assert all((ENGINE / name).exists() for name in ALLOWED)
    assert sum(len(entries) for entries in ALLOWED.values()) == 8


def test_a_guarded_file_cannot_be_built_outside_the_guard(make_repo):
    with pytest.raises(TypeError):
        GuardedFile("a.py", "raw secret", ())
    root = write_repo(make_repo("seal"), {"a.py": "x = 1\n"}, git=False)
    (released,) = SecretGuard(root).files()
    with pytest.raises(TypeError):
        GuardedFile(released.rel_path, "raw secret", ())

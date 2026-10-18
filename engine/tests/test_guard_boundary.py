"""ADR-0004: the Secret Guard is the only reader of Project files.

Parses every engine module outside `umbra_engine/guard/` and fails on a fixed list of ways to read
files, list directories, run programs, use introspection or dynamic code, reach guard internals or
copy a GuardedFile. It catches mistakes, not deliberate obfuscation; review covers intent. A new
exception goes into ALLOWED with its reason, which is visible in review.
"""

import ast
from pathlib import Path

import pytest
from secret_fixtures import write_repo

import umbra_engine
from umbra_engine.guard import GuardedFile, SecretGuard

ENGINE = Path(str(umbra_engine.__file__)).parent
GUARD = ENGINE / "guard"

# Attribute or function names that read, list, run or bypass, whether called or just referenced.
FORBIDDEN_NAMES = {
    "open", "read_text", "read_bytes", "fdopen", "iterdir", "glob", "rglob", "walk", "scandir", "listdir",
    "system", "popen", "startfile", "execv", "execve", "execvp", "spawnv", "spawnl", "posix_spawn",
    "getattr", "setattr", "delattr", "vars", "exec", "eval", "compile", "__import__", "__dict__",
    "__new__", "__setattr__", "__getattribute__", "__reduce__",
}  # fmt: skip
FORBIDDEN_MODULES = {
    "subprocess", "mmap", "glob", "shutil", "fileinput", "linecache", "zipfile", "tarfile", "io",
    "builtins", "importlib", "copy", "pickle", "marshal", "sqlite3", "codecs", "ctypes", "pty", "runpy",
}  # fmt: skip

# module (relative to the package) -> forbidden names or modules it may use, with the reason.
ALLOWED: dict[str, set[str]] = {
    "settings.py": {"open", "fdopen", "read_text"},  # Umbra's own token file under UMBRA_HOME
    "sqlite_db.py": {"sqlite3"},  # Umbra's own stores under UMBRA_HOME
    "cli.py": {"sqlite3", "getattr"},  # catch sqlite3.Error; optional stream.reconfigure()
}


def violations(source: str, module: str) -> list[str]:
    allowed = ALLOWED.get(module, set())
    found = []
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", 0)
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
            owner = getattr(node.value, "id", None)
            if _is_private(name) and owner not in {"self", "cls"} and name not in FORBIDDEN_NAMES:
                found.append(f"{module}:{line} touches private attribute {name} of another object")
        elif isinstance(node, ast.Name):
            name = node.id
        if name in FORBIDDEN_NAMES and name not in allowed:
            found.append(f"{module}:{line} uses {name}")
        if isinstance(node, ast.Attribute) and node.attr == "replace" and owner_name(node) == "dataclasses":
            found.append(f"{module}:{line} copies a dataclass with dataclasses.replace")
        if isinstance(node, ast.Import):
            for alias in node.names:
                found += _module_problems(alias.name, set(), allowed, module, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            found += _module_problems(node.module or "", names, allowed, module, node.lineno)
    return found


def owner_name(node: ast.Attribute) -> str | None:
    return getattr(node.value, "id", None)


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _module_problems(imported: str, names: set[str], allowed: set[str], module: str, line: int) -> list[str]:
    top = imported.split(".")[0]
    problems = []
    if top in FORBIDDEN_MODULES and top not in allowed:
        problems.append(f"{module}:{line} imports {imported}")
    if imported.startswith("umbra_engine.guard."):
        problems.append(f"{module}:{line} imports guard internals from {imported}")
    if imported == "dataclasses" and "replace" in names:
        problems.append(f"{module}:{line} imports dataclasses.replace")
    if imported == "umbra_engine.guard" and any(n.startswith("_") for n in names):
        problems.append(f"{module}:{line} imports private guard names {sorted(names)}")
    return problems


def engine_modules() -> list[Path]:
    return [p for p in ENGINE.rglob("*.py") if not p.is_relative_to(GUARD)]


def test_no_engine_module_reads_project_files_outside_the_guard():
    problems = []
    for path in engine_modules():
        problems += violations(path.read_text(encoding="utf-8"), path.relative_to(ENGINE).as_posix())
    assert problems == []


BAD_ANALYZER = """\
import subprocess, copy, builtins, importlib
from pathlib import Path
from dataclasses import replace
from umbra_engine.guard._listing import list_files
from umbra_engine.guard.content import RuleSet
from umbra_engine.guard import _SEAL, GuardedFile
def analyze(root, guarded, guard, os):
    open(root / "a.py")
    reader = Path.read_text
    getattr(Path, "read_" + "text")(root)
    os.system("cat x")
    __import__("subprocess")
    exec("x")
    GuardedFile.__new__(GuardedFile)
    vars(guarded)["_seal"]
    guard._rules = None
    return guarded._seal, guard.__dict__
"""


def test_the_boundary_check_catches_every_kind_of_bypass():
    """A deliberately bad Analyzer: if this stops failing, the boundary test above protects nothing."""
    found = violations(BAD_ANALYZER, "analyzers/bad.py")
    flagged_lines = {int(problem.split(":")[1].split()[0]) for problem in found}
    assert flagged_lines == set(range(1, 18)) - {2, 7}, found


def test_the_allowlist_stays_minimal():
    assert all((ENGINE / name).exists() for name in ALLOWED)
    assert sum(len(entries) for entries in ALLOWED.values()) == 6


def test_a_guarded_file_cannot_be_built_outside_the_guard(make_repo):
    with pytest.raises(TypeError):
        GuardedFile("a.py", "raw secret", ())
    root = write_repo(make_repo("seal"), {"a.py": "x = 1\n"}, git=False)
    (released,) = SecretGuard(root).files()
    with pytest.raises(TypeError):
        GuardedFile(released.rel_path, "raw secret", ())

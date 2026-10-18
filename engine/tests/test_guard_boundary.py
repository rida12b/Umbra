"""ADR-0004: the Secret Guard is the only reader of Project files.

Parses every engine module outside `umbra_engine/guard/` and fails on any way to read files, list
directories, run external programs, reach guard internals or forge a GuardedFile. A new exception
must be added to ALLOWED below, which is visible in review.
"""

import ast
from dataclasses import replace
from pathlib import Path

import pytest
from secret_fixtures import write_repo

import umbra_engine
from umbra_engine.guard import GuardedFile, SecretGuard

ENGINE = Path(str(umbra_engine.__file__)).parent
GUARD = ENGINE / "guard"

READING_CALLS = {
    "open",
    "read_text",
    "read_bytes",
    "fdopen",
    "iterdir",
    "glob",
    "rglob",
    "walk",
    "scandir",
    "listdir",
}
READING_MODULES = {
    "subprocess",
    "mmap",
    "glob",
    "shutil",
    "fileinput",
    "linecache",
    "zipfile",
    "tarfile",
    "io",
}
GUARD_INTERNALS = {"_seal", "_SEAL", "_root", "_listing", "list_files"}

# file (relative to the package) -> calls it may make, with the reason.
ALLOWED: dict[str, set[str]] = {
    "settings.py": {
        "open",
        "fdopen",
        "read_text",
    },  # Umbra's own token file under UMBRA_HOME, never a Project file
}


def violations(source: str, module: str) -> list[str]:
    found = []
    allowed = ALLOWED.get(module, set())
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
            if name in READING_CALLS and name not in allowed:
                found.append(f"{module}:{node.lineno} calls {name}()")
            if name == "replace" and isinstance(node.func, ast.Attribute):
                if getattr(node.func.value, "id", None) == "dataclasses":
                    found.append(f"{module}:{node.lineno} copies a dataclass with dataclasses.replace()")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in READING_MODULES or alias.name.startswith(
                    "umbra_engine.guard."
                ):
                    found.append(f"{module}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            source_module = node.module or ""
            names = {alias.name for alias in node.names}
            if source_module.split(".")[0] in READING_MODULES:
                found.append(f"{module}:{node.lineno} imports from {source_module}")
            if (
                source_module.startswith("umbra_engine.guard.")
                and source_module != "umbra_engine.guard.content"
            ):
                found.append(f"{module}:{node.lineno} imports guard internals from {source_module}")
            if source_module == "dataclasses" and "replace" in names:
                found.append(f"{module}:{node.lineno} imports dataclasses.replace")
            if source_module.startswith("umbra_engine.guard") and names & GUARD_INTERNALS:
                found.append(f"{module}:{node.lineno} imports {sorted(names & GUARD_INTERNALS)}")
        elif isinstance(node, ast.Attribute) and node.attr in GUARD_INTERNALS:
            found.append(f"{module}:{node.lineno} touches {node.attr}")
    return found


def engine_modules() -> list[Path]:
    return [p for p in ENGINE.rglob("*.py") if not p.is_relative_to(GUARD)]


def test_no_engine_module_reads_project_files_outside_the_guard():
    problems = []
    for path in engine_modules():
        problems += violations(path.read_text(encoding="utf-8"), path.relative_to(ENGINE).as_posix())
    assert problems == []


def test_the_boundary_check_catches_every_kind_of_bypass():
    """A deliberately bad Analyzer: if this stops failing, the boundary test above protects nothing."""
    bad_analyzer = """
import subprocess
from pathlib import Path
from dataclasses import replace
from umbra_engine.guard._listing import list_files
from umbra_engine.guard import _SEAL, GuardedFile

def analyze(root, guarded):
    open(root / "a.py")
    Path(root, "b.py").read_text()
    (root / "c.py").read_bytes()
    list(root.rglob("*.py"))
    subprocess.run(["cat", "d.py"])
    GuardedFile("x", "raw", (), _seal=_SEAL)
    replace(guarded, text="raw")
    return guarded._seal, guard._root
"""
    found = violations(bad_analyzer, "analyzers/bad.py")
    flagged_lines = {int(problem.split(":")[1].split()[0]) for problem in found}
    assert flagged_lines == {2, 4, 5, 6, 9, 10, 11, 12, 16}, found


def test_the_allowlist_stays_minimal():
    assert set(ALLOWED) == {"settings.py"}
    assert all(path.exists() for path in (ENGINE / name for name in ALLOWED))


def test_a_guarded_file_cannot_be_forged_or_copied_with_raw_text(make_repo):
    with pytest.raises(TypeError):
        GuardedFile("a.py", "raw secret", ())

    root = write_repo(make_repo("seal"), {"a.py": "x = 1\n"}, git=False)
    (released,) = SecretGuard(root).files()
    assert isinstance(released, GuardedFile)
    forged = replace(released, text="raw secret")  # possible in Python, hence the static ban above
    assert forged.text == "raw secret"

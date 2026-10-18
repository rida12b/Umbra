"""Which files belong to a Project: what git tracks plus untracked files git does not ignore.

Private to the guard package: names can hold secrets too, so only the guard may hand them out.
"""

import os
import subprocess
from pathlib import Path

import pathspec

ALWAYS_SKIPPED_DIRS = {".git", ".hg", ".svn"}
GIT_TIMEOUT_S = 120
UNDECODABLE = "�"


def list_files(root: Path) -> list[str]:
    """Relative POSIX paths of the Project's files, sorted. Uses git when the folder is a repository.

    A name git reports in an encoding that cannot be decoded is kept (with U+FFFD), so it can be
    reported as a Coverage Gap instead of vanishing; tracked files missing on disk are dropped.
    """
    files = _git_files(root)
    if files is None:
        files = _walk_files(root)
    return sorted(f for f in set(files) if UNDECODABLE in f or (root / f).is_file())


def _git_files(root: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True,
            check=True,
            timeout=GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return [entry.decode("utf-8", errors="replace") for entry in result.stdout.split(b"\0") if entry]


def _walk_files(root: Path) -> list[str]:
    """Fallback for folders that are not git repositories.

    Honours every `.gitignore` on the way down, each relative to its own folder. Approximation of git:
    a deeper `!pattern` cannot re-include what a parent ignores.
    """
    specs: dict[str, list[tuple[str, pathspec.GitIgnoreSpec]]] = {}
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        parent = Path(rel_dir).parent.as_posix() if rel_dir != "." else None
        inherited = specs.get(parent, []) if parent is not None else []
        own = _gitignore(Path(dirpath))
        active = [*inherited, (rel_dir, own)] if own is not None else inherited
        specs[rel_dir] = active

        dirnames[:] = [
            d
            for d in dirnames
            if d not in ALWAYS_SKIPPED_DIRS and not _ignored(active, _join(rel_dir, d), True)
        ]
        files += [rel for f in filenames if not _ignored(active, rel := _join(rel_dir, f))]
    return files


def _ignored(active: list[tuple[str, pathspec.GitIgnoreSpec]], rel: str, is_dir: bool = False) -> bool:
    for base, spec in active:
        local = rel if base == "." else rel.removeprefix(base + "/")
        if spec.match_file(local + ("/" if is_dir else "")):
            return True
    return False


def _gitignore(directory: Path) -> pathspec.GitIgnoreSpec | None:
    file = directory / ".gitignore"
    if not file.is_file():
        return None
    return pathspec.GitIgnoreSpec.from_lines(file.read_text(encoding="utf-8", errors="replace").splitlines())


def _join(rel_dir: str, name: str) -> str:
    return name if rel_dir == "." else f"{rel_dir}/{name}"

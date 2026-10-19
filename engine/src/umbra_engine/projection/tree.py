"""The Zoom Levels as a tree: Application → services → Components (directories) → Modules → definitions.

Components come from Facts: a service's code root (the directory of the Dockerfile it is built from),
then directories. A directory holding a single sub-directory and no file is merged with it
(`backend/app`), so every level shows a real choice.
"""

import posixpath

from umbra_engine.projection.graph import ProjectGraph
from umbra_engine.projection.model import APPLICATION

DIR = "dir:"


def children(graph: ProjectGraph, key: str) -> list[str]:
    if key == APPLICATION:
        claimed = [s.code_root for s in graph.services.values() if s.code_root is not None]
        outside = [
            c
            for c in _directory_children(graph, "")
            if not _covered(c, claimed) and c not in graph.declaration_files
        ]
        return sorted(graph.services) + outside
    if key in graph.services:
        root = graph.services[key].code_root
        return _directory_children(graph, root) if root is not None else []
    if key.startswith(DIR):
        return _directory_children(graph, key.removeprefix(DIR))
    if key in graph.definitions:
        return graph.children_of_definition.get(key, [])
    return graph.top_definitions.get(key, [])


def files_under(graph: ProjectGraph, key: str) -> list[str]:
    """The Modules an element stands for (a definition stands for its file)."""
    if key == APPLICATION:
        return graph.files
    if key in graph.services:
        root = graph.services[key].code_root
        return graph.files_in(root) if root is not None else []
    if key.startswith(DIR):
        return graph.files_in(key.removeprefix(DIR))
    return [key.split("::", 1)[0]]


def path_to(graph: ProjectGraph, target: str) -> list[str]:
    """Keys from the Application down to `target` (inclusive), following `children`."""
    path, current = [APPLICATION], APPLICATION
    while current != target:
        step = next((c for c in children(graph, current) if _contains(graph, c, target)), None)
        if step is None:
            return path if target == APPLICATION else []
        path.append(step)
        current = step
    return path


def _contains(graph: ProjectGraph, key: str, target: str) -> bool:
    if key == target:
        return True
    if key in graph.definitions or not (key.startswith(DIR) or key in graph.services):
        return target.startswith(key + ("." if "::" in key else "::"))
    if target in graph.services:
        return False  # services are children of the Application only
    target_file = target.removeprefix(DIR).split("::", 1)[0]
    if key in graph.services:
        # A service shows what is inside its code root, not the root itself: that directory keeps
        # its own place in the tree (`src/frontend` under `src`).
        root = graph.services[key].code_root
        return root is not None and (root == "" or target_file.startswith(root + "/"))
    root = key.removeprefix(DIR)
    return root == "" or target_file == root or target_file.startswith(root + "/")


def _directory_children(graph: ProjectGraph, directory: str) -> list[str]:
    subdirs, files = graph.directories.get(directory, ([], []))
    return [DIR + _collapse(graph, d) for d in subdirs] + files


def _collapse(graph: ProjectGraph, directory: str) -> str:
    while True:
        subdirs, files = graph.directories.get(directory, ([], []))
        if len(subdirs) != 1 or files:
            return directory
        directory = subdirs[0]


def _covered(child: str, roots: list[str]) -> bool:
    """A root-level directory entirely made of service code is shown through those services instead."""
    path = child.removeprefix(DIR)
    return child.startswith(DIR) and any(r == "" or path == r or path.startswith(r + "/") for r in roots)


def label(graph: ProjectGraph, parent: str, key: str) -> str:
    if key in graph.services:
        return graph.services[key].label
    if key.startswith(DIR):
        path, base = key.removeprefix(DIR), _directory_of(graph, parent)
        return posixpath.relpath(path, base) if base else path
    if key in graph.definitions:
        return key.split("::", 1)[1].rsplit(".", 1)[-1]
    return posixpath.basename(key) if key != APPLICATION else graph.name


def _directory_of(graph: ProjectGraph, key: str) -> str:
    if key in graph.services:
        return graph.services[key].code_root or ""
    return key.removeprefix(DIR) if key.startswith(DIR) else ""

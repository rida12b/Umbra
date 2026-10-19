"""The guarded copy Claude Code studies: only text released by the Secret Guard (secrets masked,
private files absent), plus UMBRA_INDEX.md, Umbra's own map of the Project to start from."""

import re
from collections import Counter, defaultdict
from pathlib import Path

from umbra_engine.claims import StoredClaim
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.projection.graph import ProjectGraph

INDEX_FILE = "UMBRA_INDEX.md"
MAX_INDEX_CHARS = 300_000
LIBRARIES_PER_FOLDER = 25


def write_mirror(guard: SecretGuard, destination: Path) -> dict[str, str]:
    """Copy every released file into `destination`; returns their texts, by path, for later diffs."""
    texts = {}
    for released in guard.files():
        if not isinstance(released, GuardedFile):
            continue
        target = destination / released.rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(released.text, encoding="utf-8")
        texts[released.rel_path] = released.text
    return texts


def write_index(
    graph: ProjectGraph, imports: list[StoredClaim], copied: list[str], destination: Path
) -> None:
    (destination / INDEX_FILE).write_text(index_text(graph, imports, copied), encoding="utf-8")


def index_text(graph: ProjectGraph, imports: list[StoredClaim], copied: list[str]) -> str:
    links: dict[str, list[str]] = defaultdict(list)
    for claim in graph.module_links:
        links[claim.subject].append(f"{claim.object.removeprefix('dir:')} (l.{claim.line_start})")
    lines = [
        "# UMBRA_INDEX — Umbra's map of this project (generated; every path is relative to this folder)",
        "",
        f"## Files ({len(graph.files)}): path — top definitions (lines) — imports resolved to project files",
    ]
    for path in graph.files:
        definitions = [
            f"{key.split('::', 1)[1]} ({graph.definitions[key].lines[0]}-{graph.definitions[key].lines[1]})"
            for key in graph.top_definitions.get(path, [])
        ]
        entry = f"- {path}"
        if definitions:
            entry += " — " + ", ".join(definitions[:30])
        if links.get(path):
            entry += " — imports " + ", ".join(links[path][:15])
        lines.append(entry)
    others = sorted(set(copied) - set(graph.files))
    lines += [
        "",
        f"## Other readable files ({len(others)}): no Umbra analyser for them, open them directly",
        *(f"- {path}" for path in others),
        "",
        "## Declared services (compose, Kubernetes)",
        services_summary(graph),
        "",
        "## Outside libraries imported, per top folder",
        libraries_by_folder(graph, imports),
    ]
    return "\n".join(lines)[:MAX_INDEX_CHARS]


def libraries_by_folder(graph: ProjectGraph, imports: list[StoredClaim]) -> str:
    """Imports that resolve to no file of the Project are outside libraries: they tell the technology."""
    internal = {(c.subject, c.line_start) for c in graph.module_links}
    per_folder: dict[str, Counter[str]] = defaultdict(Counter)
    for claim in imports:
        if (claim.file, claim.line_start) in internal or claim.object.startswith((".", "/")):
            continue
        name = re.split(r"[/.:]", claim.object.lstrip("@"))[0]
        folder = claim.file.split("/")[0] if "/" in claim.file else "(root)"
        if name:
            per_folder[folder][name] += 1
    lines = [
        f"{folder}: {', '.join(n for n, _ in names.most_common(LIBRARIES_PER_FOLDER))}"
        for folder, names in sorted(per_folder.items())
    ]
    return "\n".join(lines) or "(none)"


def services_summary(graph: ProjectGraph) -> str:
    links = defaultdict(list)
    for claim in graph.service_links:
        links[claim.subject].append(f"{claim.relation} {claim.object}")
    return (
        "\n".join(
            f"{s.key}: image {', '.join(s.images) or '-'}; ports {', '.join(s.ports) or '-'}; "
            f"code {s.code_root if s.code_root is not None else '-'}; {'; '.join(links[s.key])}"
            for s in graph.services.values()
        )
        or "(none declared)"
    )

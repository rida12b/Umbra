"""Search by name: jump to any service, folder, Module or definition of the map."""

from dataclasses import dataclass

from umbra_engine.projection.graph import ProjectGraph
from umbra_engine.projection.model import APPLICATION, NodeKind
from umbra_engine.projection.tree import DIR, path_to
from umbra_engine.projection.view import node

MAX_HITS = 20


@dataclass(frozen=True)
class SearchHit:
    key: str
    kind: NodeKind
    label: str
    path: str | None
    level: str  # the element whose view shows this one: open it, then select `key`


def search(graph: ProjectGraph, query: str, limit: int = MAX_HITS) -> list[SearchHit]:
    """Exact names first, then names starting with the query, then names containing it."""
    wanted = query.strip().lower()
    if not wanted:
        return []
    names = [(key, graph.services[key].label) for key in graph.services]
    names += [(DIR + d, d.rsplit("/", 1)[-1]) for d in graph.directories if d]
    names += [(path, path.rsplit("/", 1)[-1]) for path in graph.files]
    names += [(key, key.split("::", 1)[1].split("~", 1)[0].rsplit(".", 1)[-1]) for key in graph.definitions]
    ranked = sorted(
        ((_rank(name.lower(), wanted), len(key), key) for key, name in names if wanted in name.lower()),
    )
    hits: list[SearchHit] = []
    for _, _, key in ranked:
        trail = path_to(graph, key)  # a folder merged into its only child has no view of its own
        if len(trail) < 2:
            continue
        found = node(graph, trail[-2], key)
        hits.append(SearchHit(key, found.kind, found.label, found.path, trail[-2] or APPLICATION))
        if len(hits) == limit:
            break
    return hits


def _rank(name: str, wanted: str) -> int:
    return 0 if name == wanted else 1 if name.startswith(wanted) else 2

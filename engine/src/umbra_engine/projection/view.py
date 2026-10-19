"""One map view: the children of an element, at most ~12 shown, and the links between them."""

from collections import defaultdict

from umbra_engine.claims import IMPORTS_MODULE, StoredClaim
from umbra_engine.projection.graph import ProjectGraph
from umbra_engine.projection.model import (
    APPLICATION,
    MAX_VISIBLE,
    Crumb,
    MapEdge,
    MapNode,
    MapView,
    NodeKind,
    NodeStatus,
)
from umbra_engine.projection.tree import DIR, children, files_under, label, path_to

EVIDENCE_SAMPLE = 5
DEFINITION_KINDS: dict[str, NodeKind] = {"class": "class", "method": "method", "type": "type"}


class UnknownElementError(KeyError):
    """The key names nothing in this Project's map."""


def map_view(graph: ProjectGraph, key: str = APPLICATION, expand: bool = False) -> MapView:
    crumbs_keys = path_to(graph, key)
    if not crumbs_keys:
        raise UnknownElementError(key)
    child_keys = children(graph, key)
    weights = {c: len(files_under(graph, c)) for c in child_keys}
    shown = child_keys if expand or len(child_keys) <= MAX_VISIBLE else _largest(child_keys, weights)
    hidden = [c for c in child_keys if c not in shown]
    nodes = [node(graph, key, c) for c in shown]
    if hidden:
        nodes.append(
            MapNode(f"group:{key}", "group", f"+{len(hidden)} more", "fact", len(hidden), hidden=hidden)
        )
    representative = {c: c for c in shown} | {c: f"group:{key}" for c in hidden}
    crumbs = [
        Crumb(k, _kind(graph, k), label(graph, p, k))
        for p, k in zip([APPLICATION, *crumbs_keys], crumbs_keys, strict=False)
    ]
    return MapView(
        parent=node(graph, crumbs_keys[-2] if len(crumbs_keys) > 1 else APPLICATION, key),
        breadcrumbs=crumbs,
        nodes=nodes,
        edges=_edges(graph, child_keys, representative),
        total_children=len(child_keys),
    )


def node(graph: ProjectGraph, parent: str, key: str) -> MapNode:
    kind = _kind(graph, key)
    count = len(children(graph, key))
    if key in graph.services:
        service = graph.services[key]
        details = {
            "images": service.images,
            "ports": service.ports,
            "declared in": sorted({c.file for c in service.declared_by}),
        }
        root = [service.code_root] if service.code_root is not None else []
        return MapNode(key, kind, service.label, "declaration", count, details=details | {"code": root})
    if key in graph.definitions:
        definition = graph.definitions[key]
        status = "fact" if definition.status == "fact" else "hypothesis"
        return MapNode(
            key, kind, label(graph, parent, key), status, count, path=definition.file, lines=definition.lines
        )
    path = key.removeprefix(DIR) if key.startswith(DIR) else (None if key == APPLICATION else key)
    return MapNode(key, kind, label(graph, parent, key), "fact", count, path=path)


def _kind(graph: ProjectGraph, key: str) -> NodeKind:
    if key == APPLICATION:
        return "application"
    if key in graph.services:
        return "service"
    if key.startswith(DIR):
        return "component"
    if key in graph.definitions:
        return DEFINITION_KINDS.get(graph.definitions[key].kind, "function")
    return "module"


def _largest(keys: list[str], weights: dict[str, int]) -> list[str]:
    """The heaviest elements first, in their original order; the rest goes into one group."""
    kept = set(sorted(keys, key=lambda k: (-weights[k], k))[: MAX_VISIBLE - 1])
    return [k for k in keys if k in kept]


def _edges(graph: ProjectGraph, child_keys: list[str], representative: dict[str, str]) -> list[MapEdge]:
    owner = {file: c for c in child_keys for file in files_under(graph, c)}
    grouped: dict[tuple[str, str, str], list[StoredClaim]] = defaultdict(list)
    for claim in graph.module_links:
        source = owner.get(claim.subject)
        target = owner.get(claim.object) or _owner_of_directory(claim.object, owner)
        if source and target and source != target:
            grouped[(representative[source], representative[target], "imports")].append(claim)
    for claim in graph.service_links:
        if claim.subject in representative and claim.object in representative:
            grouped[(representative[claim.subject], representative[claim.object], claim.relation)].append(
                claim
            )
    return [
        MapEdge(
            source, target, relation, _status(claims), len(claims), [c.key for c in claims[:EVIDENCE_SAMPLE]]
        )
        for (source, target, relation), claims in sorted(grouped.items())
        if source != target
    ]


def _owner_of_directory(target: str, owner: dict[str, str]) -> str | None:
    """A Go import names a package directory: its owner is whoever owns a file in it."""
    if not target.startswith(DIR):
        return None
    directory = target.removeprefix(DIR) + "/"
    return next((c for file, c in owner.items() if file.startswith(directory)), None)


def _status(claims: list[StoredClaim]) -> NodeStatus:
    """Service links are Declarations; an import link is a Fact as soon as one Fact backs it."""
    if any(c.relation != IMPORTS_MODULE for c in claims):
        return "declaration"
    return "fact" if any(c.status == "fact" for c in claims) else "hypothesis"

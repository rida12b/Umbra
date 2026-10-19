"""One map view: the children of an element, at most ~12 shown, and the links between them."""

import posixpath
from collections import defaultdict

from umbra_engine.claims import CALLS, IMPORTS_MODULE, StoredClaim
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
    # Services first at the Application level (they are what it is made of), then the largest elements.
    weights = {
        c: (key == APPLICATION and c in graph.services, len(files_under(graph, c))) for c in child_keys
    }
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
        details["code"] = [service.code_root] if service.code_root is not None else []
        if details["code"] and service.code_root_status != "fact":
            details["code status"] = [service.code_root_status]
        evidence = [c.key for c in service.declared_by[:EVIDENCE_SAMPLE]]
        return MapNode(
            key,
            kind,
            service.label,
            "declaration",
            count,
            details=details,
            evidence=evidence,
        )
    if key in graph.definitions:
        definition = graph.definitions[key]
        status = "fact" if definition.status == "fact" else "hypothesis"
        return MapNode(
            key,
            kind,
            label(graph, parent, key),
            status,
            count,
            path=definition.file,
            lines=definition.lines,
            evidence=[definition.claim],
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


def _largest(keys: list[str], weights: dict[str, tuple[bool, int]]) -> list[str]:
    """The heaviest elements, kept in their original order; the rest goes into one group."""
    kept = set(sorted(sorted(keys), key=lambda k: weights[k], reverse=True)[: MAX_VISIBLE - 1])
    return [k for k in keys if k in kept]


def _edges(graph: ProjectGraph, child_keys: list[str], representative: dict[str, str]) -> list[MapEdge]:
    owner: dict[str, str] = {}
    for child in child_keys:  # first wins: services come first and own their code
        for file in files_under(graph, child):
            owner.setdefault(file, child)
    # A Go import names a package directory: it links to the element owning all of that package's files
    # (no link when they are shown as several elements, since the import names none of them).
    package_owners: dict[str, set[str]] = defaultdict(set)
    for file, child in owner.items():
        package_owners[DIR + posixpath.dirname(file)].add(child)
    package_owner = {package: next(iter(c)) for package, c in package_owners.items() if len(c) == 1}
    grouped: dict[tuple[str, str, str], list[StoredClaim]] = defaultdict(list)
    for claim in graph.module_links:
        source = owner.get(claim.subject)
        if source is None:
            continue
        target = owner.get(claim.object) or package_owner.get(claim.object)
        if target and source != target:
            grouped[(representative[source], representative[target], "imports")].append(claim)
    shown = set(child_keys)
    # Inside a file or a class the children are definitions: a call from outside them (module level,
    # another class) has no place there. Elsewhere, a call belongs to the element owning its file.
    by_file = not any(child in graph.definitions for child in child_keys)
    for caller, callee, claim in graph.calls:
        source = _definition_owner(caller, shown) or (
            owner.get(caller.split("::", 1)[0]) if by_file else None
        )
        target = _definition_owner(callee, shown) or (
            owner.get(callee.split("::", 1)[0]) if by_file else None
        )
        if source and target and source != target:
            grouped[(representative[source], representative[target], "calls")].append(claim)
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


def _status(claims: list[StoredClaim]) -> NodeStatus:
    """Service links are Declarations; imports and calls are Facts as soon as one Fact backs them
    (resolved calls are matched names: Hypotheses)."""
    if any(c.relation not in (IMPORTS_MODULE, CALLS) for c in claims):
        return "declaration"
    if any(c.relation == CALLS for c in claims):
        return "hypothesis"
    return "fact" if any(c.status == "fact" for c in claims) else "hypothesis"


def _definition_owner(key: str, shown: set[str]) -> str | None:
    """The shown element a definition belongs to: itself, or its enclosing class or function."""
    while key:
        if key in shown:
            return key
        head, _, rest = key.partition("::")
        if "." not in rest:
            return None
        key = f"{head}::{rest.rsplit('.', 1)[0]}"
    return None

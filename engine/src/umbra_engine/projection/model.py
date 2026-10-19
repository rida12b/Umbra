"""What the map API returns: the children of one element, and the links between them."""

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal[
    "application", "service", "component", "module", "function", "class", "method", "type", "group"
]
NodeStatus = Literal["fact", "hypothesis", "declaration"]

APPLICATION = "app:"
MAX_VISIBLE = 12  # a UX preference (SPEC S2), not a hard limit: the rest is one click away


@dataclass(frozen=True)
class MapNode:
    """One element of the map. `key` is stable: it names what the element is, never a database row."""

    key: str
    kind: NodeKind
    label: str
    status: NodeStatus
    children: int
    path: str | None = None
    lines: tuple[int, int] | None = None
    details: dict[str, list[str]] = field(default_factory=dict)
    hidden: list[str] = field(default_factory=list)  # for a `group`: the keys it stands for
    evidence: list[str] = field(default_factory=list)  # keys of the Claims this element stands on


@dataclass(frozen=True)
class MapEdge:
    """Links aggregated between two visible elements, with the keys of a few Claims that prove them."""

    source: str
    target: str
    relation: str
    status: NodeStatus
    count: int
    evidence: list[str]


@dataclass(frozen=True)
class Crumb:
    key: str
    kind: NodeKind
    label: str


@dataclass(frozen=True)
class MapView:
    parent: MapNode
    breadcrumbs: list[Crumb]
    nodes: list[MapNode]
    edges: list[MapEdge]
    total_children: int

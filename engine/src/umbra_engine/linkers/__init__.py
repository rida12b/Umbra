"""Linkers: Claims that need the whole Project (an import resolved to a file, a Service reaching a
workload, a service built from a code directory). They run after every file is analyzed and reuse the
Evidence of the Claims they are derived from."""

import posixpath
from collections import defaultdict

from umbra_engine.claims import (
    BUILT_FROM,
    CODE_ROOT,
    HAS_LABELS,
    SELECTS,
    TARGETS,
    Claim,
    StoredClaim,
)
from umbra_engine.linkers.imports import ModuleIndex, resolve_imports

PRODUCER = "linker@1.0"


def link(claims: list[StoredClaim], readable_files: set[str]) -> list[tuple[str, Claim]]:
    """`(evidence file, Claim)` for every cross-file link found."""
    return (
        resolve_imports(claims, ModuleIndex(readable_files))
        + _service_targets(claims)
        + _code_roots(claims, readable_files)
    )


def _service_targets(claims: list[StoredClaim]) -> list[tuple[str, Claim]]:
    """A Service targets every workload of the same namespace whose labels include all its selector pairs."""
    selectors: dict[str, list[StoredClaim]] = defaultdict(list)
    labels: dict[str, set[str]] = defaultdict(set)
    for claim in claims:
        if claim.relation == SELECTS:
            selectors[claim.subject].append(claim)
        elif claim.relation == HAS_LABELS:
            labels[claim.subject].add(claim.object)
    links = []
    for service, pairs in selectors.items():
        wanted = {p.object for p in pairs}
        start, end = min(p.line_start for p in pairs), max(p.line_end for p in pairs)
        for workload, owned in sorted(labels.items()):
            if _namespace(workload) == _namespace(service) and wanted <= owned:
                target = Claim(service, "k8s-service", TARGETS, workload, "workload", "fact", start, end)
                links.append((pairs[0].file, target))
    return links


def _code_roots(claims: list[StoredClaim], readable_files: set[str]) -> list[tuple[str, Claim]]:
    """A service built from one of the Project's Dockerfiles has that Dockerfile's directory as code."""
    links = []
    for claim in claims:
        if claim.relation == BUILT_FROM and claim.object.startswith("build:"):
            dockerfile = claim.object.removeprefix("build:")
            if dockerfile in readable_files:
                root = posixpath.dirname(dockerfile) or "."
                root_claim = Claim(claim.subject, "service", CODE_ROOT, f"dir:{root}", "directory", "fact",
                             claim.line_start, claim.line_end)  # fmt: skip
                links.append((claim.file, root_claim))
    return links


def _namespace(key: str) -> str:
    """`k8s:shop/Service/web` → `shop`; no namespace → empty."""
    parts = key.removeprefix("k8s:").split("/")
    return parts[0] if len(parts) == 3 else ""

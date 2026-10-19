"""Map routes: the Zoom Levels of a Project and the Evidence behind each element (SPEC S2)."""

import threading
from collections.abc import Callable
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, params, status

from umbra_engine.claims import StoredClaim
from umbra_engine.evidence import EvidenceExcerpt, EvidenceUnavailableError, excerpt
from umbra_engine.guard import SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.graph import MAP_RELATIONS, ProjectGraph
from umbra_engine.projection.model import APPLICATION, MapView
from umbra_engine.projection.search import MAX_HITS, SearchHit, search
from umbra_engine.projection.view import UnknownElementError, map_view
from umbra_engine.registry import Project
from umbra_engine.store_schema import INDEX_ID

GRAPH_CACHE_SIZE = 4


def add_map_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
) -> Callable[[str], ProjectGraph]:
    """Adds the map routes; returns the cached graph of a Project, for other routes to share."""
    graphs: dict[tuple[str, str], ProjectGraph] = {}
    lock = threading.Lock()

    def graph_of(project_id: str) -> ProjectGraph:
        """Built once per index run, so every request sees one consistent map."""
        project = known_project(project_id)
        with indexed_store(project_id) as store, lock:
            cache_key = (project_id, store.meta().get(INDEX_ID, ""))
            if cache_key not in graphs:
                if len(graphs) >= GRAPH_CACHE_SIZE:
                    graphs.pop(next(iter(graphs)))
                claims = store.claims_with_relations(MAP_RELATIONS)
                graphs[cache_key] = ProjectGraph(project.name, store.files(), claims)
            return graphs[cache_key]

    @app.get("/v1/projects/{project_id}/map", dependencies=authorized)
    def project_map(project_id: str, node: str = APPLICATION, expand: bool = False) -> MapView:
        try:
            return map_view(graph_of(project_id), node, expand)
        except UnknownElementError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown element: {node}") from error

    @app.get("/v1/projects/{project_id}/search", dependencies=authorized)
    def search_map(
        project_id: str, q: str, limit: Annotated[int, Query(ge=1, le=50)] = MAX_HITS
    ) -> list[SearchHit]:
        """Elements whose name matches `q`, with the view to open for each."""
        return search(graph_of(project_id), q, limit)

    @app.get("/v1/projects/{project_id}/claims/{key}", dependencies=authorized)
    def claim(project_id: str, key: str) -> StoredClaim:
        """What a map element or link stands on: its keys are stable across index runs."""
        known_project(project_id)
        with indexed_store(project_id) as store:
            found = store.claims_by_key([key])
        if not found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown claim: {key}")
        return found[0]

    @app.get("/v1/projects/{project_id}/evidence", dependencies=authorized)
    def evidence(
        project_id: str,
        file: str,
        start: Annotated[int, Query(ge=1)],
        end: Annotated[int, Query(ge=1)],
    ) -> EvidenceExcerpt:
        project = known_project(project_id)
        with indexed_store(project_id) as store:
            entry = store.file(file)
        if entry is None or entry.state != "readable" or end < start:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no readable evidence at this location")
        try:
            return excerpt(SecretGuard(project.root), entry, start, end)
        except EvidenceUnavailableError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error

    return graph_of

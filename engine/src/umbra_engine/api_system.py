"""The project map, Level 0 (ADR-0007): built from hard signals of the last index run, no LLM."""

import threading
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, params, status

from umbra_engine.analyzers.signals import SignalsAnalyzer
from umbra_engine.claims import DEFINES
from umbra_engine.indexer import ANALYZERS, GIT_BRANCH, GIT_DATE
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.system import system_map
from umbra_engine.projection.system_facts import SYSTEM_RELATIONS, facts_of
from umbra_engine.projection.system_layout import place
from umbra_engine.projection.system_model import SystemMap
from umbra_engine.registry import Project
from umbra_engine.store_schema import INDEX_ID, LIST_SEPARATOR

LEVEL_0 = "L0"
INDEXING = "indexing: Umbra is reading this project"
CACHE_SIZE = 4


def _signals_outdated(store: ProjectStore) -> bool:
    """The map reads the hard signals: an index made by another version of their Analyzer is read again."""
    return SignalsAnalyzer.producer not in store.meta().get(ANALYZERS, "").split(LIST_SEPARATOR)


def add_system_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    ensure_indexed: Callable[..., bool],
) -> None:
    maps: dict[tuple[str, str], SystemMap] = {}
    lock = threading.Lock()

    @app.get("/v1/projects/{project_id}/system", dependencies=authorized)
    def project_system(project_id: str, relire: bool = False) -> SystemMap:
        """The boxes, arrows, outputs and tools around of the Project, each with its proof (file:lines).
        Cells are stored the first time a box is placed: the map does not move on reload or re-index.
        A Project never read is read first (409 meanwhile); a failed read says so (500), `relire` retries."""
        project = known_project(project_id)
        if not ensure_indexed(project_id, retry=relire, outdated=_signals_outdated):
            raise HTTPException(status.HTTP_409_CONFLICT, INDEXING)
        with indexed_store(project_id) as store, lock:
            meta = store.meta()
            key = (project_id, meta.get(INDEX_ID, ""))
            if key not in maps:
                if len(maps) >= CACHE_SIZE:
                    maps.pop(next(iter(maps)))
                files = [f.path for f in store.files() if f.state == "readable"]
                claims = store.claims_with_relations(SYSTEM_RELATIONS)
                facts = facts_of(project.name, files, claims, store.claims_of_kind(DEFINES, "class"))
                maps[key] = system_map(facts, meta.get(GIT_BRANCH, ""), meta.get(GIT_DATE, ""))
            found = maps[key]
            cells = place(found.boxes, found.links, store.layout(LEVEL_0))
            store.save_layout(LEVEL_0, cells)
            for box in found.boxes:
                box.col, box.row = cells[box.id]
            found.boxes.sort(key=lambda b: (b.col, b.row))  # reading order: left to right, top to bottom
            return found

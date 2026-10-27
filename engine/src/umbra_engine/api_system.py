"""The project map, Level 0 (ADR-0007): built from hard signals of the last index run, no LLM."""

import threading
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, params, status

from umbra_engine.analyzers.signals import SignalsAnalyzer
from umbra_engine.claims import DEFINES
from umbra_engine.indexer import ANALYZERS, GIT_BRANCH, GIT_DATE
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.inside import has_inside, inside_map
from umbra_engine.projection.inside_model import InsideMap
from umbra_engine.projection.system import system_map
from umbra_engine.projection.system_facts import SYSTEM_RELATIONS, Facts, facts_of
from umbra_engine.projection.system_layout import place
from umbra_engine.projection.system_model import SystemMap
from umbra_engine.projection.system_units import Unit, find_units
from umbra_engine.registry import Project
from umbra_engine.store_schema import INDEX_ID, LIST_SEPARATOR

LEVEL_0 = "L0"
LEVEL_1 = "L1:"  # + the box: each inside keeps its own cells
INDEXING = "indexing: Umbra is reading this project"
CACHE_SIZE = 4
Owners = dict[str, str]  # repo file -> the box that holds it
SystemOf = Callable[..., tuple[SystemMap, Owners]]


def _signals_outdated(store: ProjectStore) -> bool:
    """The map reads the hard signals: an index made by another version of their Analyzer is read again."""
    return SignalsAnalyzer.producer not in store.meta().get(ANALYZERS, "").split(LIST_SEPARATOR)


def add_system_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    ensure_indexed: Callable[..., bool],
) -> SystemOf:
    maps: dict[tuple[str, str], tuple[SystemMap, Owners, Facts, list[Unit]]] = {}
    lock = threading.Lock()

    def system_of(project_id: str, retry: bool = False) -> tuple[SystemMap, Owners]:
        """The placed map, and which box holds each indexed file (for `show`, #104)."""
        found, owners, _, _ = read(project_id, retry)
        return found, owners

    def read(project_id: str, retry: bool = False) -> tuple[SystemMap, Owners, Facts, list[Unit]]:
        project = known_project(project_id)
        if not ensure_indexed(project_id, retry=retry, outdated=_signals_outdated):
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
                facts.functions = store.claims_of_kind(DEFINES, "function")
                found = system_map(facts, meta.get(GIT_BRANCH, ""), meta.get(GIT_DATE, ""))
                units = find_units(facts)
                shown = {b.id for b in found.boxes}
                owners = {f: u.id for u in units if u.id in shown for f in u.files}
                for box in found.boxes:  # « voir dedans » only where Level 1 has ≥ 2 parts to show
                    unit = next((u for u in units if u.id == box.id), None)
                    box.opens = box.opens and unit is not None and has_inside(facts, unit, box.folder)
                maps[key] = (found, owners, facts, units)
            found, owners, facts, units = maps[key]
            cells = place(found.boxes, found.links, store.layout(LEVEL_0))
            store.save_layout(LEVEL_0, cells)
            for box in found.boxes:
                box.col, box.row = cells[box.id]
            found.boxes.sort(key=lambda b: (b.col, b.row))  # reading order: left to right, top to bottom
            return found, owners, facts, units

    @app.get("/v1/projects/{project_id}/system", dependencies=authorized)
    def project_system(project_id: str, relire: bool = False) -> SystemMap:
        """The boxes, arrows, outputs and tools around of the Project, each with its proof (file:lines).
        Cells are stored the first time a box is placed: the map does not move on reload or re-index.
        A Project never read is read first (409 meanwhile); a failed read says so (500), `relire` retries."""
        return system_of(project_id, retry=relire)[0]

    @app.get("/v1/projects/{project_id}/system/inside", dependencies=authorized)
    def project_inside(project_id: str, box: str) -> InsideMap:
        """Level 1: the parts inside one box of the map, its neighbours as stubs, each with its proof.
        404 when the box has no inside (fewer than 2 parts). Cells are stored as Level 0's."""
        found, _, facts, units = read(project_id)
        with indexed_store(project_id) as store, lock:
            level = LEVEL_1 + box
            inside = inside_map(facts, units, found, box, store.layout(level))
            if inside is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"no inside for box {box!r}")
            store.save_layout(level, {p.id: (p.col, p.row) for p in inside.parts if p.kind != "stub"})
        return inside

    return system_of

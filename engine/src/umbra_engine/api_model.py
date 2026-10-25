"""The Project model routes: what Claude Code understood of the whole Project (ADR-0005).

The first request starts a study session; once the code changes, the model is out of date and the
next request (or live mode) starts an update session that re-reads only the changed files.
A model written by an older version of the method is kept and served as it is ("methode"): nothing
studies it again until the user asks, since a full study spends their Claude subscription (#78).
"""

import json
from collections.abc import Callable
from typing import Literal

from fastapi import FastAPI, params
from pydantic import BaseModel

from umbra_engine.analysis.runner import (
    MODEL_KEY,
    MODEL_PRODUCER,
    Study,
    changed_files,
    file_digests,
    project_digest,
    run_session,
)
from umbra_engine.claims import IMPORTS
from umbra_engine.explain.worker import STUDY, Explainer, Job
from umbra_engine.guard import SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.graph import ProjectGraph
from umbra_engine.registry import Project

ModelState = Literal["ready", "stale", "methode", "missing", "queued", "working", "error", "indexing"]


class ProjectModelState(BaseModel):
    state: ModelState
    model: dict | None = None  # the last model written, even when out of date
    created_at: str | None = None
    changed: list[str] = []  # files changed since the model was written
    message: str | None = None
    producer: str | None = None  # the method version that wrote the model
    methode_ancienne: bool = False  # written by an older method: a full study waits for « Relancer »


class StudyRequest(BaseModel):
    relancer: bool = False  # the user clicked « Relancer l'étude »: the only way to restudy an old model


def add_model_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    graph_of: Callable[[str], ProjectGraph],
    explainer: Explainer,
    study: Study,
    ensure_indexed: Callable[[str], bool],
) -> Callable[[str], ModelState]:
    """Adds the routes; returns `refresh_model(project_id)`: study or update when needed."""

    def current(project_id: str) -> tuple[ProjectModelState, dict | None, dict[str, str]]:
        with indexed_store(project_id) as store:
            row = store.card(MODEL_KEY)
            digests = file_digests(store.files())
        record = json.loads(row[1]) if row else None
        state = ProjectModelState(state="missing")
        if row is not None and record is not None:
            changed = changed_files(record["digests"], digests)
            outdated = row[2] != MODEL_PRODUCER
            state = ProjectModelState(
                state="methode" if outdated else "stale" if changed else "ready",
                model=record["model"],
                created_at=row[3],
                changed=changed[:50],
                producer=row[2],
                methode_ancienne=outdated,
            )
        working = explainer.state(project_id, MODEL_KEY)
        if working in ("queued", "working"):
            state = state.model_copy(update={"state": working})
        elif working is not None:
            state = state.model_copy(update={"state": "error", "message": working})
        return state, record, digests

    def refresh_model(project_id: str, relaunch: bool = False) -> ModelState:
        """Study or update when needed. A model by an older method is studied again only on `relaunch`:
        neither live changes, nor a retry after an error, nor an old page asking by itself start one."""
        state, record, digests = current(project_id)
        if state.methode_ancienne and not relaunch:
            return state.state
        if state.state not in ("missing", "stale", "error", "methode"):
            return state.state
        project = known_project(project_id)
        graph = graph_of(project_id)
        with indexed_store(project_id) as store:
            imports = store.claims_with_relations((IMPORTS,))
        # A model written by another version of the method is studied again from scratch.
        previous = record if record is not None and record.get("producer") == MODEL_PRODUCER else None
        explainer.request(
            Job(
                project_id,
                MODEL_KEY,
                project_digest(digests),
                MODEL_PRODUCER,
                lambda: indexed_store(project_id),
                lambda: run_session(SecretGuard(project.root), graph, imports, digests, study, previous),
                STUDY,
            )
        )
        return current(project_id)[0].state

    @app.get("/v1/projects/{project_id}/model", dependencies=authorized)
    def get_model(project_id: str) -> ProjectModelState:
        # Not read yet (just added, or never indexed): read it now and say so; never « index it again » (#85).
        if not ensure_indexed(project_id):
            return ProjectModelState(state="indexing")
        return current(project_id)[0]

    @app.post("/v1/projects/{project_id}/model", dependencies=authorized)
    def request_model(project_id: str, body: StudyRequest | None = None) -> ProjectModelState:
        """Study the Project when it has no model, update it when the code changed since, or study it
        again with the current method when the user asks (`relancer`)."""
        if not ensure_indexed(project_id):
            return ProjectModelState(state="indexing")
        refresh_model(project_id, relaunch=body is not None and body.relancer)
        return current(project_id)[0]

    return refresh_model

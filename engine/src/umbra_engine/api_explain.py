"""Explanation routes: the card of a map element, written in the background by the user's Claude Code."""

import json
from collections.abc import Callable
from typing import Literal

from fastapi import FastAPI, HTTPException, params, status
from pydantic import BaseModel

from umbra_engine.explain.cards import CARD_PRODUCER
from umbra_engine.explain.material import Material, material
from umbra_engine.explain.worker import Explainer, Job
from umbra_engine.guard import SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.graph import ProjectGraph
from umbra_engine.projection.model import APPLICATION
from umbra_engine.projection.view import UnknownElementError
from umbra_engine.registry import Project

CardState = Literal["ready", "stale", "missing", "queued", "working", "error"]


class Explanation(BaseModel):
    state: CardState
    card: dict | None = None  # the last card written, even when out of date
    producer: str | None = None
    created_at: str | None = None
    message: str | None = None


def add_explain_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    graph_of: Callable[[str], ProjectGraph],
    explainer: Explainer,
) -> None:
    def material_of(project_id: str, node: str) -> Material:
        project = known_project(project_id)
        try:
            return material(graph_of(project_id), SecretGuard(project.root), node)
        except UnknownElementError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown element: {node}") from error

    def explanation(project_id: str, node: str, found: Material) -> Explanation:
        with indexed_store(project_id) as store:
            row = store.card(node)
        working = explainer.state(project_id, node)
        card = None if row is None else Explanation(
            state="ready" if (row[0], row[2]) == (found.digest, CARD_PRODUCER) else "stale",
            card=json.loads(row[1]),
            producer=row[2],
            created_at=row[3],
        )  # fmt: skip
        if working in ("queued", "working"):
            return (card or Explanation(state="missing")).model_copy(update={"state": working})
        if working is not None:
            return (card or Explanation(state="error")).model_copy(
                update={"state": "error", "message": working}
            )
        return card or Explanation(state="missing")

    @app.get("/v1/projects/{project_id}/explain", dependencies=authorized)
    def get_explanation(project_id: str, node: str = APPLICATION) -> Explanation:
        return explanation(project_id, node, material_of(project_id, node))

    @app.post("/v1/projects/{project_id}/explain", dependencies=authorized)
    def request_explanation(project_id: str, node: str = APPLICATION) -> Explanation:
        """Write (or rewrite) the card when there is none, or when the code changed since."""
        found = material_of(project_id, node)
        current = explanation(project_id, node, found)
        if current.state in ("missing", "stale", "error"):
            project = known_project(project_id)
            explainer.request(Job(project_id, node, found, lambda: indexed_store(project.id)))
            current = explanation(project_id, node, found)
        return current

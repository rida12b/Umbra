"""Explanation routes: the card of a map element, written in the background by the user's Claude Code."""

import json
from collections.abc import Callable
from typing import Literal

from fastapi import FastAPI, HTTPException, params, status
from pydantic import BaseModel

from umbra_engine.claims import IMPORTS
from umbra_engine.explain.architecture import (
    ARCHITECTURE,
    architecture_material,
    parse_architecture,
    prompt_for_architecture,
)
from umbra_engine.explain.cards import CARD_PRODUCER, parse_card, prompt_for
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
    level: str | None = None  # application, group, code, doc, test or architecture: how to read the card


def add_explain_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    graph_of: Callable[[str], ProjectGraph],
    explainer: Explainer,
) -> Callable[[str], int]:
    """Adds the routes; returns `refresh_cards(project_id)`, which queues every out-of-date card."""

    def material_of(project_id: str, node: str) -> Material:
        project = known_project(project_id)
        guard = SecretGuard(project.root)
        if node == ARCHITECTURE:
            with indexed_store(project_id) as store:
                imports = store.claims_with_relations((IMPORTS,))
            return architecture_material(graph_of(project_id), guard, imports)
        try:
            return material(graph_of(project_id), guard, node)
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
            return (card or Explanation(state="missing")).model_copy(
                update={"state": working, "level": found.level}
            )
        if working is not None:
            return (card or Explanation(state="error")).model_copy(
                update={"state": "error", "message": working, "level": found.level}
            )
        return (card or Explanation(state="missing")).model_copy(update={"level": found.level})

    @app.get("/v1/projects/{project_id}/explain", dependencies=authorized)
    def get_explanation(project_id: str, node: str = APPLICATION) -> Explanation:
        return explanation(project_id, node, material_of(project_id, node))

    @app.post("/v1/projects/{project_id}/explain", dependencies=authorized)
    def request_explanation(project_id: str, node: str = APPLICATION) -> Explanation:
        """Write (or rewrite) the card when there is none, or when the code changed since."""
        found = material_of(project_id, node)
        current = explanation(project_id, node, found)
        if current.state in ("missing", "stale", "error"):
            explainer.request(job(project_id, node, found))
            current = explanation(project_id, node, found)
        return current

    def job(project_id: str, node: str, found: Material) -> Job:
        graph = graph_of(project_id)
        prompt, parse = (
            (prompt_for_architecture(found), lambda answer: parse_architecture(answer, graph))
            if node == ARCHITECTURE
            else (prompt_for(found), lambda answer: parse_card(answer, found))
        )
        return Job(project_id, node, found, lambda: indexed_store(project_id), prompt, parse)

    def refresh_cards(project_id: str) -> int:
        """After the code changed: rewrite the cards already written whose material changed since."""
        with indexed_store(project_id) as store:
            keys = store.card_keys()
        queued = 0
        for node in keys:
            try:
                found = material_of(project_id, node)
            except HTTPException:
                continue  # the element is gone from the map
            if explanation(project_id, node, found).state == "stale":
                explainer.request(job(project_id, node, found))
                queued += 1
        return queued

    return refresh_cards

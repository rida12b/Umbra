"""« Ce qu'on peut faire » (ADR-0007, #107): the list of a Project's actions, and the path of one of them
traced in the code and lit on the open map, like a `show` from Claude Code. No model runs (#114)."""

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, params, status
from pydantic import BaseModel

from umbra_engine.api_system import MapReader, released_text
from umbra_engine.claims import DEFINES
from umbra_engine.guard import SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.projection.action_chain import chain
from umbra_engine.projection.action_client import client_call
from umbra_engine.projection.action_code import Code
from umbra_engine.projection.action_path import action_path, path_box
from umbra_engine.projection.actions import ROUTES, ActionList, list_actions
from umbra_engine.projection.highlight import Highlight
from umbra_engine.registry import Project


class ActionIn(BaseModel):
    action: str  # an id from the list: « backend/app/api/routes/items.py:62 »


def add_action_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    indexed_store: Callable[[str], ProjectStore],
    reader: MapReader,
    publish: Callable[[str, Highlight], Highlight],
) -> None:
    @app.get("/v1/projects/{project_id}/system/actions", dependencies=authorized)
    def actions(project_id: str) -> ActionList:
        """The addresses the server answers and the commands the CLI offers, grouped by file, in the code's
        own words (French only for a plain shape: « Créer un item »)."""
        _, _, facts, units = reader.read(project_id)
        return list_actions(facts, units, released_text(SecretGuard(known_project(project_id).root)))

    @app.post("/v1/projects/{project_id}/show/action", dependencies=authorized)
    def show_action(project_id: str, body: ActionIn) -> Highlight:
        """Lights the static path of one action on every open tab: who sends it, the function that answers,
        what it calls (≤ 6 numbered parts), what it writes. 404 for an action not in the list."""
        shown, owners, facts, units = reader.read(project_id)
        text_of = released_text(SecretGuard(known_project(project_id).root))
        found = list_actions(facts, units, text_of).find(body.action)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown action: {body.action!r}")
        with indexed_store(project_id) as store:
            methods = store.claims_of_kind(DEFINES, "method")
        hits = chain(Code(text_of, facts.module_links, methods), facts, found.file, found.line)
        client = None
        if found.kind == ROUTES:
            web = sorted(f for u in units if u.role == "web" for f in u.files)
            client = client_call(web, text_of, found.verb, found.address)
        opens = {b.id for b in shown.boxes if b.opens}
        box = path_box(hits, owners, opens)
        read = reader.inside(project_id, box) if box else None
        return publish(project_id, action_path(found, hits, client, shown, owners, read))

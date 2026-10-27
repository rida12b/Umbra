"""The terminal draws on the map (ADR-0007, #104): Claude Code calls the MCP tool `show`, which posts here;
the lit path is checked against the map, kept as the Project's current highlight, and pushed to the open
tabs over the live stream (`/events`). No LLM runs here: Claude Code is the only model."""

import threading
from collections.abc import Callable
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, params
from pydantic import BaseModel, Field

from umbra_engine.api_system import MapReader
from umbra_engine.events import EventHub
from umbra_engine.projection.highlight import Highlight, NotOnMapError, StepRequest, resolve
from umbra_engine.projection.lit_inside import names_a_part, resolve_inside
from umbra_engine.registry import Project

SHOW = "show"
CLEARED = "cleared"
NOT_ON_MAP = 422  # named differently across Starlette versions


class StepIn(BaseModel):
    part: str = Field(
        description="a box of the map (id, title or folder), a part of a box (« Serveur/Contrôle d'accès »), "
        "or a repo path, file or folder"
    )
    note: str = Field("", description="2-4 words shown beside it, e.g. « ajouter le champ »")
    why: str = Field("", description="one sentence shown on hover: why this place")


class ShowIn(BaseModel):
    caption: str
    parts: list[str] = Field(default_factory=list)
    path: list[StepIn | str] = Field(default_factory=list)


def add_show_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    reader: MapReader,
    events: EventHub,
) -> Callable[[str, Highlight], Highlight]:
    current: dict[str, Highlight] = {}
    guard = threading.Lock()
    serials = iter(range(1, 1 << 62))

    @app.post("/v1/projects/{project_id}/show", dependencies=authorized)
    def show(project_id: str, body: ShowIn) -> Highlight:
        """Light ≤ 6 numbered parts on the open map, dim the rest, one caption. 422 names what is valid."""
        known_project(project_id)
        shown, owners = reader.system_of(project_id)
        steps = [
            StepRequest(s) if isinstance(s, str) else StepRequest(s.part, s.note, s.why) for s in body.path
        ]
        named = [s.part for s in steps] + body.parts
        inside = next((b for n in named if (b := names_a_part(shown, n))), None)
        try:
            if inside is not None:  # a part of a box is named: the path is drawn inside that box (Level 1)
                read = reader.inside(project_id, inside)
                if read is None:
                    raise NotOnMapError(f"box {inside!r} has no inside to draw on")
                lit = resolve_inside(read, body.caption, body.parts, steps)
            else:
                lit = resolve(shown, owners, body.caption, body.parts, steps)
        except NotOnMapError as error:
            raise HTTPException(NOT_ON_MAP, str(error)) from error
        return publish(project_id, lit)

    def publish(project_id: str, lit: Highlight) -> Highlight:
        """Kept as the Project's current highlight and pushed to every open tab (a `show`, or an action)."""
        with guard:
            lit.serial = next(serials)
            current[project_id] = lit
        events.publish(project_id, {"type": SHOW, "highlight": asdict(lit)})
        return lit

    @app.get("/v1/projects/{project_id}/show", dependencies=authorized)
    def shown_now(project_id: str) -> Highlight | None:
        """What is lit now, for a tab opened (or reloaded) after the `show` call; null when nothing."""
        known_project(project_id)
        with guard:
            return current.get(project_id)

    @app.delete("/v1/projects/{project_id}/show", dependencies=authorized)
    def clear(project_id: str) -> dict[str, bool]:
        """« effacer »: every open tab goes back to the plain map."""
        known_project(project_id)
        with guard:
            had = current.pop(project_id, None) is not None
        events.publish(project_id, {"type": CLEARED})
        return {"cleared": had}

    return publish

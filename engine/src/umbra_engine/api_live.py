"""The live stream of a Project: pages read it to refresh themselves when the code changes."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request, params
from fastapi.responses import StreamingResponse

from umbra_engine.events import EventHub
from umbra_engine.journal import Turn, stored_events, turns
from umbra_engine.project_store import ProjectStore
from umbra_engine.registry import Project

POLL_S = 0.5
HEARTBEAT_S = 15.0


MAX_TURNS = 100
MAX_EVENTS = 5000  # enough for the last MAX_TURNS turns; the page never reads the whole history


def add_live_routes(
    app: FastAPI,
    authorized: list[params.Depends],
    known_project: Callable[[str], Project],
    events: EventHub,
    open_store: Callable[[Project], ProjectStore],
) -> None:
    @app.get("/v1/projects/{project_id}/activity", dependencies=authorized)
    def activity(project_id: str) -> list[Turn]:
        """What Claude Code did in the Project, turn by turn (prompt, edited files, final message),
        newest first."""
        project = known_project(project_id)
        with open_store(project) as store:
            return turns(stored_events(store, MAX_EVENTS), project)[:MAX_TURNS]

    @app.get("/v1/projects/{project_id}/events", dependencies=authorized)
    async def project_events(
        project_id: str, request: Request, since: int | None = None
    ) -> StreamingResponse:
        """Server-sent events: `indexed` (files changed), `studying`, `rewriting`, `card` (written),
        `failed`. A page that reconnects passes the last id it saw (`since`) and gets what it missed."""
        known_project(project_id)

        async def stream() -> AsyncIterator[str]:
            last_seen, quiet = (events.latest() if since is None else since), 0.0
            yield ": connected\n\n"
            while not await request.is_disconnected():
                fresh = events.since(project_id, last_seen)
                for number, event in fresh:
                    last_seen = number
                    yield f"id: {number}\ndata: {json.dumps(event)}\n\n"
                quiet = 0.0 if fresh else quiet + POLL_S
                if quiet >= HEARTBEAT_S:
                    quiet = 0.0
                    yield ": still here\n\n"
                await asyncio.sleep(POLL_S)

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"}
        )

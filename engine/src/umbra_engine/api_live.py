"""The live stream of a Project: pages read it to refresh themselves when the code changes."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI, Request, params
from fastapi.responses import StreamingResponse

from umbra_engine.events import EventHub
from umbra_engine.registry import Project

POLL_S = 0.5
HEARTBEAT_S = 15.0


def add_live_routes(
    app: FastAPI, authorized: list[params.Depends], known_project: Callable[[str], Project], events: EventHub
) -> None:
    @app.get("/v1/projects/{project_id}/events", dependencies=authorized)
    async def project_events(project_id: str, request: Request) -> StreamingResponse:
        """Server-sent events, from now on: `indexed` (files changed), `rewriting`, `card` (rewritten)."""
        known_project(project_id)

        async def stream() -> AsyncIterator[str]:
            last_seen, quiet = events.latest(), 0.0
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

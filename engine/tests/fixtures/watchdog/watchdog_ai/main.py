"""Watchdog application entrypoint.

Wires the FastAPI app with the tenant auth middleware and the API routes.

Start the server with:
    uvicorn watchdog_ai.main:app --reload
"""

from fastapi import FastAPI

from watchdog_ai.api.middleware.tenant_auth import TenantAuthMiddleware
from watchdog_ai.api.routes.events import router as events_router

app = FastAPI(
    title="Watchdog",
    description="AI Agent Production Watchdog - multi-agent observability platform.",
    version="0.1.0",
)

app.add_middleware(TenantAuthMiddleware)
app.include_router(events_router)

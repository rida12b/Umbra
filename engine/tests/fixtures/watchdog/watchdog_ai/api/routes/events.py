"""POST /api/v1/events route for telemetry ingestion.

Reads the tenant_id from request.state (injected by TenantAuthMiddleware),
validates the body against EventIn, persists via the storage layer,
and returns the stored EventOut.
"""

from fastapi import APIRouter, Request, status

from watchdog_ai.ingestion.schemas import EventIn, EventOut
from watchdog_ai.storage.events import append_event

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.post(
    "/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(event: EventIn, request: Request) -> EventOut:
    tenant_id: str = request.state.tenant_id
    return append_event(event, tenant_id=tenant_id)

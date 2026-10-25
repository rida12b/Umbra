"""In-memory storage for telemetry events.
TODO LEARN Sem 6: replace with PostgreSQL + SQLAlchemy async.
"""

from datetime import UTC, datetime

from watchdog_ai.ingestion.schemas import EventIn, EventOut

_events: list[EventOut] = []


def append_event(event: EventIn, tenant_id: str) -> EventOut:
    """Persist a telemetry event for a given tenant. Returns the stored EventOut."""
    event_out = EventOut(
        **event.model_dump(),
        tenant_id=tenant_id,
        received_at=datetime.now(UTC),
    )
    _events.append(event_out)
    return event_out


def list_events(tenant_id: str) -> list[EventOut]:
    """Return all events stored for the given tenant."""
    return [e for e in _events if e.tenant_id == tenant_id]

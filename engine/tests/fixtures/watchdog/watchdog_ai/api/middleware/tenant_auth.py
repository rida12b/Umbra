"""Tenant authentication middleware.

Reads the X-Tenant-ID header on every incoming request, injects it into
request.state.tenant_id, and rejects requests without the header.

Defense-in-depth layer 1/3:
  1. Middleware (this file)         - AuthN: who are you?
  2. Repository filter (tenant_id)  - AuthZ logic: scope reads/writes
  3. PostgreSQL RLS                 - AuthZ DB-level (TODO LEARN Sem 6)

Note on rejection: we return a JSONResponse directly instead of `raise
HTTPException(...)`. Reason: HTTPException raised from inside a
BaseHTTPMiddleware is NOT caught by Starlette's ExceptionMiddleware
(which only catches exceptions from inside its inner wrap = routes and
dependencies). Raising here would surface as a 500 Internal Server Error.

TODO LEARN Sem 7: replace the raw header with a JWT-verified tenant claim.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """Gate every incoming HTTP request on the X-Tenant-ID header."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-Tenant-ID header"},
            )
        request.state.tenant_id = tenant_id
        return await call_next(request)

"""Local HTTP API (`/v1`). Every client — UI, MCP server, future dashboard — goes through it."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from umbra_engine import __version__
from umbra_engine.api_map import add_map_routes
from umbra_engine.claims import Relation, Status, StoredClaim
from umbra_engine.coverage import CoverageReport, coverage_report
from umbra_engine.coverage import State as CoverageState
from umbra_engine.indexer import IndexSummary, index_project
from umbra_engine.project_store import STALE_INDEX, ProjectStore
from umbra_engine.registry import Project, ProjectIdCollisionError, ProjectPathError, Registry
from umbra_engine.settings import LOOPBACK_HOSTS, Settings, load_or_create_token
from umbra_engine.ui_session import SESSION_HEADER, UiSessions
from umbra_engine.web import add_web_routes

MAX_PAGE = 1000


class ProjectIn(BaseModel):
    path: str


class ProjectOut(BaseModel):
    id: str
    name: str
    root: str
    created_at: str

    @classmethod
    def of(cls, project: Project) -> "ProjectOut":
        return cls(id=project.id, name=project.name, root=str(project.root), created_at=project.created_at)


def create_app(settings: Settings) -> FastAPI:
    registry = Registry(settings)
    token = load_or_create_token(settings).encode()
    sessions = UiSessions()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        registry.close()

    app = FastAPI(title="Umbra engine", version=__version__, lifespan=lifespan)
    # A web page can make the browser resolve any host name to 127.0.0.1 (DNS rebinding);
    # requests that do not address the loopback by name are refused before any route runs.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(LOOPBACK_HOSTS))
    app.state.ui_sessions = sessions

    def require_token(
        authorization: Annotated[str | None, Header()] = None,
        session: Annotated[str | None, Header(alias=SESSION_HEADER)] = None,
    ) -> None:
        """The token (CLI, MCP, dashboard) or a browser session opened with a one-time login code."""
        if session and sessions.is_valid(session):
            return
        presented = ""
        if authorization and authorization.lower().startswith("bearer "):
            presented = authorization[7:].strip()
        if not presented or not secrets.compare_digest(presented.encode(), token):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or invalid local token")

    authorized = [Depends(require_token)]

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/projects", dependencies=authorized)
    def add_project(body: ProjectIn) -> ProjectOut:
        if not Path(body.path).expanduser().is_absolute():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "path must be absolute")
        try:
            project, _ = registry.add(body.path)
        except ProjectPathError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
        except ProjectIdCollisionError as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
        return ProjectOut.of(project)

    @app.get("/v1/projects", dependencies=authorized)
    def list_projects() -> list[ProjectOut]:
        return [ProjectOut.of(project) for project in registry.list()]

    def known_project(project_id: str) -> Project:
        project = registry.get(project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown project: {project_id}")
        return project

    def indexed_store(project_id: str) -> ProjectStore:
        store = registry.open_store(known_project(project_id))
        if not store.index_is_current():
            store.close()
            raise HTTPException(status.HTTP_409_CONFLICT, STALE_INDEX)
        return store

    @app.get("/v1/projects/{project_id}", dependencies=authorized)
    def get_project(project_id: str) -> ProjectOut:
        return ProjectOut.of(known_project(project_id))

    @app.get("/v1/projects/{project_id}/claims", dependencies=authorized)
    def claims(
        project_id: str,
        response: Response,
        file: str | None = None,
        subject: str | None = None,
        object: str | None = None,
        relation: Relation | None = None,
        status: Status | None = None,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 200,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[StoredClaim]:
        filters = {"file": file, "subject": subject, "object": object, "relation": relation, "status": status}
        with indexed_store(project_id) as store:
            response.headers["X-Total-Count"] = str(store.count_claims_matching(**filters))
            return store.claims(limit, offset, **filters)

    @app.get("/v1/projects/{project_id}/coverage", dependencies=authorized)
    def coverage(
        project_id: str,
        state: CoverageState | None = None,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = MAX_PAGE,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> CoverageReport:
        with indexed_store(project_id) as store:
            return coverage_report(store.files(), only=state, limit=limit, offset=offset)

    @app.post("/v1/projects/{project_id}/index", dependencies=authorized)
    def index(project_id: str) -> IndexSummary:
        project = known_project(project_id)
        with registry.open_store(project) as store:
            return index_project(project, store)

    add_map_routes(app, authorized, known_project, indexed_store)
    add_web_routes(app, authorized, sessions)  # last: the web app is mounted at `/`
    return app

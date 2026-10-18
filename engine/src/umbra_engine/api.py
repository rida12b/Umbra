"""Local HTTP API (`/v1`). Every client — UI, MCP server, future dashboard — goes through it."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from umbra_engine import __version__
from umbra_engine.registry import Project, ProjectPathError, Registry
from umbra_engine.settings import Settings, load_or_create_token


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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        registry.close()

    app = FastAPI(title="Umbra engine", version=__version__, lifespan=lifespan)

    def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
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
        return ProjectOut.of(project)

    @app.get("/v1/projects", dependencies=authorized)
    def list_projects() -> list[ProjectOut]:
        return [ProjectOut.of(project) for project in registry.list()]

    @app.get("/v1/projects/{project_id}", dependencies=authorized)
    def get_project(project_id: str) -> ProjectOut:
        project = registry.get(project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown project: {project_id}")
        return ProjectOut.of(project)

    return app

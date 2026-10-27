"""Local HTTP API (`/v1`). Every client — UI, MCP server, future dashboard — goes through it."""

import secrets
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from umbra_engine import __version__
from umbra_engine.analysis.runner import MODEL_KEY, Study
from umbra_engine.api_explain import add_explain_routes
from umbra_engine.api_live import add_live_routes
from umbra_engine.api_map import add_map_routes
from umbra_engine.api_model import add_model_routes
from umbra_engine.api_system import add_system_routes
from umbra_engine.claims import Relation, Status, StoredClaim
from umbra_engine.coverage import CoverageReport, coverage_report
from umbra_engine.coverage import State as CoverageState
from umbra_engine.events import EventHub
from umbra_engine.explain.worker import Explainer
from umbra_engine.gateways import claude
from umbra_engine.indexer import IndexSummary, index_project
from umbra_engine.journal import ingest
from umbra_engine.live import LiveProjects
from umbra_engine.project_store import STALE_INDEX, ProjectStore
from umbra_engine.registry import Project, ProjectIdCollisionError, ProjectPathError, Registry
from umbra_engine.settings import LOOPBACK_HOSTS, Settings, load_or_create_token
from umbra_engine.ui_session import SESSION_HEADER, UiSessions
from umbra_engine.web import add_web_routes

MAX_PAGE = 1000
MODEL_FOLLOW_UP_S = 60.0
JOURNAL_POLL_S = 0.5
READ_JOIN_S = 10.0  # at shutdown, how long to wait for a project being read
READ_RETRY_S = 30.0  # a read that failed is tried again by itself at most this often


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


def create_app(
    settings: Settings,
    ask: Callable[[str], str] = claude.ask,
    study: Study = claude.study,
    live: bool = False,
) -> FastAPI:
    """`ask` and `study` run the user's Claude Code (tests pass fakes). With `live`, every indexed
    Project is watched: a change re-indexes it and updates the model and cards it made out of date."""
    registry = Registry(settings)
    token = load_or_create_token(settings).encode()
    sessions = UiSessions()
    events = EventHub()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if live_projects is not None:
            for project in registry.list():
                with registry.open_store(project) as store:
                    current = store.index_is_current()
                if current:
                    live_projects.follow(project)
                else:  # never indexed (`umbra-engine add`), or by an older Umbra: read it, then follow it
                    start_indexing(project)
        if live_projects is not None:
            threading.Thread(target=pump_journal, name="umbra-journal", daemon=True).start()
        yield
        journal_stop.set()
        # Let a read in progress finish before the registry closes: one budget for all of them, not one each.
        deadline = time.monotonic() + READ_JOIN_S
        for reader in list(readers):
            reader.join(timeout=max(0.0, deadline - time.monotonic()))
        for timer in follow_ups:
            timer.cancel()
        if live_projects is not None:
            live_projects.stop_all()
        registry.close()

    journal_stop = threading.Event()

    def pump_journal() -> None:
        """Move what Claude Code's hooks reported into the Projects, and tell the pages."""
        while not journal_stop.wait(JOURNAL_POLL_S):
            try:
                for project_id, count in ingest(settings.home, registry.list(), registry.open_store).items():
                    events.publish(project_id, {"type": "activity", "count": count})
            except Exception:  # noqa: BLE001 — a bad spool file must not stop the journal
                continue

    index_locks: dict[str, threading.Lock] = {}
    index_guard = threading.Lock()
    indexing: set[str] = set()
    index_errors: dict[str, tuple[str, float]] = {}  # a failed read and when: a steady state, retried slowly
    readers: list[threading.Thread] = []  # background reads, waited for at shutdown

    def lock_of(project_id: str) -> threading.Lock:
        with index_guard:
            return index_locks.setdefault(project_id, threading.Lock())

    def index_now(project: Project) -> IndexSummary:
        with lock_of(project.id), registry.open_store(project) as store:
            return index_project(project, store)

    def reindex_and_follow(project: Project) -> None:
        try:
            try:
                index_now(project)
            except Exception as error:  # noqa: BLE001 — a background read must report, never vanish
                with index_guard:
                    index_errors[project.id] = (f"{type(error).__name__}: {error}", time.monotonic())
                return
            finally:
                with index_guard:
                    indexing.discard(project.id)
            if journal_stop.is_set():  # the engine stopped while it was reading: nothing to follow any more
                return
            # The page asks for its model again.
            events.publish(project.id, {"type": "indexed", "changed": [], "count": 0})
            if live_projects is not None:
                live_projects.follow(project)
        finally:  # only now: shutdown waits for this thread until its very last step
            with index_guard:
                readers[:] = [r for r in readers if r is not threading.current_thread()]

    def start_indexing(project: Project) -> None:
        """Read a Project in the background, one read at a time (#85); meanwhile its model is « indexing »."""
        with index_guard:
            if project.id in indexing:
                return
            indexing.add(project.id)
        name = f"umbra-index-{project.id}"
        reader = threading.Thread(target=reindex_and_follow, args=(project,), name=name, daemon=True)
        readers.append(reader)
        reader.start()

    def ensure_indexed(
        project_id: str, retry: bool = False, outdated: Callable[[ProjectStore], bool] | None = None
    ) -> bool:
        """True when the index is current; otherwise start reading the Project and say False. A failed read
        stays said (500) to every ask: the page asks on each live event. It is tried again by itself after
        READ_RETRY_S, or at once on `retry` (« Réessayer », adding the folder again). `outdated`: the
        caller's own reason to read again (its Analyzer changed since the last run)."""
        project = known_project(project_id)
        with index_guard:
            if project_id in indexing:
                return False
            error = index_errors.get(project_id)
            if error and (retry or time.monotonic() - error[1] >= READ_RETRY_S):
                del index_errors[project_id]
                error = None
            failed = error[0] if error else None
        if failed:
            detail = f"reading the project failed: {failed}"
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)
        with registry.open_store(project) as store:
            if store.index_is_current() and not (outdated and outdated(store)):
                return True
        start_indexing(project)
        return False

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
        if live_projects is not None:  # the running engine reads it at once, as at startup (#85)
            ensure_indexed(project.id, retry=True)  # adding the folder again is the user's own retry
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
        summary = index_now(project)
        with index_guard:
            index_errors.pop(project_id, None)  # an explicit read that works clears an old failure
        if live_projects is not None:
            live_projects.follow(project)
        return summary

    graph_of = add_map_routes(app, authorized, known_project, indexed_store)

    follow_ups: list[threading.Timer] = []  # cancelled when the engine stops

    def follow_up(project_id: str) -> None:
        try:
            refresh_model(project_id)
        except Exception:  # noqa: BLE001 — a late follow-up must never take the engine down
            return

    def saved(project_id: str, key: str) -> None:
        events.publish(project_id, {"type": "card", "key": key})
        if key == MODEL_KEY:  # changes that landed during the session: one follow-up, a bit later
            timer = threading.Timer(MODEL_FOLLOW_UP_S, follow_up, args=(project_id,))
            timer.daemon = True
            follow_ups.append(timer)
            timer.start()

    app.state.explainer = Explainer(
        on_saved=saved,
        on_failed=lambda project_id, key: events.publish(project_id, {"type": "failed", "key": key}),
    )
    refresh_cards = add_explain_routes(
        app, authorized, known_project, indexed_store, graph_of, app.state.explainer, ask
    )
    add_system_routes(app, authorized, known_project, indexed_store, ensure_indexed)
    refresh_model = add_model_routes(
        app, authorized, known_project, indexed_store, graph_of, app.state.explainer, study, ensure_indexed
    )
    add_live_routes(app, authorized, known_project, events, registry.open_store)
    live_projects = (
        LiveProjects(registry.open_store, events, refresh_cards, refresh_model, lock_of) if live else None
    )
    app.state.live = live_projects
    add_web_routes(app, authorized, sessions)  # last: the web app is mounted at `/`
    return app

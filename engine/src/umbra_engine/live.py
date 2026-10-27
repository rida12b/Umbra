"""Live mode: when a Project's files change, index it again and tell the pages what changed (SPEC S5).
Nothing here runs a model (ADR-0007)."""

import threading
from collections.abc import Callable

from umbra_engine.events import EventHub
from umbra_engine.gateways.watch import watch_project
from umbra_engine.indexer import index_project
from umbra_engine.project_store import ProjectStore
from umbra_engine.registry import Project

MAX_LISTED_CHANGES = 50


class LiveProjects:
    def __init__(
        self,
        open_store: Callable[[Project], ProjectStore],
        events: EventHub,
        lock_of: Callable[[str], threading.Lock],
    ) -> None:
        self._open_store = open_store
        self._events = events
        self._watched: dict[str, threading.Event] = {}
        self._lock_of = lock_of  # shared with the engine's own indexing: one read of a Project at a time
        self._guard = threading.Lock()

    def follow(self, project: Project) -> None:
        """Start watching a Project (once)."""
        with self._guard:
            if project.id in self._watched:
                return
            stop = self._watched[project.id] = threading.Event()
        watch_project(project.root, lambda: self.refresh(project), stop)

    def stop_all(self) -> None:
        with self._guard:
            for stop in self._watched.values():
                stop.set()

    def refresh(self, project: Project) -> list[str]:
        """Index again, then publish the changed files; one refresh at a time per Project."""
        with self._lock_of(project.id):
            with self._open_store(project) as store:
                before = {f.path: f.digest for f in store.files()}
                index_project(project, store)
                after = {f.path: f.digest for f in store.files()}
            changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
            if not changed:
                return []
            self._events.publish(
                project.id,
                {"type": "indexed", "changed": changed[:MAX_LISTED_CHANGES], "count": len(changed)},
            )
            return changed

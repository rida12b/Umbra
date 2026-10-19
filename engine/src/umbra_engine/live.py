"""Live mode: when a Project's files change, index it again, tell the pages what changed, and have
Claude Code rewrite only the cards whose code changed (SPEC S5)."""

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
        refresh_cards: Callable[..., int],
    ) -> None:
        self._open_store = open_store
        self._events = events
        self._refresh_cards = refresh_cards
        self._watched: dict[str, threading.Event] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def follow(self, project: Project) -> None:
        """Start watching a Project (once)."""
        with self._guard:
            if project.id in self._watched:
                return
            stop = self._watched[project.id] = threading.Event()
            self._locks[project.id] = threading.Lock()
        watch_project(project.root, lambda: self.refresh(project), stop)
        queued = self._refresh_cards(project.id, warm_up=True)  # first look: written once, in the background
        if queued:
            self._events.publish(project.id, {"type": "rewriting", "count": queued})

    def stop_all(self) -> None:
        with self._guard:
            for stop in self._watched.values():
                stop.set()

    def refresh(self, project: Project) -> list[str]:
        """Index again, then publish the changed files; one refresh at a time per Project."""
        with self._locks.setdefault(project.id, threading.Lock()):
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
            rewriting = self._refresh_cards(project.id)
            if rewriting:
                self._events.publish(project.id, {"type": "rewriting", "count": rewriting})
            return changed

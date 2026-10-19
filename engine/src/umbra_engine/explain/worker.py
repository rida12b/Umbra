"""One background worker runs Claude Code sessions, one at a time (ADR-0003), within a daily budget.

A card someone asked for goes before a long study; every session counts against the Project's
budget for the day, rewrites and failures included.
"""

import itertools
import queue
import threading
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from umbra_engine.analysis.model import ModelFormatError
from umbra_engine.explain.cards import CardFormatError
from umbra_engine.gateways.claude import ClaudeUnavailableError
from umbra_engine.project_store import ProjectStore

DAILY_CARD_BUDGET = 150  # sessions per Project per day: they share the user's own Claude limits
CARD, STUDY = 0, 1  # priorities: lower runs first


@dataclass(frozen=True)
class Job:
    """One thing to write with Claude Code (an element's card, or the Project model): `produce` runs
    the session and returns what to store; `digest` names what it was written from."""

    project_id: str
    key: str
    digest: str
    producer: str
    open_store: Callable[[], ProjectStore]
    produce: Callable[[], str]
    priority: int = field(default=CARD)


class Explainer:
    def __init__(
        self,
        daily_budget: int = DAILY_CARD_BUDGET,
        on_saved: Callable[[str, str], None] = lambda project_id, key: None,
        on_failed: Callable[[str, str], None] = lambda project_id, key: None,
    ) -> None:
        self._on_saved = on_saved
        self._on_failed = on_failed
        self._budget = daily_budget
        self._jobs: queue.PriorityQueue[tuple[int, int, Job]] = queue.PriorityQueue()
        self._order = itertools.count()
        self._sessions: Counter[tuple[str, str]] = Counter()  # (project, day) -> sessions started
        self._states: dict[tuple[str, str], str] = {}  # "queued", "working" or an error message
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def state(self, project_id: str, key: str) -> str | None:
        with self._lock:
            return self._states.get((project_id, key))

    def request(self, job: Job) -> str:
        """Queue a session unless one for the same thing is already on its way; returns the state."""
        with self._lock:
            current = self._states.get((job.project_id, job.key))
            if current in ("queued", "working"):
                return current
            with job.open_store() as store:
                written_today = store.cards_written_since(_today())
            if max(written_today, self._sessions[(job.project_id, _today())]) >= self._budget:
                message = f"daily budget reached ({self._budget} Claude sessions for this Project)"
                self._states[(job.project_id, job.key)] = message
                return message
            self._sessions[(job.project_id, _today())] += 1
            self._states[(job.project_id, job.key)] = "queued"
            self._jobs.put((job.priority, next(self._order), job))
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="umbra-explainer", daemon=True)
                self._thread.start()
            return "queued"

    def _run(self) -> None:
        while True:  # a daemon thread: it waits for free and ends with the engine
            _, _, job = self._jobs.get()
            self._set(job, "working")
            try:
                written = job.produce()
                with job.open_store() as store:
                    store.save_card(job.key, job.digest, written, job.producer, _now())
                self._set(job, None)
                self._on_saved(job.project_id, job.key)
            except (ClaudeUnavailableError, CardFormatError, ModelFormatError) as error:
                self._fail(job, f"explanation failed: {error}")
            except Exception as error:  # the worker must survive any single failure
                self._fail(job, f"explanation failed: {type(error).__name__}")

    def _fail(self, job: Job, message: str) -> None:
        self._set(job, message)
        self._on_failed(job.project_id, job.key)

    def _set(self, job: Job, state: str | None) -> None:
        with self._lock:
            if state is None:
                self._states.pop((job.project_id, job.key), None)
            else:
                self._states[(job.project_id, job.key)] = state


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(UTC).date().isoformat()

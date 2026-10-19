"""One background worker writes cards, one Claude call at a time (ADR-0003), within a daily budget."""

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from umbra_engine.analysis.model import ModelFormatError
from umbra_engine.explain.cards import CardFormatError
from umbra_engine.gateways.claude import ClaudeUnavailableError
from umbra_engine.project_store import ProjectStore

DAILY_CARD_BUDGET = 150  # per Project: background calls share the user's own Claude limits


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


class Explainer:
    def __init__(
        self,
        daily_budget: int = DAILY_CARD_BUDGET,
        on_saved: Callable[[str, str], None] = lambda project_id, key: None,
    ) -> None:
        self._on_saved = on_saved
        self._budget = daily_budget
        self._jobs: queue.Queue[Job] = queue.Queue()
        self._states: dict[tuple[str, str], str] = {}  # "queued", "working" or an error message
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def state(self, project_id: str, key: str) -> str | None:
        with self._lock:
            return self._states.get((project_id, key))

    def request(self, job: Job) -> str:
        """Queue a card unless one is already on its way; returns the state to show."""
        with self._lock:
            current = self._states.get((job.project_id, job.key))
            if current in ("queued", "working"):
                return current
            with job.open_store() as store:
                if store.cards_written_since(_today()) >= self._budget:
                    message = f"daily budget reached ({self._budget} cards for this Project)"
                    self._states[(job.project_id, job.key)] = message
                    return message
            self._states[(job.project_id, job.key)] = "queued"
            self._jobs.put(job)
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="umbra-explainer", daemon=True)
                self._thread.start()
            return "queued"

    def _run(self) -> None:
        while True:  # a daemon thread: it waits for free and ends with the engine
            job = self._jobs.get()
            self._set(job, "working")
            try:
                written = job.produce()
                with job.open_store() as store:
                    store.save_card(job.key, job.digest, written, job.producer, _now())
                self._set(job, None)
                self._on_saved(job.project_id, job.key)
            except (ClaudeUnavailableError, CardFormatError, ModelFormatError) as error:
                self._set(job, f"explanation failed: {error}")
            except Exception as error:  # the worker must survive any single failure
                self._set(job, f"explanation failed: {type(error).__name__}")

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

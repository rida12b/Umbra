"""One background worker writes cards, one Claude call at a time (ADR-0003), within a daily budget."""

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from umbra_engine.explain.cards import CARD_PRODUCER, CardFormatError, parse_card, prompt_for
from umbra_engine.explain.material import Material
from umbra_engine.gateways.claude import ClaudeUnavailableError
from umbra_engine.project_store import ProjectStore

DAILY_CARD_BUDGET = 150  # per Project: background calls share the user's own Claude limits


@dataclass(frozen=True)
class Job:
    project_id: str
    key: str
    material: Material
    open_store: Callable[[], ProjectStore]


class Explainer:
    def __init__(self, ask: Callable[[str], str], daily_budget: int = DAILY_CARD_BUDGET) -> None:
        self._ask = ask
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
                card = parse_card(self._ask(prompt_for(job.material)), job.material)
                with job.open_store() as store:
                    store.save_card(job.key, job.material.digest, card.to_json(), CARD_PRODUCER, _now())
                self._set(job, None)
            except (ClaudeUnavailableError, CardFormatError) as error:
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

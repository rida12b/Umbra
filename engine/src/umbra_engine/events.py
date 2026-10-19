"""Live events of each Project (re-indexed, card rewritten), for pages that follow them.

Published from background threads, read by the streaming route: a short, numbered history per
Project, so a page that reconnects with the last number it saw gets what it missed.
"""

import threading
from collections import deque

HISTORY = 200


class EventHub:
    def __init__(self) -> None:
        self._events: dict[str, deque[tuple[int, dict]]] = {}
        self._next = 1
        self._lock = threading.Lock()

    def publish(self, project_id: str, event: dict) -> None:
        with self._lock:
            history = self._events.setdefault(project_id, deque(maxlen=HISTORY))
            history.append((self._next, event))
            self._next += 1

    def since(self, project_id: str, last_seen: int) -> list[tuple[int, dict]]:
        with self._lock:
            return [
                (number, event) for number, event in self._events.get(project_id, ()) if number > last_seen
            ]

    def latest(self) -> int:
        with self._lock:
            return self._next - 1

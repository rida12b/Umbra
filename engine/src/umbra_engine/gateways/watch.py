"""File-system changes under a Project, as a bare signal: "something changed, look again".

No path leaves this module: what changed is decided by indexing again through the Secret Guard.
"""

import threading
from collections.abc import Callable
from pathlib import Path

from watchfiles import DefaultFilter, watch

DEBOUNCE_MS = 1500  # an editor or Claude often writes several files in a row
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".umbra"}


class _Filter(DefaultFilter):
    def __init__(self) -> None:
        super().__init__(ignore_dirs=tuple(DefaultFilter.ignore_dirs) + tuple(IGNORED_DIRS))


def watch_project(root: Path, on_change: Callable[[], object], stop: threading.Event) -> threading.Thread:
    """Calls `on_change` (from a daemon thread) after each burst of changes, until `stop` is set."""

    def run() -> None:
        for _ in watch(
            root, watch_filter=_Filter(), debounce=DEBOUNCE_MS, stop_event=stop, raise_interrupt=False
        ):
            try:
                on_change()
            except Exception:  # noqa: BLE001 — a failed refresh must not stop the watch
                continue

    thread = threading.Thread(target=run, name=f"umbra-watch-{root.name}", daemon=True)
    thread.start()
    return thread

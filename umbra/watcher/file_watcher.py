"""
File system watcher with debouncing for Python files.

This module provides a robust file watcher that:
- Monitors only .py files
- Debounces rapid saves
- Runs in a separate thread (non-blocking)
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

console = Console()


@dataclass
class FileChangeEvent:
    """Represents a file change event."""

    file_path: Path
    event_type: Literal["created", "modified", "deleted"]
    timestamp: datetime
    diff: str | None = None


class DebouncedHandler(FileSystemEventHandler):
    """
    Watchdog handler with debouncing logic.

    Collects events and only triggers callback after a quiet period.
    """

    # Patterns to ignore
    IGNORE_PATTERNS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".env",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        "__pypackages__",
    }

    # Extensions to watch (Python + JavaScript/TypeScript)
    WATCH_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

    def __init__(
        self,
        callback: Callable[[FileChangeEvent], None],
        debounce_seconds: float = 2.0,
    ):
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_events: dict[str, FileChangeEvent] = {}
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _should_ignore(self, path: str) -> bool:
        """Check if the path should be ignored."""
        path_obj = Path(path)

        # Check extension
        if path_obj.suffix not in self.WATCH_EXTENSIONS:
            return True

        # Check ignore patterns
        parts = path_obj.parts
        for pattern in self.IGNORE_PATTERNS:
            if pattern in parts:
                return True

        return False

    def _schedule_callback(self):
        """Schedule the debounced callback."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self.debounce_seconds, self._fire_callback)
            self._timer.start()

    def _fire_callback(self):
        """Fire the callback with all pending events."""
        with self._lock:
            events = list(self._pending_events.values())
            self._pending_events.clear()
            self._timer = None

        # Process each event
        for event in events:
            try:
                self.callback(event)
            except Exception as e:
                console.print(f"[red]Error in callback: {e}[/red]")

    def _handle_event(
        self, event_type: Literal["created", "modified", "deleted"], src_path: str
    ):
        """Handle a file system event."""
        if self._should_ignore(src_path):
            return

        path = Path(src_path)

        # Read file content for diff (if file exists)
        diff = None
        if event_type != "deleted" and path.exists():
            try:
                # For now, we'll just note the full content
                # A proper implementation would compute git-style diff
                diff = f"File {event_type}: {path.name}"
            except Exception:
                pass

        change_event = FileChangeEvent(
            file_path=path,
            event_type=event_type,
            timestamp=datetime.now(),
            diff=diff,
        )

        with self._lock:
            # Store/update the pending event for this file
            self._pending_events[src_path] = change_event

        self._schedule_callback()

    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            self._handle_event("created", event.src_path)

    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory:
            self._handle_event("modified", event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if not event.is_directory:
            self._handle_event("deleted", event.src_path)


class UmbraWatcher:
    """
    Main watcher class that manages the file system observer.

    Usage:
        watcher = UmbraWatcher(path=".", callback=my_callback)
        watcher.start()
        # ... do other things ...
        watcher.stop()
    """

    def __init__(
        self,
        path: str | Path,
        callback: Callable[[FileChangeEvent], None],
        debounce_seconds: float = 2.0,
    ):
        self.path = Path(path).resolve()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._observer: Observer | None = None
        self._handler: DebouncedHandler | None = None

    def start(self):
        """Start watching the directory."""
        if self._observer is not None:
            raise RuntimeError("Watcher is already running")

        self._handler = DebouncedHandler(
            callback=self.callback,
            debounce_seconds=self.debounce_seconds,
        )

        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.path), recursive=True)
        self._observer.start()

        console.print(f"[dim]Watching: {self.path}[/dim]")

    def stop(self):
        """Stop watching and cleanup."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        if self._handler is not None and self._handler._timer is not None:
            self._handler._timer.cancel()

        console.print("[dim]Watcher stopped[/dim]")

    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._observer is not None and self._observer.is_alive()


def start_watching(
    path: str | Path,
    callback: Callable[[FileChangeEvent], None],
    debounce_seconds: float = 2.0,
) -> UmbraWatcher:
    """
    Convenience function to start watching a directory.

    Args:
        path: Directory to watch (recursive)
        callback: Function called on each debounced change
        debounce_seconds: Delay before triggering callback

    Returns:
        UmbraWatcher instance with .stop() method
    """
    watcher = UmbraWatcher(
        path=path,
        callback=callback,
        debounce_seconds=debounce_seconds,
    )
    watcher.start()
    return watcher


if __name__ == "__main__":
    # Simple test
    def test_callback(event: FileChangeEvent):
        console.print(f"[green]Event:[/green] {event.event_type} - {event.file_path}")

    watcher = start_watching(".", test_callback, debounce_seconds=1.0)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()


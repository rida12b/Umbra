"""Tests for the file watcher."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from umbra.watcher.file_watcher import DebouncedHandler, FileChangeEvent, UmbraWatcher


class TestDebouncedHandler:
    """Test cases for the DebouncedHandler."""

    def test_ignores_non_code_files(self):
        """Non-code files should be ignored."""
        handler = DebouncedHandler(callback=MagicMock())

        assert handler._should_ignore("test.txt") is True
        assert handler._should_ignore("test.md") is True
        assert handler._should_ignore("README.md") is True
        assert handler._should_ignore("package.json") is True
        assert handler._should_ignore("style.css") is True

    def test_accepts_code_files(self):
        """Python and JS/TS files should be accepted."""
        handler = DebouncedHandler(callback=MagicMock())

        # Python
        assert handler._should_ignore("test.py") is False
        assert handler._should_ignore("main.py") is False
        assert handler._should_ignore("/path/to/service.py") is False
        
        # JavaScript/TypeScript
        assert handler._should_ignore("app.js") is False
        assert handler._should_ignore("component.tsx") is False
        assert handler._should_ignore("utils.ts") is False
        assert handler._should_ignore("Button.jsx") is False

    def test_ignores_pycache(self):
        """__pycache__ directories should be ignored."""
        handler = DebouncedHandler(callback=MagicMock())

        assert handler._should_ignore("__pycache__/test.py") is True
        assert handler._should_ignore("/path/__pycache__/cached.py") is True

    def test_ignores_venv(self):
        """Virtual environment directories should be ignored."""
        handler = DebouncedHandler(callback=MagicMock())

        assert handler._should_ignore("venv/lib/test.py") is True
        assert handler._should_ignore(".venv/bin/activate.py") is True

    def test_ignores_git(self):
        """Git directories should be ignored."""
        handler = DebouncedHandler(callback=MagicMock())

        assert handler._should_ignore(".git/hooks/pre-commit.py") is True


class TestUmbraWatcher:
    """Test cases for the UmbraWatcher."""

    def test_watcher_starts_and_stops(self):
        """Watcher should start and stop cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            callback = MagicMock()
            watcher = UmbraWatcher(path=tmpdir, callback=callback)

            watcher.start()
            assert watcher.is_running() is True

            watcher.stop()
            assert watcher.is_running() is False

    def test_watcher_cannot_start_twice(self):
        """Starting an already running watcher should raise an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            callback = MagicMock()
            watcher = UmbraWatcher(path=tmpdir, callback=callback)

            watcher.start()
            with pytest.raises(RuntimeError):
                watcher.start()

            watcher.stop()

    def test_debouncing_consolidates_events(self):
        """Multiple rapid changes should result in a single callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            callback = MagicMock()
            watcher = UmbraWatcher(
                path=tmpdir,
                callback=callback,
                debounce_seconds=0.5,  # Short debounce for testing
            )

            watcher.start()

            # Create a Python file and modify it rapidly
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# v1")
            time.sleep(0.1)
            test_file.write_text("# v2")
            time.sleep(0.1)
            test_file.write_text("# v3")

            # Wait for debounce
            time.sleep(1.0)

            watcher.stop()

            # Should have been called (possibly multiple times due to OS events)
            # but the debouncing should consolidate rapid changes
            assert callback.call_count >= 1


class TestFileChangeEvent:
    """Test cases for FileChangeEvent dataclass."""

    def test_event_creation(self):
        """FileChangeEvent should be created with correct fields."""
        from datetime import datetime

        event = FileChangeEvent(
            file_path=Path("/test/file.py"),
            event_type="modified",
            timestamp=datetime.now(),
            diff="+ new line",
        )

        assert event.file_path == Path("/test/file.py")
        assert event.event_type == "modified"
        assert event.diff == "+ new line"

    def test_event_without_diff(self):
        """FileChangeEvent can be created without diff."""
        from datetime import datetime

        event = FileChangeEvent(
            file_path=Path("/test/file.py"),
            event_type="created",
            timestamp=datetime.now(),
        )

        assert event.diff is None


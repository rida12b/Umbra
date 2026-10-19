"""Re-indexing reads only what changed: same result as a full run, far fewer file reads."""

import os
import subprocess
from pathlib import Path

import pytest
from secret_fixtures import write_repo

from umbra_engine.analyzers import default_analyzers
from umbra_engine.guard import SecretGuard
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry

FILES = {
    "app/main.py": "from .db import save\n\n\ndef handle(order):\n    return save(order)\n",
    "app/db.py": "def save(order):\n    return order\n",
    "app/util.py": "def helper():\n    return 1\n",
    "logo.png": "\x89PNG binary",
}


@pytest.fixture
def reads(monkeypatch) -> list[str]:
    seen: list[str] = []
    original = SecretGuard.read

    def counting(self, rel_path):
        seen.append(rel_path)
        return original(self, rel_path)

    monkeypatch.setattr(SecretGuard, "read", counting)
    return seen


def run(settings, root: Path, analyzers=None):
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            summary = index_project(project, store, analyzers)
            return summary, store.files(), store.claims(limit=100_000)


def touch_later(path: Path, text: str) -> None:
    """Rewrite and move the modification time forward, so a fast test cannot reuse a stale fingerprint."""
    stat = path.stat()
    path.write_text(text)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))


def test_nothing_changed_reads_nothing_and_gives_the_same_index(settings, make_repo, reads):
    root = write_repo(make_repo("same"), FILES, git=False)
    first = run(settings, root)
    reads.clear()
    second = run(settings, root)
    assert reads == []
    assert second[1] == first[1] and second[2] == first[2] and second[0] == first[0]


def test_one_changed_file_is_the_only_one_read(settings, make_repo, reads):
    root = write_repo(make_repo("one"), FILES, git=False)
    run(settings, root)
    reads.clear()
    touch_later(
        root / "app/db.py", "def save(order):\n    return order\n\n\ndef load(key):\n    return key\n"
    )
    _, files, claims = run(settings, root)
    assert reads == ["app/db.py"]
    assert any(c.object == "app/db.py::load" for c in claims)
    assert any(
        c.relation == "imports_module" and c.subject == "app/main.py" for c in claims
    )  # links recomputed
    fresh = run(settings, root)  # and a later run agrees with a full one
    assert fresh[2] == claims


def test_a_file_excluded_since_is_dropped_without_being_read(settings, make_repo, reads):
    root = write_repo(make_repo("excluded"), FILES, git=False)
    run(settings, root)
    reads.clear()
    (root / ".umbraignore").write_text("app/util.py\n")
    _, files, claims = run(settings, root)
    assert "app/util.py" not in reads
    assert next(f for f in files if f.path == "app/util.py").state == "skipped"
    assert not any(c.file == "app/util.py" for c in claims)


def test_reused_claims_follow_the_new_commit(settings, make_repo, reads):
    root = write_repo(make_repo("commit"), FILES)
    run(settings, root)  # nothing committed yet: worktree versions
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "."], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-qm", "init"], check=True, capture_output=True)
    commit = subprocess.run(
        [*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    reads.clear()
    _, _, claims = run(settings, root)
    assert reads == []
    assert {c.evidence_version for c in claims if c.file == "app/db.py"} == {commit}


def test_changed_analyzers_read_everything_again(settings, make_repo, reads):
    root = write_repo(make_repo("analyzers"), FILES, git=False)
    run(settings, root)
    reads.clear()
    run(settings, root, analyzers=default_analyzers()[:1])
    assert "app/main.py" in reads


def test_a_file_skipped_for_a_passing_reason_is_read_again(settings, make_repo, reads, monkeypatch):
    """A lock or a permission fixed later changes neither size nor modification time."""
    from umbra_engine.guard import UNREADABLE, Skipped

    root = write_repo(make_repo("locked"), FILES, git=False)
    original = SecretGuard.read

    def locked(self, rel_path):
        if rel_path == "app/util.py":
            return Skipped(rel_path, UNREADABLE, "PermissionError")
        return original(self, rel_path)

    monkeypatch.setattr(SecretGuard, "read", locked)
    _, files, _ = run(settings, root)
    assert next(f for f in files if f.path == "app/util.py").reason == UNREADABLE
    monkeypatch.setattr(SecretGuard, "read", original)
    _, files, claims = run(settings, root)
    assert next(f for f in files if f.path == "app/util.py").state == "readable"
    assert any(c.object == "app/util.py::helper" for c in claims)

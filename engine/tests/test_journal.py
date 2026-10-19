"""The Event Journal's guarantees (SPEC S5): unique ids, idempotent replay, nothing lost while the engine
is down, half-written files ignored, parallel sessions kept apart, turns rebuilt in order."""

import json
import uuid
from pathlib import Path

from secret_fixtures import PLANTED, write_repo

from umbra_engine.journal import ingest, spool_folder, stored_events, turns
from umbra_engine.registry import Registry


def drop(home: Path, kind: str, session: str, at: str, cwd: Path, files=(), text="", event_id=None) -> str:
    """What the hook does: write the whole event to a temporary name, then rename it into place."""
    folder = spool_folder(home)
    folder.mkdir(parents=True, exist_ok=True)
    event_id = event_id or uuid.uuid4().hex
    event = {"id": event_id, "at": at, "kind": kind, "session": session, "cwd": str(cwd),
             "files": [str(f) for f in files], "text": text}  # fmt: skip
    name = f"{at.replace(':', '').replace('-', '')}-{event_id}"  # no ':' in Windows file names
    temporary = folder / f"{name}.tmp"
    temporary.write_text(json.dumps(event), encoding="utf-8")
    temporary.rename(folder / f"{name}.json")
    return event_id


def setup(settings, make_repo):
    root = write_repo(make_repo("shop"), {"app/a.py": "x = 1\n", "app/b.py": "y = 2\n"}, git=False)
    registry = Registry(settings)
    project, _ = registry.add(root)
    return registry, project, root


def run_ingest(settings, registry):
    return ingest(settings.home, registry.list(), registry.open_store)


def project_turns(registry, project):
    with registry.open_store(project) as store:
        return turns(stored_events(store), project)


def test_a_turn_links_the_prompt_the_edited_files_and_the_final_message(settings, make_repo):
    registry, project, root = setup(settings, make_repo)
    drop(settings.home, "prompt", "s1", "2026-10-19T10:00:00", root, text="Rename save to store")
    drop(settings.home, "edit", "s1", "2026-10-19T10:00:05", root, files=[root / "app" / "a.py"])
    drop(
        settings.home,
        "edit",
        "s1",
        "2026-10-19T10:00:06",
        root,
        files=[root / "app" / "b.py", root / "app" / "a.py"],
    )
    drop(settings.home, "stop", "s1", "2026-10-19T10:00:09", root, text="Done: renamed in 2 files.")
    assert run_ingest(settings, registry) == {project.id: 4}
    [turn] = project_turns(registry, project)
    assert (turn.prompt, turn.files, turn.message) == (
        "Rename save to store",
        ["app/a.py", "app/b.py"],
        "Done: renamed in 2 files.",
    )
    assert list(spool_folder(settings.home).iterdir()) == []  # ingested events leave the spool
    registry.close()


def test_replaying_the_same_events_changes_nothing(settings, make_repo):
    registry, project, root = setup(settings, make_repo)
    event_id = drop(settings.home, "edit", "s1", "2026-10-19T10:00:05", root, files=[root / "app" / "a.py"])
    run_ingest(settings, registry)
    drop(
        settings.home,
        "edit",
        "s1",
        "2026-10-19T10:00:05",
        root,
        files=[root / "app" / "a.py"],
        event_id=event_id,
    )
    assert run_ingest(settings, registry) == {}  # same id: already stored
    with registry.open_store(project) as store:
        assert len(store.events()) == 1
    registry.close()


def test_a_half_written_event_is_ignored_and_the_rest_goes_through(settings, make_repo):
    """A power cut during the hook's write leaves a temporary file, never a truncated event."""
    registry, project, root = setup(settings, make_repo)
    folder = spool_folder(settings.home)
    folder.mkdir(parents=True)
    (folder / "20261019T100001-cut.tmp").write_text('{"id": "cut", "kind": "ed')
    (folder / "20261019T100002-bad.json").write_text("{not json")
    drop(settings.home, "prompt", "s1", "2026-10-19T10:00:03", root, text="Fix the bug")
    assert run_ingest(settings, registry) == {project.id: 1}
    registry.close()


def test_events_written_while_the_engine_is_down_are_ingested_later(settings, make_repo):
    registry, project, root = setup(settings, make_repo)
    for second in range(30):  # a burst of edits, nobody ingesting
        drop(
            settings.home, "edit", "s1", f"2026-10-19T10:00:{second:02}", root, files=[root / "app" / "a.py"]
        )
    assert run_ingest(settings, registry) == {project.id: 30}
    registry.close()


def test_parallel_sessions_keep_their_own_turns(settings, make_repo):
    registry, project, root = setup(settings, make_repo)
    drop(settings.home, "prompt", "s1", "2026-10-19T10:00:00", root, text="first")
    drop(settings.home, "prompt", "s2", "2026-10-19T10:00:01", root, text="second")
    drop(settings.home, "edit", "s2", "2026-10-19T10:00:02", root, files=[root / "app" / "b.py"])
    drop(settings.home, "edit", "s1", "2026-10-19T10:00:03", root, files=[root / "app" / "a.py"])
    drop(settings.home, "stop", "s1", "2026-10-19T10:00:04", root, text="one")
    drop(settings.home, "stop", "s2", "2026-10-19T10:00:05", root, text="two")
    run_ingest(settings, registry)
    by_prompt = {t.prompt: (t.files, t.message) for t in project_turns(registry, project)}
    assert by_prompt == {"first": (["app/a.py"], "one"), "second": (["app/b.py"], "two")}
    registry.close()


def test_events_of_other_folders_are_not_stored_and_secrets_are_masked(settings, make_repo, tmp_path):
    registry, project, root = setup(settings, make_repo)
    elsewhere = tmp_path / "other-project"
    drop(settings.home, "edit", "s9", "2026-10-19T10:00:00", elsewhere, files=[elsewhere / "x.py"])
    drop(settings.home, "prompt", "s1", "2026-10-19T10:00:01", root, text=f"use token {PLANTED['github']}")
    assert run_ingest(settings, registry) == {project.id: 1}
    [turn] = project_turns(registry, project)
    assert PLANTED["github"] not in turn.prompt
    registry.close()

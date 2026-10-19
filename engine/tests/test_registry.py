import ctypes
import multiprocessing
import os
import sys
from pathlib import Path

import pytest

from umbra_engine.project_store import SCHEMA_VERSION, STORE_FILE, ProjectStore
from umbra_engine.registry import ProjectPathError, Registry, project_id_for


def test_add_creates_isolated_store_under_umbra_home(settings, make_repo):
    repo = make_repo("shop-api")

    project, created = Registry(settings).add(repo)

    assert created
    assert project.root == repo.resolve()
    assert (settings.projects_dir / project.id / STORE_FILE).is_file()
    assert ProjectStore.open_existing(settings.projects_dir / project.id).schema_version() == SCHEMA_VERSION
    assert not any(repo.iterdir()), "nothing may be written inside the registered folder"


def test_add_is_idempotent_and_id_is_stable(settings, make_repo):
    repo = make_repo("shop-api")
    first, _ = Registry(settings).add(repo)

    again, created = Registry(settings).add(str(repo) + os.sep)

    assert not created
    assert again.id == first.id
    assert len(Registry(settings).list()) == 1
    assert first.id == project_id_for(repo.resolve())


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path rules")
def test_windows_case_and_short_names_resolve_to_the_same_project(settings, make_repo):
    repo = make_repo("Long Folder Name For Short")
    project, _ = Registry(settings).add(repo)

    upper, created_upper = Registry(settings).add(str(repo).upper())
    assert not created_upper and upper.id == project.id

    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetShortPathNameW(str(repo), buffer, 1024)  # pyright: ignore[reportAttributeAccessIssue]
    short = buffer.value
    if "~" not in short:
        pytest.skip("8.3 names disabled on this volume")
    via_short, created_short = Registry(settings).add(short)
    assert not created_short and via_short.id == project.id
    assert "~" not in str(via_short.root)


def test_missing_path_is_rejected_with_a_clear_error(settings, tmp_path: Path):
    with pytest.raises(ProjectPathError, match="does not exist"):
        Registry(settings).add(tmp_path / "nope")


def test_file_path_is_rejected(settings, tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("x")
    with pytest.raises(ProjectPathError, match="not a directory"):
        Registry(settings).add(file)


def test_two_projects_get_two_isolated_stores(settings, make_repo):
    with Registry(settings) as registry:
        a, _ = registry.add(make_repo("a"))
        b, _ = registry.add(make_repo("b"))

    with ProjectStore.open_existing(settings.projects_dir / a.id) as store_a:
        store_a._db.execute("INSERT INTO meta(key, value) VALUES ('only_in_a', 'x')")
    with ProjectStore.open_existing(settings.projects_dir / b.id) as store_b:
        keys = [row[0] for row in store_b._db.execute("SELECT key FROM meta")]
    assert a.id != b.id
    assert "only_in_a" not in keys


def _add_in_process(home: str, path: str, results) -> None:
    from umbra_engine.settings import Settings

    with Registry(Settings(home=Path(home))) as registry:
        project, created = registry.add(path)
    results.put((project.id, created))


def test_concurrent_adds_of_the_same_path_create_one_project(settings, make_repo):
    repo = make_repo("raced")
    results = multiprocessing.Queue()
    workers = [
        multiprocessing.Process(target=_add_in_process, args=(str(settings.home), str(repo), results))
        for _ in range(5)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=60)
    outcomes = [results.get(timeout=5) for _ in workers]

    assert len({project_id for project_id, _ in outcomes}) == 1
    assert sum(created for _, created in outcomes) == 1
    with Registry(settings) as registry:
        assert len(registry.list()) == 1


def test_empty_path_is_rejected(settings):
    with pytest.raises(ProjectPathError, match="empty"):
        Registry(settings).add("  ")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path rules")
def test_extended_length_prefix_resolves_to_the_same_project(settings, make_repo):
    repo = make_repo("prefixed")
    with Registry(settings) as registry:
        plain, _ = registry.add(repo)
        prefixed, created = registry.add("\\\\?\\" + str(repo.resolve()))
    assert not created and prefixed.id == plain.id


def test_non_ascii_folder_gets_an_ascii_id(settings, make_repo):
    with Registry(settings) as registry:
        project, _ = registry.add(make_repo("projé ünï 日本"))
    assert project.id.startswith("proje-uni-")
    assert project.id.isascii()


def _open_registry_at_barrier(home: str, barrier) -> None:
    from umbra_engine.settings import Settings

    barrier.wait()
    Registry(Settings(home=Path(home))).close()


def test_many_processes_opening_a_new_registry_at_once_do_not_fail(settings):
    barrier = multiprocessing.Barrier(12)
    workers = [
        multiprocessing.Process(target=_open_registry_at_barrier, args=(str(settings.home), barrier))
        for _ in range(12)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=60)
    assert [worker.exitcode for worker in workers] == [0] * 12

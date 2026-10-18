from pathlib import Path

import pytest
from secret_fixtures import FILES, GH, PLANTED, store_bytes, write_repo

from umbra_engine import cli
from umbra_engine.guard import EXCLUDED_SENSITIVE, EXCLUDED_UMBRAIGNORE, SECRET_IN_PATH
from umbra_engine.indexer import index_project
from umbra_engine.registry import ProjectPathError, Registry


@pytest.fixture
def repo(make_repo) -> Path:
    return write_repo(make_repo("planted"), FILES)


def test_index_records_every_file_and_the_store_holds_no_planted_secret(settings, repo):
    with Registry(settings) as registry:
        project, _ = registry.add(repo)
        with registry.open_store(project) as store:
            summary = index_project(project, store)
            inventory = {entry.path: entry for entry in store.files()}

    assert summary.skipped == {EXCLUDED_SENSITIVE: 2, EXCLUDED_UMBRAIGNORE: 1}
    assert summary.redacted_secrets > 0
    assert inventory[".env"].reason == EXCLUDED_SENSITIVE
    assert inventory["private/notes.md"].reason == EXCLUDED_UMBRAIGNORE
    assert inventory["src/config.py"].state == "readable"
    data = store_bytes(settings.projects_dir / project.id)
    for value in PLANTED.values():
        assert value.encode() not in data


def test_a_secret_in_a_file_name_is_never_stored(settings, make_repo):
    root = write_repo(make_repo("named"), {f"logs/{GH}.txt": "x\n", "a.py": "x = 1\n"}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            skipped = [e for e in store.files() if e.state == "skipped"]
    assert [(e.reason, e.detail) for e in skipped] == [(EXCLUDED_SENSITIVE, SECRET_IN_PATH)]
    assert GH.encode() not in store_bytes(settings.projects_dir / project.id)


def test_a_folder_whose_path_holds_a_secret_is_refused_without_echoing_it(settings, make_repo):
    with pytest.raises(ProjectPathError) as error, Registry(settings) as registry:
        registry.add(make_repo(f"deploy-{GH}"))
    assert GH not in str(error.value)


def test_index_through_api_and_cli(client, auth, repo, settings, monkeypatch, capsys):
    project = client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()
    response = client.post(f"/v1/projects/{project['id']}/index", headers=auth)
    assert response.status_code == 200
    assert response.json()["skipped"] == {EXCLUDED_SENSITIVE: 2, EXCLUDED_UMBRAIGNORE: 1}
    assert client.post("/v1/projects/unknown-0000/index", headers=auth).status_code == 404

    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["index", project["id"]]) == 0
    assert "readable" in capsys.readouterr().out

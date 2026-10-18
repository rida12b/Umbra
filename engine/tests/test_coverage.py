from pathlib import Path

import pytest
from secret_fixtures import write_repo

from umbra_engine import cli
from umbra_engine.coverage import coverage_report
from umbra_engine.guard import BINARY, EXCLUDED_SENSITIVE
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry

FILES = {
    "app/api.py": "def login():\n    return 1\n",
    "native/main.cpp": "int main() { return 0; }\n",
    "lib/util.rs": "pub fn helper() {}\n",
    "config.yaml": "a: 1\n",
    "README.md": "# app\n",
    ".env": "TOKEN=x\n",
    "notes": "no extension\n",
}


@pytest.fixture
def repo(make_repo) -> Path:
    root = write_repo(make_repo("coverage"), FILES, git=False)
    (root / "logo.png").write_bytes(b"\x89PNG\x00\x00")
    return root


def indexed_report(settings, repo):
    with Registry(settings) as registry:
        project, _ = registry.add(repo)
        with registry.open_store(project) as store:
            index_project(project, store)
            return project, coverage_report(store.files())


def test_every_file_is_accounted_for_exactly_once(settings, repo):
    _, report = indexed_report(settings, repo)
    paths = [f.path for f in report.files]
    assert sorted(paths) == sorted([*FILES, "logo.png"])
    assert report.covered + report.partial + report.gap == report.total == len(paths)


def test_states_and_reasons_are_honest(settings, repo):
    _, report = indexed_report(settings, repo)
    by_path = {f.path: f for f in report.files}
    assert by_path["app/api.py"].state == "covered"
    assert by_path["native/main.cpp"].state == "partial"
    assert "definitions not extracted for cpp" in by_path["native/main.cpp"].reasons
    assert "definitions unverified for rust (Hypotheses)" in by_path["lib/util.rs"].reasons
    assert by_path["config.yaml"].reasons == ["no analyzer for yaml"]
    assert by_path["notes"].reasons == ["no analyzer for notes"]
    assert by_path["logo.png"].reasons == [BINARY]
    assert by_path[".env"].reasons == [f"{EXCLUDED_SENSITIVE} (sensitive path)"]
    assert report.gap_reasons["no analyzer for yaml"] == 1


def test_coverage_api_counts_everything_and_filters_the_list(client, auth, repo):
    project = client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()
    client.post(f"/v1/projects/{project['id']}/index", headers=auth)
    url = f"/v1/projects/{project['id']}/coverage"

    full = client.get(url, headers=auth).json()
    gaps = client.get(url, params={"state": "gap"}, headers=auth).json()
    assert full["total"] == len(full["files"]) == len(FILES) + 1
    assert gaps["total"] == full["total"] and all(f["state"] == "gap" for f in gaps["files"])
    assert len(gaps["files"]) == full["gap"]
    assert client.get(url, params={"state": "unknown"}, headers=auth).status_code == 422


def test_coverage_cli_prints_counts_and_reasons(settings, repo, monkeypatch, capsys):
    project, _ = indexed_report(settings, repo)
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["coverage", project.id]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"{len(FILES) + 1} files: 1 covered, 2 partial, 5 Coverage Gaps")
    assert "no analyzer for yaml" in out

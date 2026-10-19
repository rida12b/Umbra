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


def test_a_never_indexed_or_older_index_is_refused_not_misread(client, auth, settings, repo):
    project = client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()
    url = f"/v1/projects/{project['id']}/coverage"
    assert client.get(url, headers=auth).status_code == 409
    client.post(f"/v1/projects/{project['id']}/index", headers=auth)
    assert client.get(url, headers=auth).status_code == 200

    import sqlite3

    with sqlite3.connect(settings.projects_dir / project["id"] / "store.sqlite") as db:
        db.execute("UPDATE meta SET value = '2' WHERE key = 'indexed_schema'")
    assert client.get(url, headers=auth).status_code == 409
    assert client.get(f"/v1/projects/{project['id']}/claims", headers=auth).status_code == 409


def test_languages_without_extraction_are_gaps_not_partial(settings, make_repo):
    files = {
        "api/demo.proto": 'syntax = "proto3";\nmessage Cart { string id = 1; }\n',
        "requirements.txt": "fastapi\n",
        "web/index.ts": 'export { login } from "./auth"\nexport * from "./types"\n',
    }
    root = write_repo(make_repo("gaps"), files, git=False)
    _, report = indexed_report(settings, root)
    by_path = {f.path: f for f in report.files}
    assert by_path["api/demo.proto"].reasons == ["no analyzer for proto"]
    assert by_path["requirements.txt"].reasons == ["no analyzer for *.txt"]
    assert by_path["web/index.ts"].state == "covered"


def test_reexports_are_import_facts(settings, make_repo):
    root = write_repo(make_repo("reexport"), {"web/index.ts": 'export { login } from "./auth"\n'}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            imports = [(c.object, c.line_start) for c in store.claims(relation="imports")]
    assert imports == [("./auth", 1)]


def test_git_links_written_as_text_are_not_read_as_code(settings, make_repo):
    import subprocess

    root = write_repo(make_repo("links"), {"real.py": "def f():\n    pass\n", "alias.py": "real.py"})
    blob = subprocess.run(
        ["git", "-C", str(root), "hash-object", "-w", "alias.py"], capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--add", "--cacheinfo", f"120000,{blob},alias.py"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "real.py"], check=True)
    _, report = indexed_report(settings, root)
    by_path = {f.path: f for f in report.files}
    assert by_path["alias.py"].reasons == ["link stored as text"]
    assert by_path["real.py"].state == "covered"


def test_coverage_cli_lists_files_of_one_state(settings, repo, monkeypatch, capsys):
    project, _ = indexed_report(settings, repo)
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["coverage", project.id, "--state", "gap"]) == 0
    listed = [line for line in capsys.readouterr().out.splitlines() if line.startswith("gap ")]
    assert len(listed) == 5 and any("config.yaml" in line for line in listed)

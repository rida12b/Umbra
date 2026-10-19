"""SPEC S2 / U1: the structural map, its stable keys and the Evidence behind every element."""

import subprocess
from pathlib import Path

import pytest
from secret_fixtures import PLANTED, write_repo

from umbra_engine.projection.model import MAX_VISIBLE

MANY = MAX_VISIBLE + 3
FILES = {
    "compose.yml": (
        "services:\n  backend:\n    build: ./backend\n    ports: ['8000:8000', '8000:8000']\n"
        "    depends_on: [db]\n  db:\n    image: postgres:16\n"
    ),
    "backend/Dockerfile": "FROM python:3.12\nCOPY . /app\n",
    "backend/app/main.py": "from .core import config\n\n\ndef run():\n    return config.NAME\n",
    "backend/app/core/__init__.py": "",
    "backend/app/core/config.py": "NAME = 'x'\n\n\nclass Settings:\n    def load(self):\n        return 1\n",
    "backend/app/core/secrets.py": f'GITHUB_TOKEN = "{PLANTED["github"]}"\n\n\ndef token():\n    return 1\n',
    "tools/report.py": "def report():\n    return 0\n",
    ".env": f"API_TOKEN={PLANTED['env_file']}\n",
    **{f"backend/app/handlers/h{i:02}.py": f"def handle_{i}():\n    return {i}\n" for i in range(MANY)},
}


def git(root: Path, *args: str) -> str:
    command = [
        "git",
        "-C",
        str(root),
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "core.autocrlf=false",
    ]
    return subprocess.run([*command, *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(make_repo) -> Path:
    root = write_repo(make_repo("shop"), FILES)
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


@pytest.fixture
def project(client, auth, repo) -> str:
    return client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()["id"]


def index(client, auth, project: str) -> dict:
    response = client.post(f"/v1/projects/{project}/index", headers=auth)
    assert response.status_code == 200
    return response.json()


def view(client, auth, project: str, node: str = "app:", expand: bool = False) -> dict:
    params: dict[str, str | bool] = {"node": node, "expand": expand}
    response = client.get(f"/v1/projects/{project}/map", params=params, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def all_claims(client, auth, project: str) -> list[dict]:
    response = client.get(f"/v1/projects/{project}/claims", params={"limit": 1000}, headers=auth)
    assert int(response.headers["X-Total-Count"]) < 1000
    return response.json()


def all_claim_keys(client, auth, project: str) -> set[str]:
    return {c["key"] for c in all_claims(client, auth, project)}


def keys_of(map_view: dict) -> list[str]:
    return [n["key"] for n in map_view["nodes"]]


def test_map_before_indexing_is_refused(client, auth, project):
    assert client.get(f"/v1/projects/{project}/map", headers=auth).status_code == 409


def test_application_level_shows_services_and_their_declared_links(client, auth, project):
    index(client, auth, project)
    top = view(client, auth, project)

    assert keys_of(top) == [
        "service:backend",
        "service:db",
        "dir:tools",
    ]  # compose.yml is Evidence, not a Module
    backend = top["nodes"][0]
    assert backend["status"] == "declaration"
    assert backend["details"]["ports"] == ["8000:8000"]  # declared twice, shown once
    assert backend["details"]["code"] == ["backend"]
    [link] = top["edges"]
    assert (link["source"], link["target"], link["relation"], link["status"]) == (
        "service:backend",
        "service:db",
        "depends_on",
        "declaration",
    )


def test_drill_down_from_service_to_function_with_breadcrumbs(client, auth, project):
    index(client, auth, project)
    assert "dir:backend/app" in keys_of(view(client, auth, project, "service:backend"))
    component = view(client, auth, project, "dir:backend/app")
    imports = [e for e in component["edges"] if e["relation"] == "imports"]
    assert {(e["source"], e["target"], e["status"]) for e in imports} == {
        ("backend/app/main.py", "dir:backend/app/core", "fact")
    }

    module = view(client, auth, project, "backend/app/core/config.py")
    assert [c["label"] for c in module["breadcrumbs"]] == ["shop", "backend", "app", "core", "config.py"]
    [settings] = [n for n in module["nodes"] if n["label"] == "Settings"]
    assert settings["kind"] == "class" and settings["lines"] == [4, 6]
    assert keys_of(view(client, auth, project, settings["key"])) == [
        "backend/app/core/config.py::Settings.load"
    ]


def test_more_than_twelve_children_are_grouped_until_expanded(client, auth, project):
    index(client, auth, project)
    grouped = view(client, auth, project, "dir:backend/app/handlers")
    assert grouped["total_children"] == MANY
    assert len(grouped["nodes"]) == MAX_VISIBLE
    group = grouped["nodes"][-1]
    assert group["kind"] == "group" and len(group["hidden"]) == MANY - (MAX_VISIBLE - 1)

    expanded = view(client, auth, project, "dir:backend/app/handlers", expand=True)
    assert len(expanded["nodes"]) == MANY and all(n["kind"] != "group" for n in expanded["nodes"])


def test_unknown_element_is_404(client, auth, project):
    index(client, auth, project)
    response = client.get(f"/v1/projects/{project}/map", params={"node": "nope/missing.py"}, headers=auth)
    assert response.status_code == 404


def test_keys_are_stable_across_index_runs_and_unrelated_edits(client, auth, project, repo):
    index(client, auth, project)
    before = all_claim_keys(client, auth, project)
    nodes_before = keys_of(view(client, auth, project, "dir:backend/app"))

    index(client, auth, project)
    assert all_claim_keys(client, auth, project) == before

    (repo / "tools" / "report.py").write_text("def report():\n    return 1\n\n\ndef extra():\n    return 2\n")
    index(client, auth, project)
    after = all_claim_keys(client, auth, project)
    assert before <= after  # the edited file keeps its old keys: same subject, relation and object
    assert len(after) == len(before) + 1  # only `extra` is new
    assert keys_of(view(client, auth, project, "dir:backend/app")) == nodes_before


def evidence_versions(client, auth, project: str) -> dict[str, set[str]]:
    versions: dict[str, set[str]] = {}
    for claim in all_claims(client, auth, project):
        versions.setdefault(claim["file"], set()).add(claim["evidence_version"])
    return versions


def test_evidence_version_is_the_commit_for_clean_files_and_a_content_hash_otherwise(
    client, auth, project, repo
):
    commit = git(repo, "rev-parse", "HEAD")
    summary = index(client, auth, project)
    assert summary["git_commit"] == commit and summary["uncommitted_changes"] is False
    assert evidence_versions(client, auth, project)["backend/app/main.py"] == {commit}

    (repo / "backend/app/main.py").write_text("def run():\n    return 2\n")
    (repo / "tools/new.py").write_text("def fresh():\n    return 3\n")
    assert index(client, auth, project)["uncommitted_changes"] is True
    versions = evidence_versions(client, auth, project)
    [modified], [untracked] = versions["backend/app/main.py"], versions["tools/new.py"]
    assert modified.startswith("worktree:") and untracked.startswith("worktree:") and modified != untracked
    assert versions["tools/report.py"] == {commit}


def test_edge_evidence_resolves_to_a_claim_and_its_lines(client, auth, project):
    index(client, auth, project)
    [link] = view(client, auth, project)["edges"]
    claim = client.get(f"/v1/projects/{project}/claims/{link['evidence'][0]}", headers=auth).json()
    assert claim["file"] == "compose.yml" and claim["relation"] == "depends_on"

    excerpt = client.get(
        f"/v1/projects/{project}/evidence",
        params={"file": claim["file"], "start": claim["line_start"], "end": claim["line_end"]},
        headers=auth,
    ).json()
    assert excerpt["current"] is True
    shown = excerpt["lines"][claim["line_start"] - excerpt["first_line"]]
    assert "depends_on" in shown
    assert client.get(f"/v1/projects/{project}/claims/unknown", headers=auth).status_code == 404


def test_evidence_is_redacted_and_never_reads_excluded_files(client, auth, project):
    index(client, auth, project)
    excerpt = client.get(
        f"/v1/projects/{project}/evidence",
        params={"file": "backend/app/core/secrets.py", "start": 1, "end": 5},
        headers=auth,
    )
    assert excerpt.status_code == 200 and PLANTED["github"] not in excerpt.text
    for file in (".env", "../outside.py", "missing.py"):
        response = client.get(
            f"/v1/projects/{project}/evidence", params={"file": file, "start": 1, "end": 1}, headers=auth
        )
        assert response.status_code == 404 and PLANTED["env_file"] not in response.text


def test_evidence_says_when_the_file_changed_since_indexing(client, auth, project, repo):
    index(client, auth, project)
    (repo / "backend/app/main.py").write_text("\n\nfrom .core import config\n")
    excerpt = client.get(
        f"/v1/projects/{project}/evidence",
        params={"file": "backend/app/main.py", "start": 1, "end": 1},
        headers=auth,
    ).json()
    assert excerpt["current"] is False


def test_a_service_code_root_nested_in_a_component_is_reachable_both_ways(client, auth, make_repo):
    """otel-demo: `frontendTests` is built from `src/frontend`, which is also a directory under `src`."""
    files = {
        "compose.yml": (
            "services:\n  e2e:\n    build:\n      context: ./\n      dockerfile: ./src/web/Dockerfile.e2e\n"
        ),
        "src/web/Dockerfile.e2e": "FROM node:20\n",
        "src/web/app.ts": "export function start() { return 1 }\n",
        "src/api/main.py": "def serve():\n    return 1\n",
    }
    root = write_repo(make_repo("nested"), files, git=False)
    project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
    index(client, auth, project)

    assert "src/web/app.ts" in keys_of(view(client, auth, project, "service:e2e"))
    assert "dir:src/web" in keys_of(view(client, auth, project, "dir:src"))
    web = view(client, auth, project, "dir:src/web")
    assert [c["key"] for c in web["breadcrumbs"]] == ["app:", "dir:src", "dir:src/web"]

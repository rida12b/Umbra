"""Independent adversarial tests for U1 (structural map, stable keys, Evidence). Written by a tester,
not by the author of the code: each test states the promise it checks."""

import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from secret_fixtures import PLANTED, write_repo

from umbra_engine.projection.model import MAX_VISIBLE


def git(root: Path, *args: str) -> str:
    base = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
    return subprocess.run([*base, *args], check=True, capture_output=True, text=True).stdout.strip()


def commit_all(root: Path) -> str:
    git(root, "add", ".")
    git(root, "commit", "-qm", "c")
    return git(root, "rev-parse", "HEAD")


def register(client, auth, root: Path) -> str:
    response = client.post("/v1/projects", json={"path": str(root)}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def index(client, auth, project: str) -> dict:
    response = client.post(f"/v1/projects/{project}/index", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def get_map(client, auth, project: str, node: str = "app:", expand: bool = False):
    return client.get(f"/v1/projects/{project}/map", params={"node": node, "expand": expand}, headers=auth)


def view(client, auth, project: str, node: str = "app:", expand: bool = False) -> dict:
    response = get_map(client, auth, project, node, expand)
    assert response.status_code == 200, f"{node}: {response.status_code} {response.text}"
    return response.json()


def keys_of(map_view: dict) -> list[str]:
    return [n["key"] for n in map_view["nodes"]]


def claims(client, auth, project: str, **filters: str) -> list[dict]:
    response = client.get(f"/v1/projects/{project}/claims", params={"limit": 1000, **filters}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def versions_of(client, auth, project: str, file: str) -> set[str]:
    return {c["evidence_version"] for c in claims(client, auth, project, file=file)}


def evidence(client, auth, project: str, file: str, start: int, end: int):
    return client.get(
        f"/v1/projects/{project}/evidence",
        params={"file": file, "start": start, "end": end},
        headers=auth,
    )


def make_project(client, auth, make_repo, name: str, files: dict[str, str], git_repo: bool = False) -> str:
    root = write_repo(make_repo(name), files, git=git_repo)
    if git_repo:
        commit_all(root)
    project = register(client, auth, root)
    index(client, auth, project)
    return project


# --- Map: services and code roots -------------------------------------------------------------------


def test_every_service_is_reachable_when_one_is_built_from_the_repo_root(client, auth, make_repo):
    """`build: .` is the most common compose layout: the code root is the whole repo (`.`)."""
    files = {
        "compose.yml": (
            "services:\n  app:\n    build: .\n    depends_on: [db]\n  db:\n    image: postgres:16\n"
        ),
        "Dockerfile": "FROM python:3.12\n",
        "src/main.py": "def run():\n    return 1\n",
    }
    project = make_project(client, auth, make_repo, "rootbuild", files)
    top = view(client, auth, project)
    assert {"service:app", "service:db"} <= set(keys_of(top))
    for node in keys_of(top):
        assert get_map(client, auth, project, node).status_code == 200, node


def test_two_services_sharing_one_code_root_are_both_browsable(client, auth, make_repo):
    files = {
        "compose.yml": ("services:\n  api:\n    build: ./backend\n  worker:\n    build: ./backend\n"),
        "backend/Dockerfile": "FROM python:3.12\n",
        "backend/app.py": "from .jobs import run\n",
        "backend/jobs.py": "def run():\n    return 1\n",
    }
    project = make_project(client, auth, make_repo, "shared", files)
    for service in ("service:api", "service:worker"):
        assert "backend/app.py" in keys_of(view(client, auth, project, service))
    crumbs = view(client, auth, project, "backend/jobs.py")["breadcrumbs"]
    assert crumbs[0]["key"] == "app:" and crumbs[-1]["key"] == "backend/jobs.py"


# --- Map: grouping, leaves, nesting -----------------------------------------------------------------


def flat_dir(count: int) -> dict[str, str]:
    return {f"pkg/m{i:02}.py": f"def f{i}():\n    return {i}\n" for i in range(count)}


@pytest.mark.parametrize(("count", "grouped"), [(MAX_VISIBLE, False), (MAX_VISIBLE + 1, True)])
def test_group_appears_only_above_twelve_children(client, auth, make_repo, count, grouped):
    project = make_project(client, auth, make_repo, f"g{count}", {**flat_dir(count), "other/x.py": "X = 1\n"})
    nodes = view(client, auth, project, "dir:pkg")["nodes"]
    assert len(nodes) <= MAX_VISIBLE
    assert any(n["kind"] == "group" for n in nodes) is grouped
    if grouped:
        group = nodes[-1]
        assert group["key"] == "group:dir:pkg" and len(group["hidden"]) == count - (MAX_VISIBLE - 1)


def test_expand_on_a_leaf_is_an_empty_view_not_an_error(client, auth, make_repo):
    project = make_project(client, auth, make_repo, "leaf", {"a.py": "def f():\n    return 1\n"})
    leaf = view(client, auth, project, "a.py::f", expand=True)
    assert leaf["nodes"] == [] and leaf["total_children"] == 0
    assert leaf["parent"]["key"] == "a.py::f"


def test_nested_classes_nest_and_have_breadcrumbs(client, auth, make_repo):
    source = (
        "class Outer:\n"
        "    class Inner:\n"
        "        def deep(self):\n"
        "            return 1\n"
        "    def top(self):\n"
        "        return 2\n"
    )
    project = make_project(client, auth, make_repo, "nested", {"m.py": source, "n.py": "X = 1\n"})
    assert keys_of(view(client, auth, project, "m.py")) == ["m.py::Outer"]
    outer = keys_of(view(client, auth, project, "m.py::Outer"))
    assert set(outer) == {"m.py::Outer.Inner", "m.py::Outer.top"}
    deep = view(client, auth, project, "m.py::Outer.Inner.deep")
    assert [c["label"] for c in deep["breadcrumbs"]][-3:] == ["Outer", "Inner", "deep"]
    assert get_map(client, auth, project, "m.py::Outer.Missing").status_code == 404
    assert get_map(client, auth, project, "m.py::").status_code == 404


def test_unknown_or_malformed_nodes_are_404_not_500(client, auth, make_repo):
    project = make_project(client, auth, make_repo, "bad", {"src/a/b.py": "X = 1\n", "src/c.py": "Y = 1\n"})
    for node in ("", "dir:", "dir:src/a/b.py", "src\\a\\b.py", "../src/c.py", "group:app:", "service:x",
                 "dir:src/", "/src/c.py", "app:app:"):  # fmt: skip
        assert get_map(client, auth, project, node).status_code == 404, node


# --- Map: edges ---------------------------------------------------------------------------------------


def test_circular_imports_give_one_edge_each_way(client, auth, make_repo):
    files = {
        "pkg/__init__.py": "",
        "pkg/a.py": "from .b import g\n\n\ndef f():\n    return g()\n",
        "pkg/b.py": "from .a import f\n\n\ndef g():\n    return f()\n",
    }
    project = make_project(client, auth, make_repo, "cycle", files)
    edges = {
        (e["source"], e["target"], e["relation"], e["status"])
        for e in view(client, auth, project, "dir:pkg")["edges"]
    }
    assert edges == {
        ("pkg/a.py", "pkg/b.py", "imports", "fact"),
        ("pkg/b.py", "pkg/a.py", "imports", "fact"),
        ("pkg/a.py", "pkg/b.py", "calls", "hypothesis"),  # f() calls the imported g(): names matched
        ("pkg/b.py", "pkg/a.py", "calls", "hypothesis"),
    }


def test_edges_to_hidden_children_go_to_the_group(client, auth, make_repo):
    files = {
        **{f"pkg/m{i:02}.py": f"def f{i}():\n    return {i}\n" for i in range(MAX_VISIBLE + 4)},
        "pkg/a_main.py": "".join(f"from .m{i:02} import f{i}\n" for i in range(MAX_VISIBLE + 4)),
        "other/x.py": "X = 1\n",
    }
    project = make_project(client, auth, make_repo, "hidden", files)
    grouped = view(client, auth, project, "dir:pkg")
    shown = set(keys_of(grouped))
    for edge in grouped["edges"]:
        assert edge["source"] in shown and edge["target"] in shown, edge
    to_group = [e for e in grouped["edges"] if e["target"] == "group:dir:pkg"]
    assert to_group and to_group[0]["source"] == "pkg/a_main.py"
    assert sum(e["count"] for e in grouped["edges"]) == MAX_VISIBLE + 4


# --- Linkers -----------------------------------------------------------------------------------------


def import_links(client, auth, project: str) -> dict[str, tuple[str, str]]:
    return {
        c["subject"]: (c["object"], c["status"])
        for c in claims(client, auth, project, relation="imports_module")
    }


def test_relative_import_above_the_project_root_is_not_a_fact(client, auth, make_repo):
    """`from ...util import f` in `pkg/mod.py` climbs above the root: Python refuses it; it must not
    be presented as a Fact pointing at the root `util.py`."""
    files = {
        "pkg/__init__.py": "",
        "pkg/mod.py": "from ...util import f\n",
        "util.py": "def f():\n    pass\n",
    }
    project = make_project(client, auth, make_repo, "climb", files)
    assert "pkg/mod.py" not in import_links(client, auth, project)


def test_ambiguous_relative_python_import_is_not_a_fact(client, auth, make_repo):
    files = {
        "pkg/__init__.py": "",
        "pkg/main.py": "from .util import f\n",
        "pkg/util.py": "def f():\n    pass\n",
        "pkg/util/__init__.py": "def f():\n    pass\n",
    }
    project = make_project(client, auth, make_repo, "ambig", files)
    assert "pkg/main.py" not in import_links(client, auth, project)


def test_js_relative_import_with_explicit_extension_resolves(client, auth, make_repo):
    """ESM requires the extension (`./util.js`): the file exists and is unique, so it is a Fact."""
    files = {"web/main.js": "import { f } from './util.js'\nf()\n", "web/util.js": "export function f() {}\n"}
    project = make_project(client, auth, make_repo, "esm", files)
    assert import_links(client, auth, project).get("web/main.js") == ("web/util.js", "fact")


def test_absolute_python_import_is_only_a_hypothesis_and_dropped_when_ambiguous(client, auth, make_repo):
    files = {
        "svc/app.py": "import core.config\n",
        "svc/core/config.py": "X = 1\n",
        "lib/tool.py": "import shared.helpers\n",
        "a/shared/helpers.py": "X = 1\n",
        "b/shared/helpers.py": "X = 2\n",
    }
    project = make_project(client, auth, make_repo, "absimp", files)
    links = import_links(client, auth, project)
    assert links["svc/app.py"] == ("svc/core/config.py", "hypothesis")
    assert "lib/tool.py" not in links


K8S = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: shop
spec:
  template:
    metadata:
      labels:
        app: web
        tier: front
    spec:
      containers:
        - name: web
          image: web:1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: other
spec:
  template:
    metadata:
      labels:
        app: web
        tier: front
    spec:
      containers:
        - name: web
          image: web:1
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: shop
spec:
  selector:
    app: web
---
apiVersion: v1
kind: Service
metadata:
  name: strict
  namespace: shop
spec:
  selector:
    app: web
    tier: back
"""


def test_k8s_service_targets_only_matching_workloads_of_its_namespace(client, auth, make_repo):
    project = make_project(client, auth, make_repo, "k8s", {"deploy/all.yaml": K8S, "src/x.py": "X = 1\n"})
    targets = {(c["subject"], c["object"]) for c in claims(client, auth, project, relation="targets")}
    assert targets == {("k8s:shop/Service/web", "k8s:shop/Deployment/web")}


# --- Keys and Evidence versions ------------------------------------------------------------------------


def test_keys_do_not_depend_on_line_numbers(client, auth, make_repo):
    root = write_repo(make_repo("lines"), {"a.py": "import os\n\n\ndef f():\n    return 1\n"}, git=False)
    project = register(client, auth, root)
    index(client, auth, project)
    before = {c["key"] for c in claims(client, auth, project)}
    (root / "a.py").write_text("\n\n\n# moved\nimport os\n\n\ndef f():\n    return 1\n")
    index(client, auth, project)
    assert {c["key"] for c in claims(client, auth, project)} == before


def test_repeated_identical_claims_get_distinct_ranked_keys(client, auth, make_repo):
    project = make_project(client, auth, make_repo, "dups", {"a.py": "import os\nimport os\nimport os\n"})
    found = [c for c in claims(client, auth, project, file="a.py") if c["relation"] == "imports"]
    assert len(found) == 3 and len({c["key"] for c in found}) == 3


def test_repo_without_commit_is_worktree_everywhere(client, auth, make_repo):
    root = write_repo(make_repo("nocommit"), {"a.py": "def f():\n    return 1\n"})
    project = register(client, auth, root)
    summary = index(client, auth, project)
    assert summary["git_commit"] is None
    [version] = versions_of(client, auth, project, "a.py")
    assert version.startswith("worktree:")


def test_renamed_file_is_worktree_and_untouched_file_keeps_commit(client, auth, make_repo):
    root = write_repo(
        make_repo("rename"), {"old.py": "def f():\n    return 1\n", "keep.py": "def k():\n    return 1\n"}
    )
    head = commit_all(root)
    git(root, "mv", "old.py", "new.py")
    project = register(client, auth, root)
    index(client, auth, project)
    [renamed] = versions_of(client, auth, project, "new.py")
    assert renamed.startswith("worktree:")
    assert versions_of(client, auth, project, "keep.py") == {head}


def test_paths_with_spaces_and_unicode_are_clean_at_head(client, auth, make_repo):
    files = {"my dir/café été.py": "def f():\n    return 1\n", "x.py": "X = 1\n"}
    root = write_repo(make_repo("unicode"), files)
    head = commit_all(root)
    project = register(client, auth, root)
    index(client, auth, project)
    path = "my dir/café été.py"
    assert versions_of(client, auth, project, path) == {head}
    assert path in keys_of(view(client, auth, project, "dir:my dir"))
    assert evidence(client, auth, project, path, 1, 2).status_code == 200


def test_project_in_a_subfolder_of_a_git_repo_sees_its_modified_files(client, auth, make_repo):
    """git status paths are relative to the repository top, the Project's paths to the Project root."""
    outer = write_repo(
        make_repo("outer"), {"sub/a.py": "def f():\n    return 1\n", "sub/b.py": "def k():\n    return 1\n"}
    )
    head = commit_all(outer)
    (outer / "sub/a.py").write_text("def f():\n    return 2\n")
    project = register(client, auth, outer / "sub")
    summary = index(client, auth, project)
    assert summary["git_commit"] == head
    assert versions_of(client, auth, project, "b.py") == {head}
    [modified] = versions_of(client, auth, project, "a.py")
    assert modified.startswith("worktree:"), modified


# --- Evidence ------------------------------------------------------------------------------------------


@pytest.fixture
def small(client, auth, make_repo) -> tuple[str, Path]:
    lines = "".join(f"def f{i}():\r\n    return {i}\r\n" for i in range(200))  # CRLF, 400 lines
    root = write_repo(make_repo("ev"), {"a.py": lines, "b.py": "X = 1\n"}, git=False)
    project = register(client, auth, root)
    index(client, auth, project)
    return project, root


def test_crlf_definition_lines_point_at_the_definition(client, auth, small):
    project, _ = small
    [f7] = [c for c in claims(client, auth, small[0], file="a.py") if c["object"] == "a.py::f7"]
    shown = evidence(client, auth, project, "a.py", f7["line_start"], f7["line_end"]).json()
    line = shown["lines"][f7["line_start"] - shown["first_line"]]
    assert line == "def f7():" and not any("\r" in x for x in shown["lines"])


def test_evidence_ranges_are_bounded(client, auth, small):
    project, _ = small
    assert evidence(client, auth, project, "a.py", 5, 4).status_code == 404
    huge = evidence(client, auth, project, "a.py", 1, 10**9)
    assert huge.status_code == 200 and len(huge.json()["lines"]) <= 120
    assert evidence(client, auth, project, "a.py", 0, 1).status_code == 422


def test_evidence_past_end_of_file_is_not_a_silent_empty_excerpt(client, auth, small):
    project, _ = small
    response = evidence(client, auth, project, "a.py", 5000, 5001)
    assert response.status_code == 404 or response.json()["lines"], response.json()


def test_evidence_file_parameter_cannot_escape(client, auth, small, tmp_path):
    project, root = small
    (root.parent / "outside.py").write_text("SECRET = 1\n")
    for file in ("../outside.py", str(root.parent / "outside.py"), "a.py/../../outside.py", ".\\a.py",
                 "A.PY", "./a.py", "a.py\x00", "%2e%2e/outside.py"):  # fmt: skip
        response = evidence(client, auth, project, file, 1, 1)
        assert response.status_code == 404, (file, response.status_code)


def test_evidence_after_a_file_becomes_an_excluded_link_is_refused(client, auth, make_repo):
    root = write_repo(make_repo("swap"), {"a.py": "X = 1\n", ".env": f"API_TOKEN={PLANTED['env_file']}\n"},
                      git=False)  # fmt: skip
    project = register(client, auth, root)
    index(client, auth, project)
    (root / "a.py").unlink()
    try:
        (root / "a.py").symlink_to(root / ".env")
    except OSError:
        pytest.skip("symlinks need privileges on this machine")
    response = evidence(client, auth, project, "a.py", 1, 1)
    assert PLANTED["env_file"] not in response.text


def test_secret_in_a_file_name_never_reaches_the_map(client, auth, make_repo):
    name = f"src/{PLANTED['github']}.py"
    files = {name: "def f():\n    return 1\n", "src/ok.py": "X = 1\n"}
    project = make_project(client, auth, make_repo, "secretname", files)
    for node in ("app:", "dir:src"):
        response = get_map(client, auth, project, node, expand=True)
        assert PLANTED["github"] not in response.text
    assert PLANTED["github"] not in client.get(f"/v1/projects/{project}/claims", headers=auth).text


# --- Re-index, cache and concurrency ---------------------------------------------------------------------


def test_map_reflects_a_reindex_done_within_the_same_second(client, auth, make_repo, monkeypatch):
    """The graph cache is keyed by `indexed_at` (seconds): two runs in one second must not share it."""
    fixed = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return fixed

    monkeypatch.setattr("umbra_engine.indexer.datetime", FrozenClock)
    root = write_repo(make_repo("cache"), {"a.py": "X = 1\n", "b.py": "Y = 1\n"}, git=False)
    project = register(client, auth, root)
    index(client, auth, project)
    assert set(keys_of(view(client, auth, project))) == {"a.py", "b.py"}
    (root / "b.py").unlink()
    index(client, auth, project)
    assert keys_of(view(client, auth, project)) == ["a.py"]


def test_deleted_file_disappears_from_map_and_evidence(client, auth, make_repo):
    root = write_repo(make_repo("delete"), {"a.py": "X = 1\n", "b.py": "def g():\n    return 1\n"}, git=False)
    project = register(client, auth, root)
    index(client, auth, project)
    (root / "b.py").unlink()
    assert evidence(client, auth, project, "b.py", 1, 1).status_code == 404  # gone before re-index
    import time

    time.sleep(1.1)
    index(client, auth, project)
    assert keys_of(view(client, auth, project)) == ["a.py"]
    assert get_map(client, auth, project, "b.py::g").status_code == 404


def test_map_reads_during_index_runs_never_fail(client, auth, make_repo):
    files = {f"pkg/m{i:02}.py": f"from .m{(i + 1) % 30:02} import f\n\n\ndef f():\n    return {i}\n"
             for i in range(30)}  # fmt: skip
    root = write_repo(make_repo("busy"), {**files, "pkg/__init__.py": "", "x/y.py": "Y = 1\n"}, git=False)
    project = register(client, auth, root)
    index(client, auth, project)
    errors: list[str] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            response = get_map(client, auth, project, "dir:pkg", expand=True)
            if response.status_code != 200:
                errors.append(f"{response.status_code} {response.text[:200]}")

    with ThreadPoolExecutor(4) as pool:
        futures = [pool.submit(reader) for _ in range(3)]
        for _ in range(5):
            index(client, auth, project)
        stop.set()
        for future in futures:
            future.result()
    assert errors == []


def test_graph_cache_survives_many_projects_read_concurrently(client, auth, make_repo):
    """More Projects than cache slots, read from several threads: eviction must not raise."""
    projects = [
        make_project(client, auth, make_repo, f"p{i}", {f"m{i}.py": "X = 1\n", "z.py": "Z = 1\n"})
        for i in range(8)
    ]
    errors: list[str] = []

    def read(project: str) -> None:
        for _ in range(15):
            response = get_map(client, auth, project)
            if response.status_code != 200:
                errors.append(f"{response.status_code} {response.text[:200]}")

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(read, projects))
    assert errors == []

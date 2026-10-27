import subprocess
from pathlib import Path

import pytest
from secret_fixtures import GH, store_bytes, write_repo

from umbra_engine.analyzers.code import CodeAnalyzer
from umbra_engine.analyzers.signals import SignalsAnalyzer
from umbra_engine.claims import CALLS, DEFINES, IMPORTS
from umbra_engine.fact_check import check_facts
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry
from umbra_engine.store_schema import LIST_SEPARATOR

PYTHON = (
    '''import os
from app.core import db


class Svc:
    @staticmethod
    def run():
        return login("a", "b")


def login(user, pw):
    token = "'''
    + GH
    + """"
    if not check(pw):
        raise ValueError("bad")
    return db.create_session(user)
"""
)

TYPESCRIPT = """import { useQuery } from "@tanstack/react-query"
import * as api from "../client"

export const useAuth = () => {
  return api.login()
}

export function logout() {
  api.logout()
}
"""

GO = """package main

import "net/http"

func handler(w http.ResponseWriter, r *http.Request) {
\twrite(w)
}
"""

FILES = {"app/service.py": PYTHON, "web/auth.ts": TYPESCRIPT, "cmd/main.go": GO, "config.yaml": "a: 1\n"}


@pytest.fixture
def repo(make_repo) -> Path:
    root = write_repo(make_repo("mixed"), FILES)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        check=True,
    )
    return root


def claims_of(root: Path, rel_path: str) -> list:
    released = SecretGuard(root).read(rel_path)
    assert isinstance(released, GuardedFile)
    return list(CodeAnalyzer().analyze(released))


def test_definitions_are_facts_with_qualified_names_and_exact_lines(repo):
    defines = {(c.object, c.line_start) for c in claims_of(repo, "app/service.py") if c.relation == DEFINES}
    assert {
        ("app/service.py::Svc", 5),
        ("app/service.py::Svc.run", 7),
        ("app/service.py::login", 11),
    } <= defines


def test_imports_are_facts_naming_their_target(repo):
    py = {c.object for c in claims_of(repo, "app/service.py") if c.relation == IMPORTS and c.status == "fact"}
    ts = {c.object for c in claims_of(repo, "web/auth.ts") if c.relation == IMPORTS}
    go = {c.object for c in claims_of(repo, "cmd/main.go") if c.relation == IMPORTS}
    assert py == {"os", "app.core"}
    # `from app.core import db`: maybe the module `app.core.db`, only ever a guess (#105)
    names = [c for c in claims_of(repo, "app/service.py") if c.object_kind == "import-name"]
    assert [(c.object, c.status) for c in names] == [("app.core.db", "hypothesis")]
    assert ts == {"@tanstack/react-query", "../client"}
    assert go == {"net/http"}


def test_calls_are_hypotheses_attributed_to_their_caller(repo):
    calls = [c for c in claims_of(repo, "app/service.py") if c.relation == CALLS]
    assert calls and all(c.status == "hypothesis" for c in calls)
    assert ("app/service.py::Svc.run", "login") in {(c.subject, c.object) for c in calls}
    # `db.create_session(user)`: a method of another object, kept apart from a local `create_session`
    assert ("app/service.py::login", ".create_session") in {(c.subject, c.object) for c in calls}


def test_arrow_functions_count_as_definitions(repo):
    defines = {c.object for c in claims_of(repo, "web/auth.ts") if c.relation == DEFINES}
    assert {"web/auth.ts::useAuth", "web/auth.ts::logout"} <= defines


def test_configuration_files_are_left_to_other_analyzers(repo):
    released = SecretGuard(repo).read("config.yaml")
    assert isinstance(released, GuardedFile)
    assert not CodeAnalyzer().accepts(released)


def test_index_stores_claims_with_evidence_commit_and_no_secret(settings, repo):
    with Registry(settings) as registry:
        project, _ = registry.add(repo)
        with registry.open_store(project) as store:
            summary = index_project(project, store)
            stored = store.claims(file="app/service.py", relation=DEFINES)
            checks = check_facts(project, store, sample=100)
            inventory = {e.path: e for e in store.files()}
    assert summary.claims["fact"] > 0 and summary.claims["hypothesis"] > 0
    assert summary.git_commit is not None and len(summary.git_commit) == 40
    assert all(
        c.evidence_version == summary.git_commit and c.producer == CodeAnalyzer.producer for c in stored
    )
    assert checks and all(check.correct for check in checks)
    assert inventory["app/service.py"].analyzers.split(LIST_SEPARATOR) == [
        CodeAnalyzer.producer,
        SignalsAnalyzer.producer,
    ]
    assert inventory["config.yaml"].analyzers == ""
    assert GH.encode() not in store_bytes(settings.projects_dir / project.id)


def test_claims_api_filters_and_pages(client, auth, repo):
    project = client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()
    client.post(f"/v1/projects/{project['id']}/index", headers=auth)
    url = f"/v1/projects/{project['id']}/claims"

    facts = client.get(url, params={"status": "fact", "file": "web/auth.ts"}, headers=auth).json()
    assert facts and all(c["status"] == "fact" and c["file"] == "web/auth.ts" for c in facts)
    page = client.get(url, params={"limit": 2, "offset": 1}, headers=auth).json()
    assert len(page) == 2
    assert client.get(url, params={"status": "guess"}, headers=auth).status_code == 422
    assert client.get(url, params={"limit": 5000}, headers=auth).status_code == 422
    assert client.get(url).status_code == 401

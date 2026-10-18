"""Regressions found by the independent strict check: every Fact must name exactly what the code says."""

import subprocess
from pathlib import Path

import pytest
from secret_fixtures import write_repo

from umbra_engine.analyzers.code import CodeAnalyzer
from umbra_engine.analyzers.imports import import_targets
from umbra_engine.claims import DEFINES, IMPORTS
from umbra_engine.fact_check import check_facts
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry


@pytest.mark.parametrize(
    ("language", "statement", "targets"),
    [
        ("typescript", 'import react from "@vitejs/plugin-react-swc"', ["@vitejs/plugin-react-swc"]),
        ("typescript", 'import type { T } from "./t"', ["./t"]),
        ("javascript", 'const x = require("y")', ["y"]),
        ("python", "import os, sys as s", ["os", "sys"]),
        ("python", "from ..pkg.mod import (a,\n b)", ["..pkg.mod"]),
        ("java", "import static a.b.C.d;", ["a.b.C.d"]),
        ("java", "import io.grpc.*;", ["io.grpc.*"]),
        ("rust", "use actix_web::{web, App};", ["actix_web"]),
        ("csharp", "using static System.Math;", ["System.Math"]),
        ("csharp", "using Foo = Bar.Baz;", ["Bar.Baz"]),
        ("go", '"net/http"', ["net/http"]),
        ("cpp", '#include "demo.h"', ["demo.h"]),
        ("ruby", 'require_relative "lib/x"', ["lib/x"]),
        ("elixir", "alias Foo.Bar", ["Foo.Bar"]),
        ("cobol", "COPY BOOK.", []),
    ],
)
def test_import_targets_are_exact(language, statement, targets):
    assert import_targets(language, statement) == targets


def analyze(make_repo, rel_path: str, text: str) -> list:
    root = write_repo(make_repo("lang"), {rel_path: text}, git=False)
    released = SecretGuard(root).read(rel_path)
    assert isinstance(released, GuardedFile)
    return list(CodeAnalyzer().analyze(released))


def test_line_read_imports_cite_the_statement_not_the_blank_line_above(make_repo):
    claims = analyze(make_repo, "Program.cs", "// header\n\nusing System;\n\nusing Grpc.Core;\n")
    assert [(c.object, c.line_start, c.line_end) for c in claims if c.relation == IMPORTS] == [
        ("System", 3, 3),
        ("Grpc.Core", 5, 5),
    ]


def test_repeated_names_get_distinct_keys(make_repo):
    go = 'package main\n\ntype A struct{}\ntype B struct{}\n\nfunc (a A) String() string { return "a" }\n'
    go += 'func (b B) String() string { return "b" }\n'
    keys = [c.object for c in analyze(make_repo, "m.go", go) if c.relation == DEFINES]
    assert "m.go::String" in keys and "m.go::String~2" in keys
    assert len(keys) == len(set(keys))


def test_package_lines_are_not_definitions(make_repo):
    java = "package demo.shop;\n\npublic class Cart {\n  void add() {}\n}\n"
    keys = {c.object for c in analyze(make_repo, "Cart.java", java) if c.relation == DEFINES}
    assert keys == {"Cart.java::Cart", "Cart.java::Cart.add"}


def test_python_methods_are_methods(make_repo):
    kinds = {
        c.object: c.object_kind
        for c in analyze(make_repo, "s.py", "class S:\n    def run(self):\n        pass\n")
    }
    assert kinds["s.py::S.run"] == "method"


@pytest.mark.parametrize(
    ("rel_path", "text"), [("x.cpp", "#define X 1\nint main() { return 0; }\n"), ("m.kt", "fun main() {}\n")]
)
def test_languages_with_wrong_definitions_produce_none(make_repo, rel_path, text):
    assert not [c for c in analyze(make_repo, rel_path, text) if c.relation == DEFINES]


def test_unverified_languages_give_hypotheses_not_facts(make_repo):
    claims = analyze(make_repo, "lib.rs", "pub fn handler() {}\n")
    assert {c.status for c in claims if c.relation == DEFINES} == {"hypothesis"}


class _Broken:
    producer = "broken@0"

    def accepts(self, file: GuardedFile) -> bool:
        return True

    def analyze(self, file: GuardedFile) -> list:
        raise RuntimeError("grammar unavailable")

    def limits(self, file: GuardedFile) -> list[str]:
        return []


def test_a_failing_analyzer_is_recorded_and_does_not_stop_the_index(settings, make_repo):
    root = write_repo(make_repo("broken"), {"a.py": "def f():\n    pass\n"}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            summary = index_project(project, store, analyzers=[_Broken(), CodeAnalyzer()])
            (entry,) = store.files()
    assert summary.claims["fact"] == 1
    assert entry.analyzers == CodeAnalyzer.producer
    assert entry.detail == "broken@0 failed: RuntimeError"


def test_claims_name_a_commit_only_when_the_tree_is_clean(settings, make_repo):
    root = write_repo(make_repo("dirty"), {"a.py": "def f():\n    pass\n"})
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-qm", "init"], check=True)
    (root / "a.py").write_text("def f():\n    pass\n\n\ndef g():\n    pass\n")
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            summary = index_project(project, store)
            stored = store.claims()
    assert summary.git_commit is not None and summary.uncommitted_changes is True
    assert all(claim.git_commit is None for claim in stored)


def test_the_fact_check_rejects_a_wrong_import_target(settings, make_repo):
    root = write_repo(
        make_repo("wrong"), {"v.ts": 'import react from "@vitejs/plugin-react-swc"\n'}, git=False
    )
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            assert all(check.correct for check in check_facts(project, store))
            # Forge the bug the strict check found, straight in the store, and make sure it is caught.
            store_path = settings.projects_dir / project.id / "store.sqlite"
    import sqlite3

    with sqlite3.connect(store_path) as db:
        db.execute("UPDATE claims SET object = 'react' WHERE relation = 'imports'")
    with Registry(settings) as registry, registry.open_store(project) as store:
        assert [check.correct for check in check_facts(project, store)] == [False]


def test_store_files_are_under_the_umbra_home(settings, make_repo):
    root = write_repo(make_repo("home"), {"a.py": "x = 1\n"}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
    assert Path(settings.projects_dir / project.id / "store.sqlite").is_file()


@pytest.mark.parametrize(
    ("rel_path", "text", "expected"),
    [
        (
            "A.cs",
            '/*\nusing Fake;\n*/\nusing System;\nclass X { string s = @"\nusing Y;\n"; }\n',
            [("System", 4, 4)],
        ),
        ("x.cpp", 'auto s = R"(\n#include "x.h"\n)";\n#include <vector>\n', [("vector", 4, 4)]),
        ("m.kt", 'package p\nimport a.b.C\nval s = """\nimport x.y\n"""\n', [("a.b.C", 2, 2)]),
        (
            "r.rb",
            '=begin\nrequire "fake"\n=end\nrequire "json"\nx = <<~T\nrequire "h"\nT\n',
            [("json", 4, 4)],
        ),
        (
            "app.ex",
            "defmodule App do\n  alias Shop.{Order, User}\nend\n",
            [("Shop.Order", 2, 2), ("Shop.User", 2, 2)],
        ),
        ("App.java", "import java.util.Map\n    .Entry;\nclass App {}\n", [("java.util.Map.Entry", 1, 2)]),
    ],
)
def test_imports_inside_comments_or_strings_are_ignored_and_groups_expand(
    make_repo, rel_path, text, expected
):
    imports = [
        (c.object, c.line_start, c.line_end)
        for c in analyze(make_repo, rel_path, text)
        if c.relation == IMPORTS
    ]
    assert imports == expected

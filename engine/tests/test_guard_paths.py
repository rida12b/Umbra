from pathlib import Path

import pytest
from secret_fixtures import FILES, GH, link_dir, listed, write_repo

from umbra_engine.guard import (
    EXCLUDED_OUTSIDE,
    EXCLUDED_SENSITIVE,
    EXCLUDED_UMBRAIGNORE,
    SECRET_IN_PATH,
    SecretGuard,
    Skipped,
)


@pytest.fixture
def repo(make_repo) -> Path:
    return write_repo(make_repo("planted"), FILES)


def test_inventory_follows_git_and_ignore_rules(repo):
    files = listed(repo)
    assert "debug.log" not in files, "gitignored files are not part of the Project"
    assert {"src/config.py", ".env", "keys/id_rsa", "private/notes.md", ".env.example"} <= set(files)


def test_non_git_folder_honours_root_and_nested_gitignore(make_repo):
    files = {
        "a.py": "x\n",
        "b.log": "x\n",
        ".gitignore": "*.log\n",
        "sub/.gitignore": "local_*.txt\n",
        "sub/local_only.txt": "x\n",
        "sub/b.py": "x\n",
    }
    root = write_repo(make_repo("plain"), files, git=False)
    assert listed(root) == [".gitignore", "a.py", "sub/.gitignore", "sub/b.py"]


@pytest.mark.parametrize(
    ("rel_path", "reason"),
    [
        (".env", EXCLUDED_SENSITIVE),
        ("keys/id_rsa", EXCLUDED_SENSITIVE),
        ("private/notes.md", EXCLUDED_UMBRAIGNORE),
    ],
)
def test_off_limits_files_are_never_read(repo, rel_path, reason):
    result = SecretGuard(repo).read(rel_path)
    assert isinstance(result, Skipped)
    assert result.reason == reason


@pytest.mark.parametrize(
    "rel_path",
    [
        ".ENV",
        "keys/ID_RSA",
        "certs/Server.PEM",
        "config/Credentials.json",
        "keys/server.ppk",
        ".htpasswd",
        ".s3cfg",
        ".kube/config",
        ".envrc",
    ],
)
def test_credential_files_are_excluded_whatever_the_case(make_repo, rel_path):
    root = write_repo(make_repo("credfiles"), {rel_path: "x\n"}, git=False)
    verdict = SecretGuard(root).check(rel_path)
    assert verdict is not None and verdict.reason == EXCLUDED_SENSITIVE


def test_umbraignore_matches_whatever_the_case(make_repo):
    root = write_repo(
        make_repo("ignorecase"), {".umbraignore": "Secrets/\n", "secrets/a.md": "x\n"}, git=False
    )
    assert SecretGuard(root).check("secrets/a.md") == Skipped("secrets/a.md", EXCLUDED_UMBRAIGNORE)


def test_files_reached_through_a_link_outside_the_project_are_excluded(make_repo):
    outside = make_repo("outside")
    (outside / "leak.py").write_text("SECRET = 1\n")
    root = make_repo("linked")
    link_dir(root / "vendor", outside)
    assert SecretGuard(root).check("vendor/leak.py") == Skipped("vendor/leak.py", EXCLUDED_OUTSIDE)


def test_a_link_inside_the_project_to_a_sensitive_file_is_excluded(make_repo):
    root = write_repo(make_repo("innerlink"), {"real/.aws/credentials": "x\n"}, git=False)
    link_dir(root / "docs", root / "real" / ".aws")
    verdict = SecretGuard(root).check("docs/credentials")
    assert verdict is not None and verdict.reason == EXCLUDED_SENSITIVE


def test_a_secret_in_a_file_name_is_redacted_in_the_listing(make_repo):
    root = write_repo(make_repo("named"), {f"logs/{GH}.txt": "x\n"}, git=False)
    (result,) = SecretGuard(root).files()
    assert isinstance(result, Skipped)
    assert (result.reason, result.detail) == (EXCLUDED_SENSITIVE, SECRET_IN_PATH)
    assert GH not in result.rel_path


def test_a_project_inside_a_workspace_that_ignores_it_is_still_listed(make_repo):
    """A workspace repository ignoring `projects/` must not hide a Project kept there; the Project's
    own `.gitignore` still applies."""
    workspace = write_repo(make_repo("workspace"), {".gitignore": "projects/\n", "notes.md": "x\n"})
    project = workspace / "projects" / "app"
    write_repo(
        project, {"main.py": "x = 1\n", ".gitignore": "build/\n", "build/out.py": "y = 2\n"}, git=False
    )
    assert listed(project) == [".gitignore", "main.py"]

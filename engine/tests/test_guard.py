import subprocess
import sys
from pathlib import Path

import pytest

from umbra_engine.guard import (
    BINARY,
    EXCLUDED_OUTSIDE,
    EXCLUDED_SENSITIVE,
    EXCLUDED_UMBRAIGNORE,
    TOO_LARGE,
    UNREADABLE,
    GuardedFile,
    SecretGuard,
    Skipped,
)
from umbra_engine.guard.content import default_rules
from umbra_engine.indexer import index_project
from umbra_engine.project_files import list_files
from umbra_engine.registry import Registry

ANTHROPIC_KEY = "sk" + "-ant-api03-" + "aB3dE5fG7h" * 9 + "J9k" + "AA"
PEM_BODY = "MIIEowIBAAKCAQEA7Yq3k9Zr2LmPq8XvT4bN6cW1dF0gH5jK3sR7uV9yE2iO4pA8"

# Every value here is fake but shaped like a real credential; none may ever reach the store.
# Prefixes are joined at runtime so that no complete credential-shaped literal sits in the repository.
PLANTED = {
    "aws": "AK" + "IAZ7VQ3XK2LMNP4RST",
    "github": "gh" + "p_R8mQ2vX9kL4tB7nW1zC5yH3jF6dS0aP2eG8u",
    "stripe": "sk" + "_live_51Hq8ZtLm4Rv7Xc2Bn9Wd3Kp6",
    "anthropic": ANTHROPIC_KEY,
    "password": "q7Lr$9vZ!m2KxP4tW8",
    "url_password": "Zr9!kQ2vLm7xTp4w",
    "compose_password": "Pq4vZ8mL2xKr9tW7",
    "pem": PEM_BODY,
    "env_file": "envonly_Hv7Lq2Zx9Mk4Tp8W",
    "ssh_key": "sshonly_Ns3Kd8Wq1Zp6Lx4V",
    "umbraignored": "ignoredonly_Rt5Jm9Qz2Wx7Kp3",
    "gitignored": "logonly_Bx6Nv1Qm8Zt3Lk7W",
}

FILES = {
    "src/config.py": (
        f'AWS_ACCESS_KEY_ID = "{PLANTED["aws"]}"\n'
        f'GITHUB_TOKEN = "{PLANTED["github"]}"\n'
        f'stripe.api_key = "{PLANTED["stripe"]}"\n'
        f'ANTHROPIC_API_KEY = "{PLANTED["anthropic"]}"\n'
        f'DB_PASSWORD = "{PLANTED["password"]}"\n'
        f'DATABASE_URL = "postgresql://admin:{PLANTED["url_password"]}@db.internal:5432/app"\n'
        "def connect():\n    return DATABASE_URL\n"
    ),
    "compose.yml": (
        f"services:\n  db:\n    environment:\n      POSTGRES_PASSWORD: {PLANTED['compose_password']}\n"
    ),
    "deploy/notes.txt": (
        f"-----BEGIN RSA PRIVATE KEY-----\n{PEM_BODY}\n{PEM_BODY}\n-----END RSA PRIVATE KEY-----\n"
    ),
    ".env": f"API_TOKEN={PLANTED['env_file']}\n",
    "keys/id_rsa": f"{PLANTED['ssh_key']}\n",
    "private/notes.md": f"{PLANTED['umbraignored']}\n",
    "debug.log": f"{PLANTED['gitignored']}\n",
    ".env.example": "API_TOKEN=\nPOSTGRES_PASSWORD=changethis\n",
    ".gitignore": "*.log\n",
    ".umbraignore": "private/\n",
    "README.md": "# Shop\nA small app.\n",
}


def write_repo(root: Path, files: dict[str, str], git: bool = True) -> Path:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


@pytest.fixture
def repo(make_repo) -> Path:
    return write_repo(make_repo("planted"), FILES)


def test_inventory_follows_git_and_ignore_rules(repo):
    files = list_files(repo)
    assert "debug.log" not in files, "gitignored files are not part of the Project"
    assert {"src/config.py", ".env", "keys/id_rsa", "private/notes.md", ".env.example"} <= set(files)


def test_non_git_folder_honours_root_gitignore(make_repo):
    root = write_repo(
        make_repo("plain"), {"a.py": "x = 1\n", "b.log": "x\n", ".gitignore": "*.log\n"}, git=False
    )
    assert list_files(root) == [".gitignore", "a.py"]


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


@pytest.mark.parametrize("rel_path", ["src/config.py", "compose.yml", "deploy/notes.txt"])
def test_readable_files_come_back_with_every_secret_redacted(repo, rel_path):
    raw = (repo / rel_path).read_text(encoding="utf-8")
    result = SecretGuard(repo).read(rel_path)

    assert isinstance(result, GuardedFile)
    assert result.redacted, "the planted secrets must be detected"
    for value in PLANTED.values():
        assert value not in result.text
    assert result.text.count("\n") == raw.count("\n"), "line numbers must stay valid for evidence spans"
    assert len(result.text) == len(raw)


def test_code_and_templates_are_not_redacted(repo):
    config = SecretGuard(repo).read("src/config.py")
    assert isinstance(config, GuardedFile)
    assert "def connect():\n    return DATABASE_URL" in config.text

    template = SecretGuard(repo).read(".env.example")
    assert isinstance(template, GuardedFile)
    assert template.text == FILES[".env.example"]


def test_binary_and_oversized_files_are_skipped(make_repo):
    root = make_repo("blobs")
    (root / "image.bin").write_bytes(b"\x89PNG\x00\x00data")
    (root / "huge.txt").write_text("a" * 2_000_001)
    guard = SecretGuard(root)
    assert guard.read("image.bin") == Skipped("image.bin", BINARY)
    assert guard.read("huge.txt") == Skipped("huge.txt", TOO_LARGE)


@pytest.mark.parametrize(
    ("rel_path", "line"),
    [
        ("app/settings.py", "token = request.headers.authorization"),
        ("compose.yml", "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"),
        ("app/models.py", "if password == user.password_hash: return token"),
    ],
)
def test_ordinary_code_and_placeholders_are_not_flagged(rel_path, line):
    assert default_rules().scan(rel_path, line) == []


def test_store_never_contains_a_planted_secret(settings, repo):
    with Registry(settings) as registry:
        project, _ = registry.add(repo)
        with registry.open_store(project) as store:
            summary = index_project(project, store)
            inventory = {entry.path: entry for entry in store.files()}

    assert summary.skipped == {EXCLUDED_SENSITIVE: 2, EXCLUDED_UMBRAIGNORE: 1}
    assert inventory[".env"].reason == EXCLUDED_SENSITIVE
    assert inventory["private/notes.md"].reason == EXCLUDED_UMBRAIGNORE
    assert inventory["src/config.py"].state == "readable"

    store_bytes = b"".join(p.read_bytes() for p in (settings.projects_dir / project.id).iterdir())
    for value in PLANTED.values():
        assert value.encode() not in store_bytes


def _link_dir(link: Path, target: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


def test_files_reached_through_a_link_outside_the_project_are_excluded(make_repo):
    outside = make_repo("outside")
    (outside / "leak.py").write_text("SECRET = 1\n")
    root = make_repo("linked")
    _link_dir(root / "vendor", outside)

    assert SecretGuard(root).check("vendor/leak.py") == Skipped("vendor/leak.py", EXCLUDED_OUTSIDE)


def test_index_through_api_and_cli(client, auth, repo, settings, monkeypatch, capsys):
    project = client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()
    response = client.post(f"/v1/projects/{project['id']}/index", headers=auth)
    assert response.status_code == 200
    assert response.json()["skipped"] == {EXCLUDED_SENSITIVE: 2, EXCLUDED_UMBRAIGNORE: 1}
    assert client.post("/v1/projects/unknown-0000/index", headers=auth).status_code == 404

    from umbra_engine import cli

    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["index", project["id"]]) == 0
    assert "readable" in capsys.readouterr().out


def test_scanning_stays_linear_on_hash_heavy_files():
    """A real requirements.txt of 300 KB took 120 s with a backtracking regex engine."""
    import time

    line = "    --hash=sha256:" + "0123456789abcdef" * 4 + " \\n"
    text = "cohere==5.13.0 \\n" + line * 4000
    start = time.perf_counter()
    default_rules().scan("requirements.txt", text)
    assert time.perf_counter() - start < 2


@pytest.mark.parametrize("rel_path", [".ENV", "keys/ID_RSA", "certs/Server.PEM", "config/Credentials.json"])
def test_sensitive_paths_match_whatever_the_case(make_repo, rel_path):
    root = write_repo(make_repo("cases"), {rel_path: "x\n"}, git=False)
    verdict = SecretGuard(root).check(rel_path)
    assert verdict is not None and verdict.reason == EXCLUDED_SENSITIVE


def test_umbraignore_matches_whatever_the_case(make_repo):
    root = write_repo(
        make_repo("ignorecase"), {".umbraignore": "Secrets/\n", "secrets/a.md": "x\n"}, git=False
    )
    assert SecretGuard(root).check("secrets/a.md") == Skipped("secrets/a.md", EXCLUDED_UMBRAIGNORE)


def test_a_link_inside_the_project_to_a_sensitive_file_is_excluded(make_repo):
    root = write_repo(make_repo("innerlink"), {"real/.aws/credentials": "x\n"}, git=False)
    _link_dir(root / "docs", root / "real" / ".aws")
    verdict = SecretGuard(root).check("docs/credentials")
    assert verdict is not None and verdict.reason == EXCLUDED_SENSITIVE


def test_templates_keep_placeholders_but_lose_real_values(make_repo):
    template = (
        "API_TOKEN=\nDB_PASSWORD=hunter2\nPORT=8000\nSECRET_KEY=changethis\nDB_URL=postgres://u:pw@host/db\n"
    )
    root = write_repo(make_repo("template"), {".env.example": template}, git=False)
    result = SecretGuard(root).read(".env.example")
    assert isinstance(result, GuardedFile)
    assert (
        result.text
        == "API_TOKEN=\nDB_PASSWORD=*******\nPORT=8000\nSECRET_KEY=changethis\nDB_URL=postgres://u:**@host/db\n"
    )


def test_files_on_gitleaks_skip_paths_are_still_scanned(make_repo):
    secret = PLANTED["github"]
    root = write_repo(make_repo("lockfiles"), {"package-lock.json": f'{{"token": "{secret}"}}\n'}, git=False)
    result = SecretGuard(root).read("package-lock.json")
    assert isinstance(result, GuardedFile) and secret not in result.text


def test_redaction_offsets_survive_multibyte_text_and_crlf(make_repo):
    raw = f'# café ☕ déjà\r\nTOKEN = "{PLANTED["github"]}"\r\nprint("ok")\r\n'
    root = write_repo(make_repo("offsets"), {"app.py": raw}, git=False)
    result = SecretGuard(root).read("app.py")
    assert isinstance(result, GuardedFile)
    assert result.text == raw.replace(PLANTED["github"], "*" * len(PLANTED["github"]))


def test_unreadable_file_is_skipped_not_raised(make_repo, monkeypatch):
    root = write_repo(make_repo("locked"), {"a.py": "x = 1\n"}, git=False)

    def deny(_self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", deny)
    assert SecretGuard(root).read("a.py") == Skipped("a.py", UNREADABLE, "PermissionError")


GH = PLANTED["github"]
LIVE = PLANTED["stripe"]


@pytest.mark.parametrize(
    ("rel_path", "content", "secret"),
    [
        (
            "notebook.ipynb",
            f'{{"source": ["password = \\"{PLANTED["password"]}\\"\n"]}}',
            PLANTED["password"],
        ),
        ("data.json", f'{{"cfg": "stripe_key = \\"{LIVE}\\""}}', LIVE),
        ("config.yaml", "db:\r\n  db_passwd: hX7pQm2Lz9Kw\r\n  port: 5432\r\n", "hX7pQm2Lz9Kw"),
        ("Dockerfile", "FROM python:3.13\nENV DB_PASSWORD=hX7pQm2Lz9Kw\n", "hX7pQm2Lz9Kw"),
    ],
)
def test_secrets_in_escaped_json_crlf_and_dockerfiles_are_redacted(make_repo, rel_path, content, secret):
    root = write_repo(make_repo("shapes"), {rel_path: content}, git=False)
    result = SecretGuard(root).read(rel_path)
    assert isinstance(result, GuardedFile)
    assert secret not in result.text


@pytest.mark.parametrize("rel_path", ["keys/server.ppk", ".htpasswd", ".s3cfg", ".kube/config", ".envrc"])
def test_more_credential_files_are_excluded(make_repo, rel_path):
    root = write_repo(make_repo("credfiles"), {rel_path: "x\n"}, git=False)
    verdict = SecretGuard(root).check(rel_path)
    assert verdict is not None and verdict.reason == EXCLUDED_SENSITIVE


def test_a_secret_in_a_file_name_is_never_stored(settings, make_repo):
    root = write_repo(make_repo("named"), {f"logs/{GH}.txt": "x\n", "a.py": "x = 1\n"}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            skipped = [e for e in store.files() if e.state == "skipped"]
    assert [(e.reason, e.detail) for e in skipped] == [(EXCLUDED_SENSITIVE, "secret in path")]
    store_bytes = b"".join(p.read_bytes() for p in (settings.projects_dir / project.id).iterdir())
    assert GH.encode() not in store_bytes


def test_utf16_files_are_read_and_redacted_not_dropped_as_binary(make_repo):
    root = make_repo("utf16")
    (root / "legacy.py").write_bytes(f'TOKEN = "{GH}"\n'.encode("utf-16"))
    result = SecretGuard(root).read("legacy.py")
    assert isinstance(result, GuardedFile)
    assert "TOKEN" in result.text and GH not in result.text


def test_nested_gitignore_is_honoured_outside_git(make_repo):
    files = {"a.py": "x\n", "sub/.gitignore": "local_*.txt\n", "sub/local_only.txt": "x\n", "sub/b.py": "x\n"}
    root = write_repo(make_repo("nested"), files, git=False)
    assert list_files(root) == ["a.py", "sub/.gitignore", "sub/b.py"]


@pytest.mark.parametrize(
    "line",
    [
        'password_field = "password_confirmation"',
        'TOKEN_URL = "https://auth.example.com/oauth/token"',
        'secret_name = "projects/acme/secrets/db"',
        'PasswordInput.displayName = "PasswordInput"',
    ],
)
def test_names_urls_and_paths_are_not_mistaken_for_secrets(line):
    assert default_rules().scan("app/settings.py", line) == []

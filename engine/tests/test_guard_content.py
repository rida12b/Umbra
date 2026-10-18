import time
from pathlib import Path

import pytest
from secret_fixtures import FILES, GH, PLANTED, write_repo

from umbra_engine.guard import BINARY, TOO_LARGE, UNREADABLE, GuardedFile, SecretGuard, Skipped
from umbra_engine.guard.content import default_rules

LIVE = PLANTED["stripe"]


@pytest.fixture
def repo(make_repo) -> Path:
    return write_repo(make_repo("planted"), FILES)


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


def test_templates_keep_placeholders_but_lose_real_values(make_repo):
    template = (
        "API_TOKEN=\nDB_PASSWORD=hunter2\nPORT=8000\nSECRET_KEY=changethis\nDB_URL=postgres://u:pw@host/db\n"
    )
    root = write_repo(make_repo("template"), {".env.example": template}, git=False)
    result = SecretGuard(root).read(".env.example")
    assert isinstance(result, GuardedFile)
    expected = (
        "API_TOKEN=\nDB_PASSWORD=*******\nPORT=8000\nSECRET_KEY=changethis\nDB_URL=postgres://u:**@host/db\n"
    )
    assert result.text == expected


@pytest.mark.parametrize(
    ("rel_path", "content", "secret"),
    [
        (
            "notebook.ipynb",
            f'{{"source": ["password = \\"{PLANTED["password"]}\\"\\n"]}}',
            PLANTED["password"],
        ),
        ("data.json", f'{{"cfg": "stripe_key = \\"{LIVE}\\""}}', LIVE),
        ("config.yaml", "db:\r\n  db_passwd: hX7pQm2Lz9Kw\r\n  port: 5432\r\n", "hX7pQm2Lz9Kw"),
        ("Dockerfile", "FROM python:3.13\nENV DB_PASSWORD=hX7pQm2Lz9Kw\n", "hX7pQm2Lz9Kw"),
        ("package-lock.json", f'{{"token": "{GH}"}}\n', GH),
        ("app/aws.py", 'aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY"\n', "wJalrXUtnFEMI/K7MDENG"),
    ],
)
def test_secrets_in_every_shape_are_redacted(make_repo, rel_path, content, secret):
    root = write_repo(make_repo("shapes"), {rel_path: content}, git=False)
    result = SecretGuard(root).read(rel_path)
    assert isinstance(result, GuardedFile)
    assert secret not in result.text


@pytest.mark.parametrize(
    ("rel_path", "line"),
    [
        ("app/settings.py", "token = request.headers.authorization"),
        ("compose.yml", "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"),
        ("app/models.py", "if password == user.password_hash: return token"),
        ("app/settings.py", 'password_field = "password_confirmation"'),
        ("app/settings.py", 'TOKEN_URL = "https://auth.example.com/oauth/token"'),
        ("app/settings.py", 'secret_name = "projects/acme/secrets/db"'),
        ("app/ui.tsx", 'PasswordInput.displayName = "PasswordInput"'),
    ],
)
def test_names_urls_paths_and_placeholders_are_not_flagged(rel_path, line):
    assert default_rules().scan(rel_path, line) == []


def test_redaction_offsets_survive_multibyte_text_and_crlf(make_repo):
    raw = f'# café ☕ déjà\r\nTOKEN = "{GH}"\r\nprint("ok")\r\n'
    root = write_repo(make_repo("offsets"), {"app.py": raw}, git=False)
    result = SecretGuard(root).read("app.py")
    assert isinstance(result, GuardedFile)
    assert result.text == raw.replace(GH, "*" * len(GH))


def test_utf16_files_are_read_and_redacted_not_dropped_as_binary(make_repo):
    root = make_repo("utf16")
    (root / "legacy.py").write_bytes(f'TOKEN = "{GH}"\n'.encode("utf-16"))
    result = SecretGuard(root).read("legacy.py")
    assert isinstance(result, GuardedFile)
    assert "TOKEN" in result.text and GH not in result.text


def test_binary_and_oversized_files_are_skipped(make_repo):
    root = make_repo("blobs")
    (root / "image.bin").write_bytes(b"\x89PNG\x00\x00data")
    (root / "huge.txt").write_text("a" * 2_000_001)
    guard = SecretGuard(root)
    assert guard.read("image.bin") == Skipped("image.bin", BINARY)
    assert guard.read("huge.txt") == Skipped("huge.txt", TOO_LARGE)


def test_unreadable_file_is_skipped_not_raised(make_repo, monkeypatch):
    root = write_repo(make_repo("locked"), {"a.py": "x = 1\n"}, git=False)

    def deny(_self: Path) -> bytes:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", deny)
    assert SecretGuard(root).read("a.py") == Skipped("a.py", UNREADABLE, "PermissionError")


def test_scanning_stays_linear_on_hash_heavy_files():
    """A real requirements.txt of 300 KB took 120 s with a backtracking regex engine."""
    line = "    --hash=sha256:" + "0123456789abcdef" * 4 + " \\\n"
    text = "cohere==5.13.0 \\\n" + line * 4000
    start = time.perf_counter()
    default_rules().scan("requirements.txt", text)
    assert time.perf_counter() - start < 2

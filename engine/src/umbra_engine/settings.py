"""Where the engine keeps its data, and the local API binding."""

import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

API_HOST = "127.0.0.1"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
DEFAULT_PORT = 7811
TOKEN_FILE = "token"
TOKEN_READ_RETRIES = 20


class TokenFileError(RuntimeError):
    """The token file exists but holds no usable token."""


@dataclass(frozen=True)
class Settings:
    home: Path
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls) -> "Settings":
        home = Path(os.environ.get("UMBRA_HOME") or Path.home() / ".umbra")
        port = int(os.environ.get("UMBRA_PORT") or DEFAULT_PORT)
        return cls(home=Path(os.path.realpath(home)), port=port)

    @property
    def projects_dir(self) -> Path:
        return self.home / "projects"

    @property
    def registry_path(self) -> Path:
        return self.home / "registry.sqlite"


def load_or_create_token(settings: Settings) -> str:
    """Return the local API token, creating it atomically on first use.

    The file is created owner-only (mode 0600) on POSIX. On Windows the mode is ignored and the file
    is as private as its folder: keep UMBRA_HOME inside the user profile.
    """
    settings.home.mkdir(parents=True, exist_ok=True)
    path = settings.home / TOKEN_FILE
    if not path.exists():
        _create_token_file(path)
    for _ in range(TOKEN_READ_RETRIES):
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
        time.sleep(0.05)
    raise TokenFileError(f"empty token file: {path} (delete it to generate a new token)")


def _create_token_file(path: Path) -> None:
    staging = path.with_name(f".{TOKEN_FILE}.{os.getpid()}.{secrets.token_hex(4)}")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(secrets.token_urlsafe(32))
    try:
        os.link(staging, path)
    except FileExistsError:
        pass
    except OSError:
        _create_without_hard_link(path, staging.read_text(encoding="utf-8"))
    finally:
        staging.unlink()


def _create_without_hard_link(path: Path, token: str) -> None:
    """For filesystems without hard links (FAT, exFAT, some shares). Readers retry while it is empty."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(token)

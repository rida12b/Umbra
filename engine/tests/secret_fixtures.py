"""Fake credentials and fixture repositories shared by the Secret Guard tests."""

import subprocess
import sys
from pathlib import Path

from umbra_engine.guard import SecretGuard

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
GH = PLANTED["github"]

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
    """Write files as raw bytes (no newline translation), optionally as a git repository."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def link_dir(link: Path, target: Path) -> None:
    """Directory link without admin rights: a junction on Windows, a symlink elsewhere."""
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


def listed(root: Path) -> list[str]:
    """Paths the guard enumerates for a Project, as stored (secrets in names redacted)."""
    return [result.rel_path for result in SecretGuard(root).files()]


def store_bytes(directory: Path) -> bytes:
    return b"".join(p.read_bytes() for p in directory.iterdir() if p.is_file())

"""Path rules: files that are never read, whatever they contain."""

from pathlib import Path

import pathspec

UMBRAIGNORE = ".umbraignore"

# gitignore-style patterns, matched against the path relative to the Project root.
SENSITIVE_PATTERNS = (
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "*.kdbx",
    "*.ovpn",
    "*.tfstate",
    "*.tfstate.*",
    "*.tfvars",
    "id_rsa*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".pgpass",
    ".git-credentials",
    ".dockercfg",
    ".docker/config.json",
    ".aws/credentials",
    "credentials",
    "credentials.json",
    "*credentials*.json",
    "service-account*.json",
    "secrets.json",
    "secrets.toml",
    "secrets.yml",
    "secrets.yaml",
    "*.secret",
    "*.secrets",
    "*.ppk",
    ".htpasswd",
    ".s3cfg",
    ".envrc",
    ".kube/config",
    "kubeconfig",
    "*.kubeconfig",
)

# Templates are read (with content scanning), because they document configuration without values.
TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".tpl")

_sensitive = pathspec.GitIgnoreSpec.from_lines(SENSITIVE_PATTERNS)


def sensitive_reason(rel_path: str) -> str | None:
    """Case-insensitive on purpose: `.ENV` or `ID_RSA` are the same files on Windows and macOS."""
    lowered = rel_path.lower()
    if lowered.endswith(TEMPLATE_SUFFIXES):
        return None
    return "sensitive path" if _sensitive.match_file(lowered) else None


def load_umbraignore(root: Path) -> pathspec.GitIgnoreSpec:
    """Lower-cased: callers match lower-cased paths, so `Secrets/` also hides `secrets/`."""
    file = root / UMBRAIGNORE
    lines = file.read_text(encoding="utf-8", errors="replace").splitlines() if file.is_file() else []
    return pathspec.GitIgnoreSpec.from_lines(line.lower() for line in lines)

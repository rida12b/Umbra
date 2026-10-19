"""Package manifests: the dependencies a Project declares (package.json, pyproject.toml,
requirements*.txt, go.mod, Cargo.toml), each with the line that declares it.

Declarations only: listing `fastapi` says the Project asks for it, not which version is installed.
"""

import json
import posixpath
import re
import tomllib
from collections.abc import Iterable

from umbra_engine.claims import REQUIRES, Claim
from umbra_engine.guard import GuardedFile

NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_GO_REQUIRE = re.compile(r"^\s*(?:require\s+)?([\w.\-]+(?:/[\w.\-~]+)+)\s+v\S+")


def package(ecosystem: str, name: str) -> str:
    return f"package:{ecosystem}/{name.lower() if ecosystem == 'pypi' else name}"


class ManifestAnalyzer:
    producer = "manifests@1.0"

    def accepts(self, file: GuardedFile) -> bool:
        name = posixpath.basename(file.rel_path).lower()
        return name in ("package.json", "pyproject.toml", "go.mod", "cargo.toml") or (
            name.startswith("requirements") and name.endswith(".txt")
        )

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        name = posixpath.basename(file.rel_path).lower()
        lines = file.text.split("\n")
        if name == "package.json":
            found = _npm(file.text, lines)
        elif name == "pyproject.toml":
            found = _pyproject(file.text, lines)
        elif name == "go.mod":
            found = [
                ("go", m.group(1), i) for i, line in enumerate(lines, 1) if (m := _GO_REQUIRE.match(line))
            ]
        elif name == "cargo.toml":
            found = _cargo(file.text, lines)
        else:
            found = _requirements(lines)
        return [
            Claim(file.rel_path, "module", REQUIRES, package(ecosystem, dep), "package", "fact", line, line)
            for ecosystem, dep, line in found
        ]

    def limits(self, file: GuardedFile) -> list[str]:
        return []


def _line_of(lines: list[str], needle: str, after: int = 0) -> int | None:
    return next((i for i, line in enumerate(lines, 1) if i > after and needle in line), None)


def _npm(text: str, lines: list[str]) -> list[tuple[str, str, int]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    found = []
    for section in NPM_SECTIONS:
        names = data.get(section) if isinstance(data, dict) else None
        start = _line_of(lines, f'"{section}"')
        if not isinstance(names, dict) or start is None:
            continue
        for dep in names:
            line = _line_of(lines, f'"{dep}"', start)
            if line is not None:
                found.append(("npm", dep, line))
    return found


def _pyproject(text: str, lines: list[str]) -> list[tuple[str, str, int]]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs += extra
    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    specs += [name for name in poetry if name.lower() != "python"]
    start = _line_of(lines, "dependencies") or 0
    found = []
    for spec in (s for s in specs if isinstance(s, str)):
        match = _REQUIREMENT.match(spec)
        line = _line_of(lines, spec, start - 1) or (
            _line_of(lines, match.group(1), start - 1) if match else None
        )
        if match and line is not None:
            found.append(("pypi", match.group(1), line))
    return found


def _requirements(lines: list[str]) -> list[tuple[str, str, int]]:
    found = []
    for number, line in enumerate(lines, 1):
        stripped = line.split("#", 1)[0].strip()
        if not stripped or stripped.startswith("-"):
            continue
        match = _REQUIREMENT.match(stripped)
        if match:
            found.append(("pypi", match.group(1), number))
    return found


def _cargo(text: str, lines: list[str]) -> list[tuple[str, str, int]]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    found = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        start = _line_of(lines, f"[{section}]")
        for dep in data.get(section, {}):
            line = _line_of(lines, dep, start or 0)
            if line is not None:
                found.append(("cargo", dep, line))
    return found

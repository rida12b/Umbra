"""Package manifests: the dependencies a Project declares (package.json, pyproject.toml,
requirements*.txt, go.mod, Cargo.toml), each with the line that declares it.

The cited line is where the name is declared, in the right section, matched as a whole name
(`serde` is not `serde_json`). Declarations only: listing `fastapi` says the Project asks for it,
not which version is installed.
"""

import json
import posixpath
import re
import tomllib
from collections.abc import Iterable

from umbra_engine.claims import REQUIRES, Claim
from umbra_engine.guard import GuardedFile

NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
CARGO_SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")
_PEP508_NAME = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?=$|[\[<>=!~;@,(\s])")
_GO_REQUIREMENT = re.compile(r"^\s*([\w.\-]+(?:/[\w.\-~]+)+)\s+v\S+")
_HEADER = re.compile(r"(?m)^[ \t]*\[")

Found = list[tuple[str, str, int]]  # (ecosystem, name as written, line)


def package(ecosystem: str, name: str) -> str:
    return f"package:{ecosystem}/{name}"


class ManifestAnalyzer:
    producer = "manifests@1.2"

    def accepts(self, file: GuardedFile) -> bool:
        name = posixpath.basename(file.rel_path).lower()
        return name in ("package.json", "pyproject.toml", "go.mod", "cargo.toml") or (
            name.startswith("requirements") and name.endswith(".txt")
        )

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        name = posixpath.basename(file.rel_path).lower()
        readers = {"package.json": _npm, "pyproject.toml": _pyproject, "go.mod": _go, "cargo.toml": _cargo}
        found = readers.get(name, _requirements)(file.text)
        return [
            Claim(file.rel_path, "module", REQUIRES, package(ecosystem, dep), "package", "fact", line, line)
            for ecosystem, dep, line in found
        ]

    def limits(self, file: GuardedFile) -> list[str]:
        if not posixpath.basename(file.rel_path).lower().startswith("requirements"):
            return []
        options = [line for line in file.text.split("\n") if line.strip().startswith(("-e", "--editable"))]
        return ["editable installs (-e) are not read as dependencies"] if options else []


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def toml_section(text: str, header: str) -> tuple[int, int] | None:
    """Character range of a TOML table: from its `[header]` line to the next header."""
    match = re.search(rf"(?m)^[ \t]*\[{re.escape(header)}\][ \t]*(#.*)?\r?$", text)  # CRLF files too
    if not match:
        return None
    following = _HEADER.search(text, match.end())
    return match.start(), following.start() if following else len(text)


def toml_key_line(text: str, span: tuple[int, int], name: str) -> int | None:
    """Line of `name = ...` (bare or quoted key) inside a TOML table."""
    found = re.compile(rf"(?m)^[ \t]*[\"']?{re.escape(name)}[\"']?[ \t]*=").search(text, span[0], span[1])
    return line_of(text, found.start()) if found else None


def _npm(text: str) -> Found:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    found: Found = []
    for section in NPM_SECTIONS:
        names = data.get(section) if isinstance(data, dict) else None
        start = re.search(rf'"{section}"\s*:\s*\{{', text)
        if not isinstance(names, dict) or start is None:
            continue
        for dep in names:
            key = re.compile(rf'"{re.escape(dep)}"\s*:').search(text, start.end())
            if key:
                found.append(("npm", dep, line_of(text, key.start())))
    return found


def _pyproject(text: str) -> Found:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    found: Found = []
    project = data.get("project", {})
    project_span = toml_section(text, "project")
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs += extra
    for spec in (s for s in specs if isinstance(s, str)):
        name = _PEP508_NAME.match(spec)
        quoted = re.compile(rf"[\"']{re.escape(spec)}[\"']").search(
            text, project_span[0] if project_span else 0
        )
        if name and quoted:
            found.append(("pypi", name.group(1), line_of(text, quoted.start())))
    poetry = data.get("tool", {}).get("poetry", {})
    tables = {"tool.poetry.dependencies": poetry.get("dependencies", {})}
    tables["tool.poetry.dev-dependencies"] = poetry.get("dev-dependencies", {})
    for group, content in poetry.get("group", {}).items():
        tables[f"tool.poetry.group.{group}.dependencies"] = content.get("dependencies", {})
    for header, names in tables.items():
        span = toml_section(text, header)
        for dep in (n for n in names if n.lower() != "python"):
            line = toml_key_line(text, span, dep) if span else None
            if line is not None:
                found.append(("pypi", dep, line))
    return found


def _requirements(text: str) -> Found:
    found: Found = []
    for number, line in enumerate(text.split("\n"), 1):
        stripped = line.split(" #", 1)[0].strip()
        if not stripped or stripped.startswith(("#", "-")) or "://" in stripped.split("@", 1)[0]:
            continue  # options, editable installs, bare URLs: no package name to read
        name = _PEP508_NAME.match(stripped)
        if name:
            found.append(("pypi", name.group(1), number))
    return found


def _go(text: str) -> Found:
    """Only `require` lines and blocks; `replace`, `exclude` and `retract` name no new dependency."""
    found: Found = []
    block = None
    for number, line in enumerate(text.split("\n"), 1):
        stripped = line.split("//", 1)[0].strip()
        if block is not None:
            if stripped == ")":
                block = None
            elif block == "require" and (match := _GO_REQUIREMENT.match(stripped)):
                found.append(("go", match.group(1), number))
            continue
        opening = re.match(r"^(require|replace|exclude|retract)\s*\($", stripped)
        if opening:
            block = opening.group(1)
        elif stripped.startswith("require ") and (match := _GO_REQUIREMENT.match(stripped[8:])):
            found.append(("go", match.group(1), number))
    return found


def _cargo(text: str) -> Found:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    tables = [(section, data.get(section, {})) for section in CARGO_SECTIONS]
    tables.append(("workspace.dependencies", data.get("workspace", {}).get("dependencies", {})))
    for target, content in data.get("target", {}).items():
        quoted = f"target.'{target}'" if "(" in target or "." in target else f"target.{target}"
        tables += [(f"{quoted}.{section}", content.get(section, {})) for section in CARGO_SECTIONS]
    found: Found = []
    for header, names in tables:
        span = toml_section(text, header)
        for dep in names:
            line = toml_key_line(text, span, dep) if span else None
            if line is None:  # `[dependencies.serde]`: the dependency is its own table
                own = toml_section(text, f"{header}.{dep}")
                line = line_of(text, own[0]) if own else None
            if line is not None:
                found.append(("cargo", dep, line))
    return found

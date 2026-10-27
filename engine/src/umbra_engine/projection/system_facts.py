"""The hard signals of a Project, grouped for the Level 0 map: compose services, manifests, signals."""

import posixpath
from collections import defaultdict
from dataclasses import dataclass, field

from umbra_engine.claims import (
    CODE_ROOT,
    DECLARES,
    DEFINES,
    DEPENDS_ON,
    IMPORTS_MODULE,
    REQUIRES,
    SIGNALS,
    USES_IMAGE,
    StoredClaim,
)

# Relations the Level 0 map reads (plus class definitions, loaded apart: see `ProjectStore.claims_of_kind`).
SYSTEM_RELATIONS = (DECLARES, USES_IMAGE, CODE_ROOT, DEPENDS_ON, REQUIRES, SIGNALS, IMPORTS_MODULE)
MANIFESTS = ("pyproject.toml", "package.json", "go.mod", "cargo.toml", "setup.py")
SERVICE_KINDS = {"service", "workload"}


@dataclass
class ComposeService:
    name: str
    declared: list[StoredClaim] = field(default_factory=list)
    image: str = ""
    code_root: str | None = None  # "" is the Project root
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Facts:
    name: str
    files: list[str]
    services: dict[str, ComposeService]
    signals: dict[str, list[StoredClaim]]  # signal name -> claims, in file then line order
    requires: dict[str, list[StoredClaim]]  # manifest directory ("" = root) -> what it asks for
    module_links: list[StoredClaim]
    classes: list[StoredClaim]
    functions: list[StoredClaim] = field(default_factory=list)  # read for the inside of a box only (#105)

    def signal(self, name: str, files: set[str] | None = None) -> list[StoredClaim]:
        found = self.signals.get(name, [])
        return found if files is None else [c for c in found if c.file in files]

    def signals_starting(self, prefix: str, files: set[str] | None = None) -> list[StoredClaim]:
        return [
            c
            for name, claims in self.signals.items()
            if name.startswith(prefix)
            for c in claims
            if files is None or c.file in files
        ]

    def commands(self, files: set[str]) -> list[StoredClaim]:
        """Commands of a CLI group (`@cli.command`); lone `@click.command`s count only if no group has one."""
        found = self.signals_starting("command:", files)
        of_groups = [c for c in found if c.object != "signal:command:click"]
        return of_groups or found

    def manifest_dirs(self) -> list[str]:
        return sorted(
            {posixpath.dirname(f) for f in self.files if posixpath.basename(f).lower() in MANIFESTS}
        )

    def deps(self, directory: str) -> dict[str, StoredClaim]:
        """Package name (lower case) -> the claim that asks for it, for the manifests of this directory."""
        return {c.object.split("/", 1)[1].lower(): c for c in self.requires.get(directory, [])}


def facts_of(name: str, files: list[str], claims: list[StoredClaim], classes: list[StoredClaim]) -> Facts:
    services: dict[str, ComposeService] = {}

    def service(key: str) -> ComposeService:
        short = key.split(":", 1)[1]
        return services.setdefault(short, ComposeService(short))

    signals: dict[str, list[StoredClaim]] = defaultdict(list)
    requires: dict[str, list[StoredClaim]] = defaultdict(list)
    module_links: list[StoredClaim] = []
    for claim in sorted(claims, key=lambda c: (c.file, c.line_start, c.key)):
        if (
            claim.relation == DECLARES
            and claim.object_kind in SERVICE_KINDS
            and claim.object.startswith("service:")
        ):
            service(claim.object).declared.append(claim)
        elif claim.relation == USES_IMAGE and claim.subject.startswith("service:"):
            service(claim.subject).image = service(claim.subject).image or claim.object.removeprefix("image:")
        elif claim.relation == CODE_ROOT and claim.subject.startswith("service:"):
            root = claim.object.removeprefix("dir:")
            service(claim.subject).code_root = "" if root == "." else root
        elif claim.relation == DEPENDS_ON and claim.subject.startswith("service:"):
            service(claim.subject).depends_on.append(claim.object.split(":", 1)[1])
        elif claim.relation == SIGNALS:
            signals[claim.object.removeprefix("signal:")].append(claim)
        elif claim.relation == REQUIRES:
            requires[posixpath.dirname(claim.file)].append(claim)
        elif claim.relation == IMPORTS_MODULE:
            module_links.append(claim)
    classes = [c for c in classes if c.relation == DEFINES]
    return Facts(name, files, services, dict(signals), dict(requires), module_links, classes)


def under(directory: str, path: str) -> bool:
    return directory == "" or path == directory or path.startswith(directory + "/")

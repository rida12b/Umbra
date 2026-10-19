"""The Project as the map needs it: services, files, definitions and links, loaded once from the store."""

import bisect
import posixpath
from collections import defaultdict
from dataclasses import dataclass, field

from umbra_engine.claims import (
    CALLS,
    CODE_ROOT,
    DECLARES,
    DEFINES,
    DEPENDS_ON,
    EXPOSES,
    IMPORTS_MODULE,
    ROUTES_TO,
    TARGETS,
    USES_IMAGE,
    StoredClaim,
)
from umbra_engine.project_store import FileEntry
from umbra_engine.projection.calls import resolve_calls
from umbra_engine.store_schema import LIST_SEPARATOR

# The only relations the map reads (kept small: a large Project holds millions of import Claims).
MAP_RELATIONS = (
    DECLARES,
    USES_IMAGE,
    EXPOSES,
    CODE_ROOT,
    DEFINES,
    IMPORTS_MODULE,
    DEPENDS_ON,
    TARGETS,
    ROUTES_TO,
    CALLS,
)
SERVICE_KINDS = {"service", "workload", "k8s-service", "ingress"}
SERVICE_LINKS = (DEPENDS_ON, TARGETS, ROUTES_TO)
CODE_PRODUCER = "code-"
DOCUMENTS = {".md", ".mdx", ".rst"}


@dataclass
class Service:
    key: str
    label: str
    declared_by: list[StoredClaim] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    code_root: str | None = None
    code_root_status: str = "fact"


@dataclass(frozen=True)
class Definition:
    key: str
    kind: str
    status: str
    file: str
    lines: tuple[int, int]
    claim: str


class ProjectGraph:
    def __init__(self, name: str, files: list[FileEntry], claims: list[StoredClaim]) -> None:
        self.name = name
        # Analysed files, plus documents: no Claims come from them, but they explain the Project.
        self.files = sorted(
            f.path
            for f in files
            if f.state == "readable" and (f.analyzers or posixpath.splitext(f.path)[1].lower() in DOCUMENTS)
        )
        # Files that only declare deployment (compose, Dockerfile, manifests): Evidence of services,
        # not Modules to browse at the Application level.
        self.declaration_files = {
            f.path
            for f in files
            if f.analyzers and not any(a.startswith(CODE_PRODUCER) for a in f.analyzers.split(LIST_SEPARATOR))
        }
        self.services: dict[str, Service] = {}
        self.definitions: dict[str, Definition] = {}
        self.children_of_definition: dict[str, list[str]] = defaultdict(list)
        self.top_definitions: dict[str, list[str]] = defaultdict(list)
        self.module_links: list[StoredClaim] = []
        self.service_links: list[StoredClaim] = []
        self._calls: list[StoredClaim] = []
        for claim in claims:
            self._add(claim)
        self._nest_definitions()
        imported: dict[str, set[str]] = defaultdict(set)
        for link in self.module_links:
            imported[link.subject].add(link.object)
        self.calls = resolve_calls(self._calls, set(self.definitions), imported)
        self.directories = _directories(self.files)

    def _add(self, claim: StoredClaim) -> None:
        if claim.relation == DECLARES and claim.object_kind in SERVICE_KINDS:
            self._service(claim.object).declared_by.append(claim)
        elif claim.relation == USES_IMAGE and is_service_key(claim.subject):
            _add_once(self._service(claim.subject).images, claim.object.removeprefix("image:"))
        elif claim.relation == EXPOSES and is_service_key(claim.subject):
            _add_once(self._service(claim.subject).ports, claim.object.removeprefix("port:"))
        elif claim.relation == CODE_ROOT:
            root = claim.object.removeprefix("dir:")
            service = self._service(claim.subject)
            service.code_root, service.code_root_status = ("" if root == "." else root), claim.status
        elif claim.relation == DEFINES:
            self.definitions[claim.object] = Definition(
                claim.object,
                claim.object_kind,
                claim.status,
                claim.file,
                (claim.line_start, claim.line_end),
                claim.key,
            )
        elif claim.relation == IMPORTS_MODULE:
            self.module_links.append(claim)
        elif claim.relation in SERVICE_LINKS:
            self.service_links.append(claim)
        elif claim.relation == CALLS:
            self._calls.append(claim)

    def files_in(self, directory: str) -> list[str]:
        """Modules under `directory` (`""` is the root): one contiguous slice of the sorted list."""
        if not directory:
            return self.files
        prefix = directory + "/"
        start = bisect.bisect_left(self.files, prefix)
        return self.files[start : bisect.bisect_left(self.files, prefix + "􏿿", lo=start)]

    def _service(self, key: str) -> Service:
        if key not in self.services:
            self.services[key] = Service(key, key.split(":", 1)[1].split("/")[-1])
        return self.services[key]

    def _nest_definitions(self) -> None:
        """`file::A.b` sits under `file::A` when `A` is a definition of that file, else under the file."""
        for key in sorted(self.definitions, key=lambda k: (self.definitions[k].lines, k)):
            file, _, name = key.partition("::")
            parent = name.split("~", 1)[0].rpartition(".")[0]
            parent_key = f"{file}::{parent}"
            if parent and parent_key in self.definitions:
                self.children_of_definition[parent_key].append(key)
            else:
                self.top_definitions[file].append(key)


def _add_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def is_service_key(key: str) -> bool:
    return key.startswith(("service:", "k8s:"))


def _directories(files: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """Each directory (`""` is the root) with its sub-directories and its files, both sorted."""
    subdirs: dict[str, set[str]] = defaultdict(set)
    direct: dict[str, list[str]] = defaultdict(list)
    for path in files:
        parent = posixpath.dirname(path)
        direct[parent].append(path)
        while parent:
            grand = posixpath.dirname(parent)
            subdirs[grand].add(parent)
            parent = grand
    names = set(subdirs) | set(direct)
    return {name: (sorted(subdirs.get(name, ())), sorted(direct.get(name, []))) for name in names}

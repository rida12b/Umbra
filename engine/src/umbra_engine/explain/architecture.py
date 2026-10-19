"""The architecture diagram of a Project: who uses it, its running parts, its stores and the outside
services it talks to, and the flows between them (an HLD, written by the user's Claude Code).

Claude is shown the Project's shape, never its whole code: folders, declared services, manifests,
the external libraries each folder imports, likely entry files and the README — all through the
Secret Guard. Each block must point to code that exists; flows must join known blocks.
"""

import json
import posixpath
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field

from umbra_engine.claims import StoredClaim
from umbra_engine.explain.cards import CardFormatError
from umbra_engine.explain.material import Material, numbered_file
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.projection.graph import ProjectGraph

ARCHITECTURE = "arch:"
BLOCK_TYPES = (
    "user", "frontend", "backend", "worker", "database", "storage", "queue", "external",
    "ml_model", "device", "cli", "library", "docs", "tests", "infra",
)  # fmt: skip
MANIFESTS = ("package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml")
ENTRY_NAMES = re.compile(r"(^|/)(main|app|server|index|manage|cli|wsgi|asgi|__main__)\.\w+$")
TREE_DEPTH = 3
LIBRARIES_PER_FOLDER = 25

PROMPT = """You draw the architecture of a software project for a future solution architect.
Write in French, plain words. Think like a C4 container diagram: who uses the system, which parts run
(frontend, backend API, workers, CLI, devices), where data is stored, which outside services or AI
models are called, and what flows between them.

Answer with ONLY one JSON object:
{{
  "resume": "2-3 sentences: what the system does and how it is built",
  "blocs": [{{"id": "short-id", "nom": "display name", "type": one of {types},
             "role": "one sentence", "techno": "main technologies",
             "code": ["existing folder or file paths from the TREE below; empty for outside things"],
             "indices": "what in the material shows this block exists"}}],
  "flux": [{{"de": "block id", "vers": "block id", "quoi": "what goes through (HTTP POST /login, SQL...)"}}],
  "parcours": ["the main path a user's action follows through the blocks, 3-7 steps"],
  "incertitudes": ["what cannot be known from this material"]
}}
Use 3 to 12 blocks. Include the user and outside services as blocks. Put documentation and tests in
one block each only if they matter. Only claim what the material shows; say "probablement" otherwise.

PROJECT {name}

{text}
"""


@dataclass(frozen=True)
class Architecture:
    resume: str
    blocs: list[dict] = field(default_factory=list)
    flux: list[dict] = field(default_factory=list)
    parcours: list[str] = field(default_factory=list)
    incertitudes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def architecture_material(graph: ProjectGraph, guard: SecretGuard, imports: list[StoredClaim]) -> Material:
    sections = [
        "TREE (folders with their number of analysed files)\n" + _tree(graph),
        "EXTERNAL LIBRARIES IMPORTED, PER TOP FOLDER\n" + _libraries(graph, imports),
        "DECLARED SERVICES (compose, Kubernetes)\n" + _services(graph),
        "LIKELY ENTRY FILES\n"
        + ("\n".join(f for f in graph.files if ENTRY_NAMES.search(f))[:4000] or "(none)"),
    ]
    for manifest in [m for m in graph.files if posixpath.basename(m) in MANIFESTS][:6]:
        sections.append(numbered_file(guard, manifest, 1, 80))
    for readme in ("README.md", "readme.md", "README.rst", "README"):
        if isinstance(guard.read(readme), GuardedFile):
            sections.append(numbered_file(guard, readme, 1, 120))
            break
    text = "\n\n".join(sections)[:90_000]
    return Material("architecture", graph.name, text, [])


def prompt_for_architecture(material: Material) -> str:
    return PROMPT.format(types=" | ".join(BLOCK_TYPES), name=material.title, text=material.text)


def parse_architecture(answer: str, graph: ProjectGraph) -> Architecture:
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    try:
        raw = json.loads(match.group(0)) if match else None
    except ValueError as error:
        raise CardFormatError(f"invalid JSON: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("resume"), str):
        raise CardFormatError("missing resume")
    blocks = [b for b in (_block(item, graph) for item in _list(raw.get("blocs"))) if b]
    ids = {b["id"] for b in blocks}
    flows = [
        {"de": f["de"], "vers": f["vers"], "quoi": str(f.get("quoi", ""))}
        for f in _list(raw.get("flux"))
        if isinstance(f, dict) and f.get("de") in ids and f.get("vers") in ids and f["de"] != f["vers"]
    ]
    return Architecture(
        resume=raw["resume"],
        blocs=blocks,
        flux=flows,
        parcours=[s for s in _list(raw.get("parcours")) if isinstance(s, str)],
        incertitudes=[s for s in _list(raw.get("incertitudes")) if isinstance(s, str)],
    )


def _block(item: object, graph: ProjectGraph) -> dict | None:
    """A block keeps only code paths that exist, each with the map element to open for it."""
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("nom"), str)
    ):
        return None
    code = []
    for path in [p for p in _list(item.get("code")) if isinstance(p, str)]:
        clean = path.strip().strip("/").removeprefix("./")
        if clean in graph.files:
            code.append({"chemin": clean, "element": clean})
        elif clean in graph.directories:
            code.append({"chemin": clean, "element": f"dir:{clean}" if clean else "app:"})
    kind = item.get("type") if item.get("type") in BLOCK_TYPES else "library"
    return {
        "id": item["id"],
        "nom": item["nom"],
        "type": kind,
        "role": str(item.get("role", "")),
        "techno": str(item.get("techno", "")),
        "code": code,
        "indices": str(item.get("indices", "")),
    }


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _tree(graph: ProjectGraph) -> str:
    counts: Counter[str] = Counter()
    for file in graph.files:
        parts = file.split("/")[:-1]
        for depth in range(1, min(len(parts), TREE_DEPTH) + 1):
            counts["/".join(parts[:depth])] += 1
    root_files = [f for f in graph.files if "/" not in f]
    lines = [f"{'  ' * (d.count('/'))}{d}/ ({n})" for d, n in sorted(counts.items())]
    return "\n".join(lines + [f"(root files) {', '.join(root_files[:40])}"])[:20_000]


def _libraries(graph: ProjectGraph, imports: list[StoredClaim]) -> str:
    """Imports that resolve to no file of the Project are outside libraries: they tell the technology."""
    internal = {(c.subject, c.line_start) for c in graph.module_links}
    per_folder: dict[str, Counter[str]] = defaultdict(Counter)
    for claim in imports:
        if (claim.file, claim.line_start) in internal or claim.object.startswith((".", "/")):
            continue
        name = re.split(r"[/.:]", claim.object.lstrip("@"))[0]
        folder = claim.file.split("/")[0] if "/" in claim.file else "(root)"
        if name:
            per_folder[folder][name] += 1
    lines = [
        f"{folder}: {', '.join(n for n, _ in names.most_common(LIBRARIES_PER_FOLDER))}"
        for folder, names in sorted(per_folder.items())
    ]
    return "\n".join(lines) or "(none)"


def _services(graph: ProjectGraph) -> str:
    links = defaultdict(list)
    for claim in graph.service_links:
        links[claim.subject].append(f"{claim.relation} {claim.object}")
    return (
        "\n".join(
            f"{s.key}: image {', '.join(s.images) or '-'}; ports {', '.join(s.ports) or '-'}; "
            f"code {s.code_root if s.code_root is not None else '-'}; {'; '.join(links[s.key])}"
            for s in graph.services.values()
        )
        or "(none declared)"
    )

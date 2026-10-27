"""The inside of one box of the project map (ADR-0007, Level 1, #105): ≤ 7 parts left → right in the
same shapes and words as Level 0, its neighbours as grey stubs at the edges, what sits around folded
into « + N autour ». Hard signals only (no LLM). Cells are stored apart, as Level 0: nothing moves."""

import posixpath

from umbra_engine.projection.inside_links import Placed, Wiring, part_links, stub_links
from umbra_engine.projection.inside_model import InsideMap, InsidePart
from umbra_engine.projection.inside_parts import (
    CLIENT_DIRS,
    PAGE_DIRS,
    SCREEN_DIRS,
    Cut,
    Group,
    cut,
    is_generated,
)
from umbra_engine.projection.inside_words import detail_of, role_of, title_of
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_model import (
    AroundItem,
    Proof,
    SystemLink,
    SystemMap,
    SystemOutput,
    proof_of,
)
from umbra_engine.projection.system_units import Unit

MAX_PARTS = 7
MAX_LOWER = 4  # more on the lower row would shrink the words below reading size
SHOWN = 3
SPINE = {"server": ("entry", "routes"), "web": ("entry", "pages", "screens", "client")}
KIT_WORDS = (("button", "boutons"), ("input", "champs"), ("table", "tableaux"), ("form", "formulaires"),
             ("dialog", "fenêtres"), ("select", "listes"))  # fmt: skip
DIRS_OF = {"pages": PAGE_DIRS, "screens": SCREEN_DIRS, "client": CLIENT_DIRS}
Cell = tuple[int, int]


def has_inside(facts: Facts, unit: Unit, folder: str) -> bool:
    return len(cut(facts, unit, folder).groups) >= 2


def inside_map(
    facts: Facts, units: list[Unit], shown: SystemMap, box_id: str, stored: dict[str, Cell]
) -> InsideMap | None:
    """None when the box has no inside worth a level (fewer than 2 parts, or not a part that runs)."""
    unit = next((u for u in units if u.id == box_id), None)
    box = next((b for b in shown.boxes if b.id == box_id), None)
    if unit is None or box is None:
        return None
    found = cut(facts, unit, box.folder)
    if len(found.groups) < 2:
        return None
    web = unit.role == "web"
    routes = len(facts.signal("route", unit.files))
    placed = [Placed(_part(facts, g, found.root, box_id, web, routes), g) for g in found.groups]
    spine = _spine(unit, placed)
    lower = [p for p in placed if p.part.id not in spine][: min(MAX_LOWER, MAX_PARTS - len(spine))]
    kept = {p.part.id for p in lower} | set(spine)
    overflow = [p.group for p in placed if p.part.id not in kept]  # the smallest: « + N autour »
    placed = [p for p in placed if p.part.id in kept]
    wiring = Wiring(facts, unit, placed, found.hidden)
    links = part_links(wiring, placed, spine, unit.role in SPINE)
    stubs, stub_arrows = stub_links(wiring, shown, box, units, placed, spine)
    cells = _cells(placed, spine, links, stored)
    for p in placed:
        p.part.col, p.part.row = cells[p.part.id]
    parts = sorted((p.part for p in placed), key=lambda p: (p.row, p.col)) + stubs
    folder = f"{found.root}/" if found.root else ""
    result = InsideMap(box_id, box.title, folder, _sentence(box.role, unit, stubs, placed), parts)
    result.links = links + stub_arrows
    result.outputs = _outputs(shown, box_id, placed, facts)
    result.around = _around(facts, found, web) + [
        _folded(facts, g, found.root, web, i) for i, g in enumerate(overflow)
    ]
    return result


def _part(facts: Facts, group: Group, root: str, box_id: str, web: bool, routes: int) -> InsidePart:
    files = sorted(group.chips or group.files)
    common = (
        posixpath.commonpath([posixpath.dirname(f) for f in files]) if all("/" in f for f in files) else ""
    )
    named = DIRS_OF.get(group.kind)
    if named and common:  # a part found by its folder name shows that folder: « components/ »
        segments = common.split("/")
        cut_at = next((i for i, s in enumerate(segments) if s.lower() in named), len(segments) - 1)
        common = "/".join(segments[: cut_at + 1])
    many = len(files) > 2 or bool(group.chips) or group.kind in ("pages", "screens", "client")
    folded = many and common and common != root
    folders = [_rel(common, root) + "/"] if folded else [_rel(f, root) for f in files[:2]]
    by_file: dict[str, Proof] = {}
    for claim in group.claims:
        by_file.setdefault(claim.file, proof_of(claim))
    client = group.kind == "client"
    first = sorted(files, key=lambda f: ("sdk" not in f, not is_generated(f)))  # sdk.gen.ts first
    shown = first if client else files
    proofs = list(by_file.values())[:SHOWN] or _files(shown)
    kind = group.kind.split(":", 1)[0]
    return InsidePart(
        f"{box_id}/{group.kind}", kind, title_of(group, web), detail_of(facts, group), folders,
        role_of(group, web, routes), proofs, chips=[Proof(f, 0, 0) for f in group.chips],
    )  # fmt: skip


def _spine(unit: Unit, placed: list[Placed]) -> list[str]:
    """The top row, left → right: the way in, then the way through (routes; pages, screens, client)."""
    kinds = SPINE.get(unit.role)
    if kinds:
        return [p.part.id for k in kinds for p in placed if p.part.kind == k][: len(kinds)] or [
            placed[0].part.id
        ]
    first = next((p for p in placed if p.part.kind == "entry"), placed[0])
    data = next((p for p in placed if p.part.kind == "data" and p is not first), None)
    return [first.part.id] + ([data.part.id] if data else [])


def _cells(
    placed: list[Placed], spine: list[str], links: list[SystemLink], stored: dict[str, Cell]
) -> dict[str, Cell]:
    """Top row = the spine; lower row = the rest, each under the top part that reaches it, left to right.
    A part seen before keeps its cell."""
    wanted = {pid: (i + 1, 0) for i, pid in enumerate(spine)}
    reached_from = {x.target: spine.index(x.source) for x in reversed(links) if x.source in spine}
    lower = [p.part.id for p in placed if p.part.id not in wanted]
    lower.sort(key=lambda pid: reached_from.get(pid, len(spine)))
    wanted.update({pid: (i + 1, 1) for i, pid in enumerate(lower)})
    cells: dict[str, Cell] = {}
    taken: set[Cell] = set()
    for pid in wanted:
        if pid in stored and stored[pid] not in taken:
            cells[pid] = stored[pid]
            taken.add(cells[pid])
    for pid, (col, row) in wanted.items():
        if pid not in cells:
            while (col, row) in taken:
                col += 1
            cells[pid] = (col, row)
            taken.add((col, row))
    return cells


def _sentence(role: str, unit: Unit, stubs: list[InsidePart], placed: list[Placed]) -> str:
    sources = {s.neighbour for s in stubs if s.side == "in"}
    targets = {s.neighbour for s in stubs if s.side == "out"}
    if unit.role == "web":
        does = ["ils affichent les pages"] if any(p.part.kind == "pages" for p in placed) else []
        if any(t.startswith("server:") for t in targets):
            does.append("appellent le serveur" if does else "ils appellent le serveur")
        return f"Les écrans dans le navigateur{' : ' + ' et '.join(does) if does else ''}."
    if unit.role == "server" and any(s.startswith("web:") for s in sources):
        return role.replace("Reçoit les appels", "Reçoit les appels de l'application web", 1)
    return role


def _outputs(shown: SystemMap, box_id: str, placed: list[Placed], facts: Facts) -> list[SystemOutput]:
    """What leaves the box itself (a screen, an answer, a printed result), from the part that does it."""
    found: list[SystemOutput] = []
    for output in (o for o in shown.outputs if o.box == box_id):
        printing = [p for p in placed if facts.signal("print", p.group.files)]
        owner = next((p for k in ("screens", "routes") for p in placed if p.part.kind == k), None)
        owner = owner or (printing[0] if printing else placed[0])
        found.append(SystemOutput(output.id, owner.part.id, output.label, output.detail, output.proofs))
    return found


def _around(facts: Facts, found: Cut, web: bool) -> list[AroundItem]:
    items: list[AroundItem] = []
    tests = found.around.get("tests", [])
    if tests:
        tool = (
            "Playwright"
            if any("playwright" in f.lower() or f.endswith(".spec.ts") for f in tests)
            else "pytest"
        )
        items.append(
            AroundItem("tests", "Tests des écrans" if web else "Tests", "tests", tool, _files(tests))
        )
    settings = found.around.get("settings", [])
    if settings:
        env = facts.signal("env-file", set(settings))
        detail = "lit le fichier .env" if env else "lus au démarrage"
        proofs = [proof_of(c) for c in facts.signal("settings", set(settings))[:1] + env[:1]]
        items.append(AroundItem("settings", "Réglages", "réglages", detail, proofs))
    migrations = found.around.get("migrations", [])
    if migrations:
        versions = [f for f in migrations if "/versions/" in f and f.endswith(".py")] or migrations
        detail = f"créent et modifient les tables, {len(versions)} fichiers"
        items.append(AroundItem("migrations", "Migrations", "migrations", detail, _files(versions)))
    kit = found.around.get("ui-kit", [])
    if kit:
        stems = {posixpath.splitext(posixpath.basename(f))[0] for f in kit}
        words = [w for stem, w in KIT_WORDS if stem in stems][:3]
        detail = f"{', '.join(words)} réutilisés" if words else f"{len(kit)} fichiers réutilisés"
        items.append(AroundItem("ui-kit", "Kit d'interface", "kit d'interface", detail, _files(kit)))
    return items


def _folded(facts: Facts, group: Group, root: str, web: bool, index: int) -> AroundItem:
    """A part left out of a full row, listed « autour » with what it holds."""
    title = title_of(group, web)
    detail = detail_of(facts, group) or _rel(sorted(group.files)[0], root)
    return AroundItem(f"more-{index}", title, title.lower(), detail, _files(sorted(group.files)))


def _rel(path: str, root: str) -> str:
    return path[len(root) + 1 :] if root and path.startswith(root + "/") else path


def _files(paths: list[str]) -> list[Proof]:
    return [Proof(p, 0, 0) for p in paths[:SHOWN]]

"""Arrows inside a box (Level 1): between its parts, from the imports that join their files, and to the
neighbours of the Level 0 map, drawn as grey stubs at the edges, from the lines that reach them (a write,
an SMTP call, an HTTP client). One verb per arrow; a part on the lower row gets one arrow in, no more."""

from dataclasses import dataclass

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.inside_model import InsidePart
from umbra_engine.projection.inside_parts import Group
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_model import Proof, SystemBox, SystemLink, SystemMap, proof_of
from umbra_engine.projection.system_units import Unit

VERBS = {
    ("entry", "routes"): "passe", ("routes", "access"): "vérifie la connexion",
    ("routes", "models"): "valide", ("routes", "data"): "utilise", ("entry", "pages"): "branche",
    ("pages", "screens"): "affiche", ("screens", "client"): "appelle",
    ("pages", "session"): "qui est connecté ?", ("session", "client"): "joint la preuve",
}  # fmt: skip
SHOWN = 3


@dataclass
class Placed:
    part: InsidePart
    group: Group


class Wiring:
    """Which part holds each file, and the imports between them (one unowned file may sit in between)."""

    def __init__(self, facts: Facts, unit: Unit, placed: list[Placed], hidden: set[str]) -> None:
        self.facts = facts
        self.owner = {f: p.part.id for p in placed for f in p.group.files}
        self.hidden = hidden
        self.files = unit.files
        self.imports: dict[str, list[StoredClaim]] = {}
        for claim in facts.module_links:
            self.imports.setdefault(claim.subject, []).append(claim)

    def reach_from(self, files: set[str], target_files: set[str]) -> list[StoredClaim]:
        """Direct imports only: from another box's files into this one, or out to another box."""
        return [c for f in sorted(files) for c in self.imports.get(f, []) if c.object in target_files]

    def reach(self, source: Group, target_files: set[str]) -> list[StoredClaim]:
        """The import lines of `source` that lead to `target_files`, directly or through one free file."""
        found: list[StoredClaim] = []
        for file in sorted(source.files):
            for claim in self.imports.get(file, []):
                if claim.object in target_files:
                    found.append(claim)
                elif (
                    claim.object in self.files
                    and claim.object not in self.owner
                    and any(c.object in target_files for c in self.imports.get(claim.object, []))
                ):
                    found.append(claim)
        return found


def part_links(wiring: Wiring, placed: list[Placed], spine: list[str], typed: bool) -> list[SystemLink]:
    """Along the top row from one part to the next; down to each lower part from the last top part that
    imports it; up from a lower part only when the verb is known. `typed`: a server or a web app, whose
    arrows are only the known pairs (VERBS); elsewhere « expose » from the entry, « utilise » otherwise."""
    by_id = {p.part.id: p for p in placed}
    links: list[SystemLink] = []

    def link(source: Placed, target: Placed) -> bool:
        pair = (source.part.kind, target.part.kind)
        verb = VERBS.get(pair) if typed else ("expose" if source.part.kind == "entry" else "utilise")
        claims = wiring.reach(source.group, target.group.files) if verb else []
        if pair == ("entry", "routes"):  # the line that hangs the routes on the app says it best
            claims = wiring.facts.signal("mount", source.group.files) or claims
        if not verb or not claims:
            return False
        detail = (
            f"{len(claims)} import{'s' if len(claims) > 1 else ''}"
            if not pair == ("entry", "routes")
            else "routes"
        )
        proofs = distinct(claims)
        links.append(
            SystemLink(
                f"{source.part.id}>{target.part.id}", source.part.id, target.part.id, verb, "", detail, proofs
            )
        )
        return True

    for left, right in zip(spine, spine[1:], strict=False):
        link(by_id[left], by_id[right])
    for lower in (p for p in placed if p.part.id not in spine):
        for top in reversed(spine):
            if link(by_id[top], lower):
                break
        for top in spine:
            if typed and (lower.part.kind, by_id[top].part.kind) in VERBS:
                link(lower, by_id[top])
    return links


def stub_links(
    wiring: Wiring,
    shown: SystemMap,
    box: SystemBox,
    units: list[Unit],
    placed: list[Placed],
    spine: list[str],
) -> tuple[list[InsidePart], list[SystemLink]]:
    """The box's neighbours on Level 0, as stubs: who comes in on the left, where it goes on the right."""
    titles = {b.id: b for b in shown.boxes}
    outputs = {o.box: o for o in shown.outputs}
    unit_files = {u.id: u.files for u in units}
    entry = next((p for p in placed if p.part.id == spine[0]), placed[0])
    stubs: list[InsidePart] = []
    links: list[SystemLink] = []
    for l0 in shown.links:
        if box.id not in (l0.source, l0.target) or l0.source == l0.target:
            continue
        side = "in" if l0.target == box.id else "out"
        other = titles[l0.source if side == "in" else l0.target]
        stub_id = f"stub:{other.id}"
        if side == "in":
            sources = [(entry, l0.verb, [])]
            if other.id in unit_files:
                # Into the entry when the neighbour imports it, else into the part it imports most.
                reached = [(wiring.reach_from(unit_files[other.id], p.group.files), p) for p in placed]
                into = next(((c, p) for c, p in reached if p is entry and c), None)
                best = into or max(reached, key=lambda r: len({c.object for c in r[0]}))
                sources = [(best[1] if best[0] else entry, l0.verb, best[0])]
            if other.kind == "actor" and box.id.startswith("web:"):
                sources = [(entry, "ouvre", [])]
            title, detail = "depuis", other.title
        else:
            sources = _senders(wiring, other.id, unit_files, placed, l0.verb)
            out = outputs.get(other.id)
            title, detail = (f"vers {other.title}", f"◉ {out.label}") if out else ("vers", other.title)
        if not sources:
            continue
        if all(s.id != stub_id for s in stubs):
            role = f"{other.title} : {other.role}" if other.role else other.title
            stubs.append(InsidePart(stub_id, "stub", title, detail, [], role, other.proofs[:SHOWN],
                                    neighbour=other.id, side=side, opens=other.opens))  # fmt: skip
        for part, verb, claims in sources:
            ends = (stub_id, part.part.id) if side == "in" else (part.part.id, stub_id)
            proofs = distinct(claims) or (part.part.proofs if part.part.kind == "client" else l0.proofs)
            links.append(
                SystemLink(f"{ends[0]}>{ends[1]}", ends[0], ends[1], verb, "", l0.detail, proofs, l0.inferred)
            )
    return stubs, links


def _senders(
    wiring: Wiring, target: str, unit_files: dict[str, set[str]], placed: list[Placed], verb: str
) -> list[tuple[Placed, str, list[StoredClaim]]]:
    """The parts that do what the Level 0 arrow says: write the base, send the mail, call the server."""
    facts = wiring.facts

    def having(*signals: str) -> list[tuple[Placed, list[StoredClaim]]]:
        found = [(p, [c for s in signals for c in facts.signals_starting(s, p.group.files)]) for p in placed]
        return [(p, claims) for p, claims in found if claims]

    if target.startswith("store:"):
        writers = having("db-write")
        if writers:
            return [
                (p, "écrit" + (f" ({p.part.detail})" if p.part.kind == "data" and p.part.detail else ""), c)
                for p, c in writers
            ]
        return [(p, "lit", c) for p, c in having("db-driver:")]
    if target == "sqlite-file":
        return [(p, verb, c) for p, c in having("sqlite")]
    if target == "mail":
        helpers = {c.file for c in facts.signal("smtp") if c.file in wiring.hidden}
        direct = having("smtp")
        callers = [(p, wiring.reach(p.group, helpers)) for p in placed]
        return [(p, "envoie", c) for p, c in direct + [(p, c) for p, c in callers if c]]
    if target in unit_files:
        client = [p for p in placed if p.part.kind == "client"]
        if client:
            return [(client[0], "envoie", [])]
        calls = having("http-client") or [
            (p, c) for p in placed if (c := wiring.reach_from(p.group.files, unit_files[target]))
        ]
        return [(p, verb, c) for p, c in calls]
    entry = placed[0]
    return [(entry, verb, [])]


def distinct(claims: list[StoredClaim]) -> list[Proof]:
    """The first lines, each once (an import can be read twice: the module and a name taken from it)."""
    seen = {(c.file, c.line_start): proof_of(c) for c in reversed(claims)}
    return [seen[k] for k in sorted(seen, key=[(c.file, c.line_start) for c in claims].index)][:SHOWN]

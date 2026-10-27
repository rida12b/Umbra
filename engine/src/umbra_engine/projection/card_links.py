"""« Appelé par » and « Appelle » on a card (#106): the parts of Level 1 and the boxes of Level 0 that
import a file of it or that it imports (through one helper no part holds, as on Level 1), and the
neighbours it reaches itself: the base it writes, the mail it sends, the server it calls."""

import posixpath

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.card_model import CALLED_BY, CALLS, CardLine, CardWord
from umbra_engine.projection.inside import InsideRead
from umbra_engine.projection.inside_links import Placed
from umbra_engine.projection.inside_model import InsidePart
from umbra_engine.projection.system_around import TEST_FILE
from umbra_engine.projection.system_model import SystemMap, proof_of
from umbra_engine.projection.system_units import Unit

PROOFS = 3
TESTS = "Tests"


def http_callers(read: InsideRead) -> CardLine:
    """Routes are called over HTTP: by whoever comes into the box on Level 1 (« Application web »)."""
    stubs = [p for p in read.map.parts if p.kind == "stub" and p.side == "in"]
    words = listed([(s.detail, _inferred(read, s), "") for s in stubs])
    return CardLine(CALLED_BY, words, [pr for s in stubs for pr in s.proofs][:PROOFS])


def called_by(
    read: InsideRead, placed: Placed, files: set[str], units: list[Unit], shown: SystemMap
) -> CardLine:
    wiring = read.wiring
    claims = [c for c in wiring.facts.module_links if c.object in files and c.subject not in files]
    through = [  # a helper no part holds, imported in turn: its importers call this one
        (c2.subject, c2) for c in claims if _free(read, c.subject)
        for c2 in wiring.facts.module_links if c2.object == c.subject
    ]  # fmt: skip
    coming = {x.source for x in read.map.links if x.target == placed.part.id}
    stubs = [p for p in read.map.parts if p.kind == "stub" and p.side == "in" and p.id in coming]
    words = listed([(s.detail, _inferred(read, s), "") for s in stubs])
    named = {s.detail for s in stubs}  # a neighbour seen as a stub is not named twice
    owners = _owners(read, placed, [(c.subject, c) for c in claims] + through, units, shown, named)
    return CardLine(CALLED_BY, _joined(words, owners), [proof_of(c) for c in claims[:PROOFS]])


def calls(read: InsideRead, placed: Placed, files: set[str], units: list[Unit], shown: SystemMap) -> CardLine:
    wiring = read.wiring
    claims = [c for f in sorted(files) for c in wiring.imports.get(f, [])]
    through = [
        (c2.object, c) for c in claims if _free(read, c.object) for c2 in wiring.imports.get(c.object, [])
    ]
    owners = _owners(read, placed, [(c.object, c) for c in claims] + through, units, shown, set())
    stubs = listed([(name, inferred, "") for name, inferred in _stubs_reached(read, placed, files)])
    return CardLine(CALLS, _joined(owners, stubs), [proof_of(c) for c in claims[:PROOFS]])


def _free(read: InsideRead, file: str) -> bool:
    return file in read.wiring.files and file not in read.wiring.owner and not TEST_FILE.search(file)


def _inferred(read: InsideRead, stub: InsidePart) -> bool:
    return next((x.inferred for x in read.map.links if stub.id in (x.source, x.target)), stub.inferred)


def _owners(
    read: InsideRead,
    placed: Placed,
    ends: list[tuple[str, StoredClaim]],
    units: list[Unit],
    shown: SystemMap,
    named: set[str],
) -> list[CardWord]:
    """The part (Level 1) or box (Level 0) holding each file, in map order; tests last, as « Tests »."""
    titles = {p.part.id: p.part.title for p in read.placed}
    order = {p.id: i for i, p in enumerate(read.map.parts)}
    boxes = {b.id: b.title for b in shown.boxes}
    found: dict[str, tuple[int, list[str]]] = {}
    for file, _ in ends:
        owner = read.wiring.owner.get(file)
        if owner == placed.part.id:
            continue
        if owner:
            key, rank = titles[owner], order.get(owner, 0)
        elif TEST_FILE.search(file):
            key, rank = TESTS, len(order) + 1
        else:
            unit = next((u for u in units if file in u.files and u.id != read.unit.id), None)
            if unit is None or unit.id not in boxes:
                continue
            key, rank = boxes[unit.id], len(order)
        found.setdefault(key, (rank, []))[1].append(file)
    ranked = sorted((k for k in found if k not in named), key=lambda k: found[k][0])
    return listed([(k, False, files_hint(found[k][1])) for k in ranked])


def _stubs_reached(read: InsideRead, placed: Placed, files: set[str]) -> list[tuple[str, bool]]:
    """The neighbours this part reaches on Level 1 whose arrow these files carry themselves."""
    stubs = {p.id: p for p in read.map.parts if p.kind == "stub"}
    found: list[tuple[str, bool]] = []
    for link in read.map.links:
        stub = stubs.get(link.target)
        if link.source != placed.part.id or stub is None:
            continue
        if any(pr.file in files for pr in link.proofs) or _does(read, stub, files):
            name = stub.title.removeprefix("vers ") if stub.title != "vers" else stub.detail
            found.append((name, link.inferred))
    return list(dict.fromkeys(found))


def _does(read: InsideRead, stub: InsidePart, files: set[str]) -> bool:
    """These files do what the arrow says: write the base, open the SQLite file, send mail, call."""
    facts = read.wiring.facts
    if stub.neighbour.startswith("store:"):
        return bool(facts.signal("db-write", files) or facts.signals_starting("db-driver:", files))
    if stub.neighbour == "sqlite-file":
        return bool(facts.signal("sqlite", files))
    if stub.neighbour == "mail":
        helpers = {c.file for c in facts.signal("smtp") if c.file in read.wiring.hidden}
        return bool(facts.signal("smtp", files) or read.wiring.reach_from(files, helpers))
    return bool(facts.signals_starting("http-client", files))


def listed(items: list[tuple[str, bool, str]]) -> list[CardWord]:
    """« A · B · C », each name its own word (dashed when deduced, its files on hover)."""
    words: list[CardWord] = []
    for text, inferred, hint in items:
        if words:
            words.append(CardWord("·"))
        words.append(CardWord(text, inferred=inferred, hint=hint))
    return words


def _joined(first: list[CardWord], then: list[CardWord]) -> list[CardWord]:
    return first + ([CardWord("·")] if first and then else []) + then


def files_hint(files: list[str]) -> str:
    unique = list(dict.fromkeys(files))
    shown = ", ".join(posixpath.basename(f) for f in unique[:PROOFS])
    return shown + (f" +{len(unique) - PROOFS}" if len(unique) > PROOFS else "")

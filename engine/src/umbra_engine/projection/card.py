"""The card of one part of a box, or one file of it (ADR-0007, Level 2, #106): four lines and the names
of its functions, from hard signals only. A route file says what it receives and returns over HTTP;
any other file what others take from it and what its functions return. « Appelé par » and « Appelle »
use the part names and stubs of Level 1, so the card and the map never disagree. Nothing below."""

import posixpath
from collections import Counter
from collections.abc import Callable

from umbra_engine.claims import StoredClaim
from umbra_engine.projection import card_routes
from umbra_engine.projection.card_code import imported_names, return_types
from umbra_engine.projection.card_links import called_by, calls, files_hint, http_callers
from umbra_engine.projection.card_model import RECEIVES, RETURNS, CardFunction, CardLine, CardWord, PartCard
from umbra_engine.projection.card_routes import Route, action_id
from umbra_engine.projection.inside import InsideRead
from umbra_engine.projection.inside_links import Placed
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_model import Proof, SystemMap, proof_of
from umbra_engine.projection.system_units import Unit

MAX_FUNCTIONS = 200
NAMES_SHOWN = 4
PROOFS = 3
ROUTES_SECTION = "Ce qu'on peut faire ici"
FUNCTIONS_SECTION = "Ses fonctions"
TextOf = Callable[[str], str | None]
DefinitionsOf = Callable[[str], list[StoredClaim]]


def part_card(
    read: InsideRead, facts: Facts, shown: SystemMap, units: list[Unit], part_id: str, file: str,
    text_of: TextOf, definitions_of: DefinitionsOf,
) -> PartCard | None:  # fmt: skip
    """None when the part is not drawn on Level 1, or the file is not one of its files."""
    placed = next((p for p in read.placed if p.part.id == part_id), None)
    if placed is None or (file and file not in placed.group.files | set(placed.group.chips)):
        return None
    files = [file] if file else (placed.group.chips or sorted(placed.group.files))
    route_files = {c.file for c in facts.signal("route", set(files))}
    found = _routes(read, facts, [f for f in files if f in route_files], text_of)
    known = {c.object.rsplit("::", 1)[-1] for c in facts.classes if c.file in read.unit.files}
    title, folder, path = _names(read, placed, file)
    if found:
        sentence = card_routes.sentence([(r, full, words) for _, r, full, words in found])
        lines = [_route_receives(read, found, known, files), _route_returns(found, known), http_callers(read)]
    else:
        sentence = placed.part.role
        lines = [
            _receives(read, files, text_of),
            _returns(files, text_of),
            called_by(read, placed, set(files), units, shown),
        ]
    lines.append(calls(read, placed, set(files), units, shown))
    functions = [
        CardFunction(r.name or r.path, f, r.line, r.verb, full, words, action_id(f, r.line) if r.name else "")
        for f, r, full, words in found
    ]
    functions += _functions(files, definitions_of, {(f.file, f.name) for f in functions})
    section = ROUTES_SECTION if found else FUNCTIONS_SECTION
    return PartCard(
        read.map.box, part_id, file, title, folder, path, sentence, files[0], lines, section,
        functions[:MAX_FUNCTIONS], max(0, len(functions) - MAX_FUNCTIONS),
    )  # fmt: skip


def _names(read: InsideRead, placed: Placed, file: str) -> tuple[str, str, str]:
    """(title, folder next to it, path under the name): « items.py », « backend/app/api/routes/ »…"""
    if file:
        folder = posixpath.dirname(file)
        return posixpath.basename(file), f"{folder}/" if folder else "", file
    lines = placed.part.folders
    path = read.map.folder + lines[0] if len(lines) == 1 else read.map.folder
    return placed.part.title, path if path.endswith("/") else read.map.folder, path


def _routes(read: InsideRead, facts: Facts, files: list[str], text_of: TextOf) -> list[Route]:
    return card_routes.read_routes(facts, read.unit.files, files, text_of)


def _route_receives(read: InsideRead, found: list[Route], known: set[str], files: list[str]) -> CardLine:
    """« GET · POST · PUT · DELETE /api/v1/items/ + connexion », on one line as the mock draws it; the
    models it takes (« ItemCreate · ItemUpdate ») are read too and shown on hover of the address."""
    used = {r.verb for _, r, _, _ in found}
    taken = list(dict.fromkeys(t for _, r, _, _ in found for t in r.takes if t in known))
    words = [
        CardWord(" · ".join(v for v in card_routes.ORDER if v in used)),
        CardWord(
            card_routes.common_address([full for _, _, full, _ in found]), mono=True,
            hint=f"données reçues : {' · '.join(taken)}" if taken else "",
        ),
    ]  # fmt: skip
    access = [p for p in read.placed if p.part.kind == "access"]
    checks = [c for p in access for c in read.wiring.reach_from(set(files), p.group.files)]
    if checks:
        words.append(CardWord("+ connexion", hint=files_hint([c.object for c in checks])))
    return CardLine(RECEIVES, words, [Proof(f, r.line, r.line) for f, r, _, _ in found][:PROOFS])


def _route_returns(found: list[Route], known: set[str]) -> CardLine:
    """« un item, une liste d'items, ou une erreur », from the response models and the raises."""
    models = [a for _, r, _, _ in found for a in r.answers if a in known]
    text = card_routes.answer_words(models, known, any(r.raises for _, r, _, _ in found))
    return CardLine(RETURNS, [CardWord(text, hint=" · ".join(dict.fromkeys(models)))] if text else [])


def _receives(read: InsideRead, files: list[str], text_of: TextOf) -> CardLine:
    """What other files take from it: `from .db import Database, Table` → « appels à Database · Table »."""
    importers = [c for c in read.wiring.facts.module_links if c.object in files and c.subject not in files]
    modules = {posixpath.splitext(posixpath.basename(f))[0] for f in read.wiring.facts.files}
    names: list[str] = []
    for claim in importers:
        text = text_of(claim.subject) or ""
        taken = imported_names(text, claim.line_start, claim.line_end, claim.subject.endswith(".py"))
        names += [n for n in taken if n not in modules and not n.startswith("_")]
    names = _most_taken(names)
    if not names:
        return CardLine(RECEIVES, [])
    return CardLine(
        RECEIVES, [CardWord("appels à"), *_names_shown(names)], [proof_of(c) for c in importers[:PROOFS]]
    )


def _most_taken(names: list[str]) -> list[str]:
    """Most imported first; constants and errors after, so `Database · Table` lead, not `DEFAULT`."""
    counted = Counter(names)

    def rank(name: str) -> tuple[bool, int]:
        minor = name.isupper() or name.endswith(("Error", "Exception", "Warning"))
        return (minor, -counted[name])

    return sorted(counted, key=rank)


def _returns(files: list[str], text_of: TextOf) -> CardLine:
    """The types its public functions say they return, the most frequent first."""
    counted: Counter[str] = Counter()
    for file in (f for f in files if f.endswith(".py")):
        counted.update(return_types(text_of(file) or ""))
    names = [n for n, _ in counted.most_common()]
    return CardLine(RETURNS, _names_shown(names) if names else [])


def _names_shown(names: list[str]) -> list[CardWord]:
    """The first names in monospace, then « +N » with the others on hover."""
    words = [CardWord(" · ".join(names[:NAMES_SHOWN]), mono=True)]
    if len(names) > NAMES_SHOWN:
        words.append(CardWord(f"+{len(names) - NAMES_SHOWN}", hint=" · ".join(names[NAMES_SHOWN:])))
    return words


def _functions(
    files: list[str], definitions_of: DefinitionsOf, taken: set[tuple[str, str]]
) -> list[CardFunction]:
    """Functions and methods, public ones first, then file and line order; nested functions left out."""
    found: list[CardFunction] = []
    for file in files:
        defined = definitions_of(file)
        classes = {c.object.rsplit("::", 1)[-1] for c in defined if c.object_kind in ("class", "type")}
        for claim in sorted(defined, key=lambda c: c.line_start):
            name = claim.object.rsplit("::", 1)[-1].split("~", 1)[0]
            owner = name.rsplit(".", 1)[0] if "." in name else ""
            kept = claim.object_kind in ("function", "method") and (not owner or owner in classes)
            if kept and (file, name) not in taken:
                found.append(CardFunction(name, file, claim.line_start))
    return sorted(found, key=lambda f: _private(f.name.rsplit(".", 1)[-1]))  # stable: line order kept


def _private(name: str) -> bool:
    """`_helper` is private; `__init__` is how the class is built, so it stays with the public ones."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

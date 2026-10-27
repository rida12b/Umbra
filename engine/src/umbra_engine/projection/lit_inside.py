"""A path lit inside one box (Level 1, mock p-chemin.png): the same `Highlight` as on the whole map (#104),
numbered on the parts and stubs of the box instead of under the boxes. An action's traced path (#107) is
built here, and so is a `show` from Claude Code that names a part of a box (« Serveur/Contrôle d'accès »).

Pure: the box as drawn (`InsideRead`) and the steps in; a `Highlight` or a `NotOnMapError` out."""

import posixpath

from umbra_engine.projection.highlight import (
    MAX_NOTE,
    MAX_STEPS,
    MAX_WHY,
    QUESTION,
    Highlight,
    LitStep,
    NotOnMapError,
    StepRequest,
    short_text,
)
from umbra_engine.projection.inside import InsideRead
from umbra_engine.projection.inside_model import InsideMap, InsidePart
from umbra_engine.projection.system_model import SystemMap

SEPARATOR = "/"  # « Serveur/Contrôle d'accès »: a part of a box, for `show`


def inside_highlight(
    read: InsideRead,
    caption: str,
    steps: list[LitStep],
    kind: str,
    detail: str = "",
    before: dict[int, list[str]] | None = None,
) -> Highlight:
    """`steps` already name their part (`LitStep.part`); numbers follow their order. The parts a step goes
    through to reach the next one without an arrow of its own (Porte d'entrée) light unnumbered.
    `before`: files met before a step's own file (the form that calls the generated client), by number."""
    numbered = [s.part for s in steps]
    passed = passed_between(read.map, numbered)
    lit = set(numbered) | set(passed)
    files: list[str] = []
    for at, step in enumerate(steps):
        files += (before or {}).get(step.n, []) + [step.path]
        for middle in passed_between(read.map, numbered[at : at + 2]):
            files += _proof_files(read.map, middle)
    return Highlight(
        caption, [read.map.box], steps, list(dict.fromkeys(f for f in files if f)), kind=kind,
        detail=detail, inside=read.map.box, parts=[p.id for p in read.map.parts if p.id in lit],
        passed=passed,
    )  # fmt: skip


def passed_between(drawn: InsideMap, numbered: list[str]) -> list[str]:
    """For each two steps in a row with no arrow between them, the one part an arrow goes through."""
    arrows = {(x.source, x.target) for x in drawn.links}
    found: list[str] = []
    for source, target in zip(numbered, numbered[1:], strict=False):
        if (source, target) in arrows:
            continue
        middle = next(
            (p.id for p in drawn.parts if (source, p.id) in arrows and (p.id, target) in arrows), None
        )
        if middle and middle not in numbered and middle not in found:
            found.append(middle)
    return found


def _proof_files(drawn: InsideMap, part: str) -> list[str]:
    """The line that makes a passed part pass the request on (« passe »: where the routes are hung)."""
    proofs = [pr.file for x in drawn.links if x.source == part for pr in x.proofs]
    return proofs[:1] or [pr.file for p in drawn.parts if p.id == part for pr in p.proofs][:1]


def names_a_part(shown: SystemMap, name: str) -> str | None:
    """The box whose part `name` names (« Serveur/Contrôle d'accès », « server:backend/access »), if any."""
    wanted = name.strip().casefold()
    for box in shown.boxes:
        if not box.opens:
            continue
        for prefix in (box.id, box.title):
            if wanted.startswith(prefix.casefold() + SEPARATOR) and len(wanted) > len(prefix) + 1:
                return box.id
    return None


def resolve_inside(read: InsideRead, caption: str, parts: list[str], path: list[StepRequest]) -> Highlight:
    """`show` inside one box: each step names a part (« Contrôle d'accès », or with its box first), a stub
    (« Base »), or a file or folder one part holds. The error lists the valid parts."""
    caption = " ".join(caption.split())
    if not caption:
        raise NotOnMapError("caption is empty: give the question or the action in one short line")
    if len(path) > MAX_STEPS:
        raise NotOnMapError(f"path has {len(path)} steps: show {MAX_STEPS} at most, the most useful first")
    steps: list[LitStep] = []
    for number, request in enumerate(path, start=1):
        note, why = short_text(request.note, MAX_NOTE, "note"), short_text(request.why, MAX_WHY, "why")
        part, file = _part(read, request.part)
        label = (
            posixpath.basename(file.rstrip("/")) + ("/" if file.endswith("/") else "")
            if file
            else _name(part)
        )
        steps.append(LitStep(number, read.map.box, label, file, note, why, part=part.id))
    found = inside_highlight(read, caption, steps, QUESTION)
    lit = {_part(read, p)[0].id for p in parts}
    found.parts = [p.id for p in read.map.parts if p.id in lit or p.id in set(found.parts)]
    return found


def _part(read: InsideRead, name: str) -> tuple[InsidePart, str]:
    """The part a name stands for, and the file it names (empty for a part named by its title)."""
    wanted = name.strip()
    short = wanted.split(SEPARATOR, 1)[1] if names_prefix(read, wanted) else wanted
    for part in read.map.parts:
        if short.casefold() in (part.id.casefold(), _name(part).casefold()) or wanted == part.id:
            return part, ""
    path = short.replace("\\", "/").removeprefix("./")
    owner = read.wiring.owner.get(path)
    if owner is None and path.endswith("/"):
        owner = next((o for f, o in sorted(read.wiring.owner.items()) if f.startswith(path)), None)
    part = next((p for p in read.map.parts if p.id == owner), None)
    if part is None:
        valid = "; ".join(f"{read.map.title}{SEPARATOR}{_name(p)}" for p in read.map.parts)
        raise NotOnMapError(
            f"unknown part: {name!r}. Inside {read.map.title} the valid parts are: {valid}; or a file one "
            f"of them holds. A path inside a box stays in that box."
        )
    return part, path


def names_prefix(read: InsideRead, name: str) -> bool:
    lowered = name.casefold()
    return any(lowered.startswith(p.casefold() + SEPARATOR) for p in (read.map.box, read.map.title))


def _name(part: InsidePart) -> str:
    """« Contrôle d'accès »; a stub by its neighbour: « Base », « Application web »."""
    if part.kind != "stub":
        return part.title
    return part.title.removeprefix("vers ") if part.title.startswith("vers ") else part.detail

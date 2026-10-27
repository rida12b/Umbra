"""An action's traced path on the map (#107, mock p-chemin.png): the call chain (`action_chain`) turned into
≤ 6 numbered steps, one per part it meets, inside the box that answers it (Level 1), with the same lit
`Highlight` as a question from Claude Code (#104). Who sends the request comes first, what it writes last.
Words are fixed templates and the map's own arrow verbs: no model writes them."""

import posixpath

from umbra_engine.projection.action_chain import Hit
from umbra_engine.projection.action_client import ClientCall
from umbra_engine.projection.actions import COMMANDS, Action
from umbra_engine.projection.highlight import MAX_STEPS, PATH, Highlight, LitStep
from umbra_engine.projection.inside import InsideRead
from umbra_engine.projection.inside_model import InsidePart
from umbra_engine.projection.lit_inside import inside_highlight
from umbra_engine.projection.system_model import SystemMap

MAX_WRITES = 2
GUESSES = {
    "name": "supposé : trouvé par son nom seul, le type de l'objet n'est pas lu dans le code",
    "class": "supposé : la classe le fait, l'appel exact n'est pas suivi dans le code",
}
OUT_TO = {"db-write": ("store:",), "smtp": ("mail",), "sqlite": ("sqlite-file",)}


def path_box(hits: list[Hit], owners: dict[str, str], opens: set[str]) -> str:
    """The box whose inside shows the path: the one that answers, else the one the path spends most time
    in; empty when none has an inside (the path is then drawn on the whole map)."""
    handler = owners.get(hits[0].file, "") if hits else ""
    if handler in opens:
        return handler
    counted = [owners[h.file] for h in hits if owners.get(h.file) in opens]
    return max(counted, key=counted.count) if counted else ""


def action_path(
    action: Action, hits: list[Hit], client: ClientCall | None, shown: SystemMap, owners: dict[str, str],
    read: InsideRead | None,
) -> Highlight:  # fmt: skip
    caption = action.label or action.address
    detail = f"{action.verb} {action.address}" if action.verb else ""
    if read is None:
        return _whole_map(action, hits, client, shown, owners, caption, detail)
    steps: list[LitStep] = []
    before: dict[int, list[str]] = {}
    stubs = {p.neighbour: p for p in read.map.parts if p.kind == "stub"}
    if client is not None and (stub := stubs.get(owners.get(client.file, ""))) is not None:
        steps.append(_client_step(action, client, stub, read.map.box))
        before[1] = [client.caller[0]] if client.caller else []
    writes = [h for h in hits if h.kind == "write"]
    for hit in [h for h in hits if h.kind != "write"]:
        part = _part_of(read, stubs, owners, hit.file)
        if part is not None and part.id not in {s.part for s in steps}:
            steps.append(_step(action, read, steps, part, hit))
    kept: list[LitStep] = []
    for hit in writes:  # one step per place it writes to, the first line that does
        step = _write_step(read, stubs, steps, hit)
        if step is not None and step.part not in {s.part for s in steps + kept}:
            kept.append(step)
    kept = kept[:MAX_WRITES]
    steps = steps[: MAX_STEPS - len(kept)] + kept
    for number, step in enumerate(steps, start=1):
        step.n = number
    return inside_highlight(read, caption, steps, PATH, detail, before)


def _client_step(action: Action, client: ClientCall, stub: InsidePart, box: str) -> LitStep:
    here = f"{posixpath.basename(client.file)}:{client.line}"
    label = f"{posixpath.basename(client.caller[0])}:{client.caller[1]} → {here}" if client.caller else here
    note, why = f"envoie {action.verb} {action.address}", f"lu dans {client.file}:{client.line}"
    return LitStep(0, box, label, client.file, note, why, part=stub.id)


def _step(action: Action, read: InsideRead, steps: list[LitStep], part: InsidePart, hit: Hit) -> LitStep:
    label = f"{posixpath.basename(hit.file)}:{hit.line} {hit.name}"
    if hit.kind == "handler":
        note = "lance la commande" if action.kind == COMMANDS else "reçoit la demande"
    else:
        note = _verb(read, [s.part for s in steps], part.id) or "appelle"
    why = _why(hit)
    chip = hit.file if hit.file in {c.file for c in part.chips} else ""
    return LitStep(0, read.map.box, label, hit.file, note, why, part=part.id, guess=hit.guess, chip=chip)


def _write_step(
    read: InsideRead, stubs: dict[str, InsidePart], steps: list[LitStep], hit: Hit
) -> LitStep | None:
    stub = next(
        (p for n, p in stubs.items() if n.startswith(OUT_TO.get(hit.signal, ("-",))) and p.side == "out"),
        None,
    )
    if stub is None:
        return None
    holder = read.wiring.owner.get(hit.file, "")
    verb = _verb(read, [holder], stub.id).split(" (")[0]  # « écrit (items) »: the table is said by the line
    note = f"{verb} : {stub.detail.removeprefix('◉ ')}" if verb else stub.detail.removeprefix("◉ ")
    label = f"{posixpath.basename(hit.file)}:{hit.line} {hit.name}"
    why = _why(hit)
    return LitStep(0, read.map.box, label, hit.file, note, why, part=stub.id, guess=hit.guess)


def _why(hit: Hit) -> str:
    return GUESSES.get(hit.reason, GUESSES["name"]) if hit.guess else f"lu dans {hit.file}:{hit.line}"


def _part_of(
    read: InsideRead, stubs: dict[str, InsidePart], owners: dict[str, str], file: str
) -> InsidePart | None:
    """The part holding the file, or the stub of the box that holds it (« depuis Commande »)."""
    owner = read.wiring.owner.get(file)
    if owner is not None:
        return next((p for p in read.map.parts if p.id == owner), None)
    return stubs.get(owners.get(file, ""))


def _verb(read: InsideRead, before: list[str], target: str) -> str:
    """The verb of the map's arrow into `target` from the latest part before it, or through one part."""
    arrows = {(x.source, x.target): x.verb for x in read.map.links}
    for source in reversed(before):
        if (source, target) in arrows:
            return arrows[(source, target)]
    into = [verb for (_, t), verb in arrows.items() if t == target]
    return into[0] if len(into) == 1 else ""


def _whole_map(
    action: Action, hits: list[Hit], client: ClientCall | None, shown: SystemMap, owners: dict[str, str],
    caption: str, detail: str,
) -> Highlight:  # fmt: skip
    """No box has an inside: one step per box of the map, numbered under it as for a question."""
    steps: list[LitStep] = []
    boxes = {b.id for b in shown.boxes}
    if client is not None and owners.get(client.file) in boxes:
        here = f"{posixpath.basename(client.file)}:{client.line}"
        steps.append(
            LitStep(0, owners[client.file], here, client.file, f"envoie {action.verb} {action.address}", "")
        )
    for hit in hits:
        box = owners.get(hit.file) if hit.kind != "write" else _out_box(shown, hit.signal)
        if box in boxes and box not in {s.box for s in steps}:
            label = f"{posixpath.basename(hit.file)}:{hit.line} {hit.name}"
            steps.append(LitStep(0, box, label, hit.file, "", _why(hit), guess=hit.guess))
    steps = steps[:MAX_STEPS]
    for number, step in enumerate(steps, start=1):
        step.n = number
    order = [b.id for b in shown.boxes if b.id in {s.box for s in steps}]
    files = list(dict.fromkeys(s.path for s in steps if s.path))
    return Highlight(caption, order, steps, files, kind=PATH, detail=detail)


def _out_box(shown: SystemMap, signal: str) -> str:
    prefixes = OUT_TO.get(signal, ("-",))
    return next((b.id for b in shown.boxes if b.id.startswith(prefixes)), "")

"""A lit path on the project map (ADR-0007, Screen 4): what Claude Code shows with `show`, checked against the
map and the indexed files. Boxes light up, ≤ 6 numbered steps sit under their box, the rest is dimmed.

Pure: the map, which box owns each file, and the request in; a `Highlight` or an `NotOnMapError` error out.
The error lists what is valid, so the caller (Claude Code, through MCP) can correct itself and retry.
"""

import posixpath
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import NoReturn

from umbra_engine.projection.system_model import SystemMap

MAX_STEPS = 6
MAX_CAPTION = 120
MAX_NOTE = 40
MAX_WHY = 240
SOURCE_DIRS = (
    "src/",
    "lib/",
    "app/",
)  # dropped from a step's short label, as the mock (« components/Items/ »)


class NotOnMapError(ValueError):
    """The request names something that is not on the map; the message says what is."""


@dataclass(frozen=True)
class StepRequest:
    part: str  # a box (id, title or folder) or a repo path, file or folder
    note: str = ""  # 2-4 words beside it: « ajouter le champ »
    why: str = ""  # one sentence on hover: « pourquoi ici »


@dataclass
class LitStep:
    n: int
    box: str  # the box it sits in
    label: str  # short, in the box's own terms: « models.py », « components/Items/ »
    path: str  # repo path (a folder ends with "/"); empty for a box without a folder
    note: str
    why: str


@dataclass
class Highlight:
    caption: str  # the question or the action, one line
    boxes: list[str] = field(default_factory=list)  # lit boxes, in map order
    steps: list[LitStep] = field(default_factory=list)
    files: list[str] = field(default_factory=list)  # what « copier pour Claude » copies, in step order
    serial: int = 0  # set by the engine: tells one `show` from the next


def resolve(
    shown: SystemMap,
    owners: dict[str, str],
    caption: str,
    parts: list[str],
    path: list[StepRequest],
) -> Highlight:
    """`owners`: repo file → the box that holds it, for every indexed file inside a box of the map."""
    caption = " ".join(caption.split())
    if not caption:
        raise NotOnMapError("caption is empty: give the question or the action in one short line")
    if len(caption) > MAX_CAPTION:
        raise NotOnMapError(
            f"caption is {len(caption)} characters: keep it to one line of {MAX_CAPTION} at most"
        )
    if len(path) > MAX_STEPS:
        raise NotOnMapError(f"path has {len(path)} steps: show {MAX_STEPS} at most, the most useful first")
    if not parts and not path:
        raise NotOnMapError("nothing to show: give parts (boxes) or path (files, folders or boxes)")
    lit = [_box(shown, part) or _fail(shown, part, owners) for part in parts]
    steps: list[LitStep] = []
    for number, request in enumerate(path, start=1):
        steps.append(_step(shown, owners, request, number))
    order = [b.id for b in shown.boxes]
    wanted = set(lit) | {s.box for s in steps}
    files = list(dict.fromkeys(s.path for s in steps if s.path))
    return Highlight(caption, [b for b in order if b in wanted], steps, files)


def valid_parts(shown: SystemMap) -> str:
    rows = [f"{b.id} ({', '.join(x for x in (b.title, b.folder) if x)})" for b in shown.boxes]
    return "; ".join(rows)


def _box(shown: SystemMap, part: str) -> str | None:
    wanted = part.strip().casefold()
    for box in shown.boxes:
        if wanted in (box.id.casefold(), box.title.casefold()) or (
            box.folder and wanted == box.folder.casefold()
        ):
            return box.id
    return None


def _fail(shown: SystemMap, part: str, owners: dict[str, str]) -> NoReturn:
    example = next(iter(sorted(owners)), "")
    hint = f", or a file or folder of the repo inside one of them (e.g. {example})" if example else ""
    raise NotOnMapError(f"unknown part: {part!r}. Valid parts: {valid_parts(shown)}{hint}")


def _step(shown: SystemMap, owners: dict[str, str], request: StepRequest, number: int) -> LitStep:
    note, why = _short(request.note, MAX_NOTE, "note"), _short(request.why, MAX_WHY, "why")
    box_id = _box(shown, request.part)
    if box_id is not None:
        box = next(b for b in shown.boxes if b.id == box_id)
        folder = box.folder if box.folder.endswith("/") else ""
        return LitStep(number, box_id, box.title, folder, note, why)
    path = _normal(request.part)
    if path in owners:
        return LitStep(number, owners[path], _label(shown, owners[path], path), path, note, why)
    folder = path.rstrip("/") + "/"
    inside = Counter(owner for file, owner in owners.items() if file.startswith(folder))
    if inside:
        owner = inside.most_common(1)[0][0]
        return LitStep(number, owner, _label(shown, owner, folder), folder, note, why)
    parent = posixpath.dirname(path.rstrip("/")) + "/"
    beside = Counter(owner for file, owner in owners.items() if file.startswith(parent) and parent != "/")
    if beside and not path.endswith("/"):  # a file to create, in a folder that exists: « où j'ajoute… »
        owner = beside.most_common(1)[0][0]
        return LitStep(number, owner, _label(shown, owner, path), path, note, why)
    _fail(shown, request.part, owners)


def _short(text: str, limit: int, name: str) -> str:
    text = " ".join(text.split())
    if len(text) > limit:
        raise NotOnMapError(f"{name} is {len(text)} characters: {limit} at most")
    return text


def _normal(part: str) -> str:
    path = part.strip().replace("\\", "/")
    path = re.sub(r"^\./+", "", path)
    return re.sub(r"/{2,}", "/", path)


def _label(shown: SystemMap, box_id: str, path: str) -> str:
    """The path in the box's own terms: without the box's folder, then without a leading src/ or app/. A box
    named by one file (« cli.py », « db.py ») shows the file or folder name alone."""
    box = next(b for b in shown.boxes if b.id == box_id)
    label = path
    if box.folder.endswith("/") and label.startswith(box.folder) and label != box.folder:
        label = label[len(box.folder) :]
    elif box.folder.endswith("/"):
        top = box.folder.split("/", 1)[0] + "/"
        label = label[len(top) :] if label.startswith(top) and label != top else label
    else:
        label = posixpath.basename(label.rstrip("/")) + ("/" if label.endswith("/") else "")
    for prefix in SOURCE_DIRS:
        if label.startswith(prefix) and label != prefix:
            label = label[len(prefix) :]
            break
    return label

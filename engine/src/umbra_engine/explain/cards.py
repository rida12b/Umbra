"""Explanation cards: what an element is for, what goes in and out, what happens, where it starts.

Written by the user's Claude Code from guarded Material; always a Hypothesis (an LLM's reading of
the code, each step pointing to the lines it comes from). A card is kept with the digest of the
Material it was written from: when the code changes, the card is out of date until rewritten.
"""

import json
import re
from dataclasses import asdict, dataclass, field

from umbra_engine.explain.material import Material

CARD_PRODUCER = "claude-code-card@1.1"  # a card from another version is rewritten

INSTRUCTIONS = {
    "application": (
        "This is the WHOLE system. Explain it like a high-level architecture overview (HLD): "
        "what the product does for its users, its main blocks and how a typical request or event "
        "flows through them, where execution starts."
    ),
    "group": (
        "This is one part of the system (a service or a folder of code). Explain what this part is "
        "responsible for, what it receives and produces, and how its pieces work together."
    ),
    "doc": (
        "This is a document. Leave 'entrees', 'sorties' and 'points_entree' empty. In 'role', say what "
        "the document is for and who should read it; in 'etapes', give its 3 to 6 key points, each with "
        "the lines where it is said; in 'depend_de', the parts of the system it talks about."
    ),
    "test": (
        "These are tests. In 'role', say which part of the system they protect; in 'entrees', the "
        "situations they set up; in 'sorties', what they check; in 'etapes', the main scenarios with "
        "their lines; leave 'points_entree' empty."
    ),
    "code": (
        "This is one file or one function. Explain it like a low-level design (LLD): who calls it "
        "with what, what it returns or changes (database, files, network, messages), and the "
        "steps it takes, in order."
    ),
}

PROMPT = """You explain software to a future solution architect who reads code with difficulty.
Write in French, in short, plain sentences. Name concrete things (routes, tables, files, functions).
{instruction}

Answer with ONLY one JSON object, no other text:
{{
  "role": "one sentence: what this is for, in the product's terms",
  "entrees": ["what comes in: who or what triggers it, with which data"],
  "sorties": ["what goes out: returned data, side effects such as database writes, emails, HTTP calls"],
  "etapes": [{{"texte": "one step", "fichier": "path or null", "lignes": [start, end] or null}}],
  "points_entree": [{{"nom": "where it starts", "fichier": "path or null", "lignes": [start, end] or null}}],
  "depend_de": ["other parts it relies on, and for what"],
  "enfants": {{"<element key in square brackets below, without brackets>": "one sentence role"}},
  "incertitudes": ["what cannot be known from what you were shown"]
}}
Use 3 to 6 "etapes". Fill "enfants" only when ELEMENTS are listed, one entry per element key.
Only state what the material below shows; put the rest in "incertitudes". Never invent lines.

ELEMENT: {title}

{text}
"""


@dataclass(frozen=True)
class Card:
    role: str
    entrees: list[str] = field(default_factory=list)
    sorties: list[str] = field(default_factory=list)
    etapes: list[dict] = field(default_factory=list)
    points_entree: list[dict] = field(default_factory=list)
    depend_de: list[str] = field(default_factory=list)
    enfants: dict[str, str] = field(default_factory=dict)
    incertitudes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class CardFormatError(ValueError):
    """Claude's answer was not the expected JSON object."""


def prompt_for(material: Material) -> str:
    return PROMPT.format(instruction=INSTRUCTIONS[material.level], title=material.title, text=material.text)


def parse_card(answer: str, material: Material) -> Card:
    """Keep only well-formed fields; child roles only for children that exist."""
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        raise CardFormatError("no JSON object in the answer")
    try:
        raw = json.loads(match.group(0))
    except ValueError as error:
        raise CardFormatError(f"invalid JSON: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("role"), str):
        raise CardFormatError("missing role")
    children = raw.get("enfants")
    if not isinstance(children, dict):
        children = {}
    return Card(
        role=raw["role"],
        entrees=_texts(raw.get("entrees")),
        sorties=_texts(raw.get("sorties")),
        etapes=_located(raw.get("etapes"), "texte"),
        points_entree=_located(raw.get("points_entree"), "nom"),
        depend_de=_texts(raw.get("depend_de")),
        enfants=_child_roles(children, material.child_keys),
        incertitudes=_texts(raw.get("incertitudes")),
    )


def _child_roles(written: dict, child_keys: list[str]) -> dict[str, str]:
    """Claude may name a child by its key, its path or its last path part: map each to the real key,
    and drop names that match no child (or several)."""
    aliases: dict[str, set[str]] = {}
    for key in child_keys:
        path = key.split(":", 1)[1] if key.startswith(("dir:", "service:", "k8s:")) else key
        for alias in {key, path, path.rsplit("/", 1)[-1], path.rsplit("::", 1)[-1]}:
            aliases.setdefault(alias.strip("[]/ ").lower(), set()).add(key)
    roles = {}
    for name, role in written.items():
        found = aliases.get(str(name).strip("[]/ ").lower(), set())
        if len(found) == 1 and isinstance(role, str):
            roles[next(iter(found))] = role
    return roles


def _texts(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _located(value: object, text_field: str) -> list[dict]:
    """`{text, fichier, lignes}` entries; a line range is kept only when it is two ordered integers."""
    entries = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get(text_field), str):
            continue
        lines = item.get("lignes")
        valid = (
            isinstance(lines, list)
            and len(lines) == 2
            and all(isinstance(n, int) and n >= 1 for n in lines)
            and lines[0] <= lines[1]
        )
        file = item.get("fichier") if isinstance(item.get("fichier"), str) else None
        entries.append({"texte": item[text_field], "fichier": file, "lignes": lines if valid else None})
    return entries

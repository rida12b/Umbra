"""What the Level 2 card returns (ADR-0007, #106): one part of a box, or one file of it, in four lines
(Reçoit / Renvoie / Appelé par / Appelle) and the names of its functions with their line. Built from
hard signals only (imports, definitions, route decorators, signals), never an LLM. Nothing below it:
the code itself opens in VS Code."""

from dataclasses import dataclass, field

from umbra_engine.projection.system_model import Proof

RECEIVES = "Reçoit"
RETURNS = "Renvoie"
CALLED_BY = "Appelé par"
CALLS = "Appelle"


@dataclass
class CardWord:
    text: str
    mono: bool = False  # a repo name (« /api/v1/items/ », « ItemCreate »), drawn in monospace
    inferred: bool = False  # deduced, not read: drawn dashed, « supposé »
    hint: str = ""  # on hover: the files behind it


@dataclass
class CardLine:
    label: str  # « Reçoit », « Renvoie », « Appelé par », « Appelle »
    words: list[CardWord]  # empty when nothing was read: the line says so
    proofs: list[Proof] = field(default_factory=list)


@dataclass
class CardFunction:
    name: str  # « read_items », « Table.insert »
    file: str
    line: int  # where it starts: VS Code opens there
    verb: str = ""  # a route: « GET »
    path: str = ""  # a route: « /api/v1/items/{id} »
    label: str = ""  # a route of a plain shape: « Voir un item »; empty otherwise
    action: str = ""  # a route: its id in « Ce qu'on peut faire », whose path « chemin → » lights (#107)


@dataclass
class PartCard:
    box: str
    part: str
    file: str  # the file asked for (a chip); empty for the whole part
    title: str  # « items.py », « Accès aux données »
    folder: str  # next to the title: « backend/app/api/routes/ »
    path: str  # under the name: « backend/app/api/routes/items.py »
    sentence: str
    open_file: str  # what « ouvrir le code » opens
    lines: list[CardLine]
    section: str  # « Ce qu'on peut faire ici » (routes), « Ses fonctions »
    functions: list[CardFunction]
    more: int = 0  # functions left out of the list

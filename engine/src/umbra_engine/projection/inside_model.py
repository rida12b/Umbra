"""What the Level 1 map returns (ADR-0007, #105): the inside of one box of the Level 0 map, ≤ 7 parts left
to right, and its neighbours drawn as grey stubs at the edges. Same words and shapes as Level 0; every
part and stub carries its proof (file and lines). Built from hard signals only, never an LLM."""

from dataclasses import dataclass, field

from umbra_engine.projection.system_model import AroundItem, Proof, SystemLink, SystemOutput


@dataclass
class InsidePart:
    id: str
    kind: str  # what the part does (« entry », « routes », « data »…), or « stub » for a neighbour
    title: str  # « Porte d'entrée », « vers Base », « depuis »
    detail: str  # « User · Item », « ◉ ligne enregistrée », « Application web »; empty when none
    folders: list[str]  # mono lines under the detail, relative to the box's folder: « api/deps.py »
    role: str  # one plain sentence, on hover
    proofs: list[Proof]
    chips: list[Proof] = field(default_factory=list)  # files drawn as chips inside the part (Routes)
    neighbour: str = ""  # a stub: the box of the Level 0 map it stands for (a click goes there)
    side: str = ""  # a stub: « in » (left edge, comes in) or « out » (right edge, goes out)
    opens: bool = False  # a stub whose neighbour has an inside of its own
    inferred: bool = False
    col: int = 0  # placed once and stored, as Level 0: the parts never move
    row: int = 0


@dataclass
class InsideMap:
    box: str  # the Level 0 box this is the inside of
    title: str  # « Serveur »
    folder: str  # the folder every part sits in: « backend/app/ »
    sentence: str
    parts: list[InsidePart] = field(default_factory=list)  # parts then stubs
    links: list[SystemLink] = field(default_factory=list)
    outputs: list[SystemOutput] = field(default_factory=list)
    around: list[AroundItem] = field(default_factory=list)

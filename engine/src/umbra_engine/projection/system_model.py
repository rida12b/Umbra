"""What the Level 0 project map API returns (ADR-0007): boxes, arrows, outputs and what sits around.

Every element carries its proof (file and lines). `inferred` marks what is deduced rather than read
(drawn dashed, « supposé »). Words are the plain French role words of the map (UI text is French).
"""

from dataclasses import dataclass, field
from typing import Literal

from umbra_engine.claims import StoredClaim

BoxKind = Literal["actor", "box", "external"]


@dataclass(frozen=True)
class Proof:
    file: str
    start: int
    end: int


def proof_of(claim: StoredClaim) -> Proof:
    return Proof(claim.file, claim.line_start, claim.line_end)


@dataclass
class SystemBox:
    id: str
    kind: BoxKind
    title: str  # the role word: « Serveur », « Base », « Commande »
    detail: str  # under the title: « FastAPI · Python », « 47 commandes »
    folder: str  # in mono under the detail: « backend/app/ », « cli.py »; empty when none
    role: str  # one plain sentence, on hover
    proofs: list[Proof]
    inferred: bool = False
    col: int = 0
    row: int = 0


@dataclass
class SystemLink:
    id: str
    source: str
    target: str
    verb: str  # on the arrow: « appelle », « écrit »
    back: str  # the verb of the way back, drawn as a second arrow (« répond »); empty when none
    detail: str  # on hover: how (protocol, library)
    proofs: list[Proof]
    inferred: bool = False


@dataclass
class SystemOutput:
    id: str
    box: str  # the box it leaves from
    label: str  # « ligne enregistrée »
    detail: str  # a second line, « JSON, CSV, tableau »; empty when none
    proofs: list[Proof]


@dataclass
class AroundItem:
    id: str
    title: str  # « Tests »
    short: str  # in the chip: « tests », « CI »; empty when it is not named there
    detail: str  # « pytest et Playwright »
    proofs: list[Proof]


@dataclass
class SystemMap:
    name: str
    sentence: str
    branch: str
    last_change: str  # YYYY-MM-DD of the last commit; empty when unknown
    boxes: list[SystemBox] = field(default_factory=list)
    links: list[SystemLink] = field(default_factory=list)
    outputs: list[SystemOutput] = field(default_factory=list)
    around: list[AroundItem] = field(default_factory=list)
    actions: int = 0  # routes a server answers, or commands a CLI offers

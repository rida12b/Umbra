"""Check a random sample of Facts against the code they cite (SPEC S1: 30 Facts, 100 % correct).

A Fact is correct when the lines it points to, read again through the Secret Guard, contain what it
claims: the defined name in the definition header (decorators allowed), the imported target in the
import statement.
"""

import random
from dataclasses import dataclass

from umbra_engine.claims import DEFINES, IMPORTS, StoredClaim
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.project_store import ProjectStore
from umbra_engine.registry import Project

CHECKED_RELATIONS = (DEFINES, IMPORTS)
HEADER_LINES = 15  # decorators and multi-line signatures before the name


@dataclass(frozen=True)
class FactCheck:
    claim: StoredClaim
    correct: bool
    cited_line: str


def check_facts(project: Project, store: ProjectStore, sample: int = 30, seed: int = 0) -> list[FactCheck]:
    facts = [
        claim
        for relation in CHECKED_RELATIONS
        for claim in store.claims(limit=1_000_000, relation=relation, status="fact")
    ]
    chosen = random.Random(seed).sample(facts, min(sample, len(facts)))
    guard = SecretGuard(project.root)
    return [_check(guard, claim) for claim in sorted(chosen, key=lambda c: c.id)]


def _check(guard: SecretGuard, claim: StoredClaim) -> FactCheck:
    released = guard.read(claim.file)
    if not isinstance(released, GuardedFile):
        return FactCheck(claim, False, f"<file now skipped: {released.reason}>")
    lines = released.text.splitlines()
    if not 1 <= claim.line_start <= len(lines):
        return FactCheck(claim, False, "<line out of range>")
    if claim.relation == DEFINES:
        expected = claim.object.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
        last = min(claim.line_end, claim.line_start + HEADER_LINES - 1)
    else:
        expected, last = claim.object, claim.line_end
    cited = lines[claim.line_start - 1 : last]
    hit = next((line for line in cited if expected in line), None)
    return FactCheck(claim, hit is not None, (hit or cited[0]).strip()[:160])

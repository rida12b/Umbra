"""Calls between definitions. A call is linked to a definition only when exactly one candidate fits:
- `save()` (bare): a function nested in the caller, else a top-level function of the caller's file,
  else of the files it imports — never a method;
- `self.save()`: a method of the caller's own class;
- `d.save()` (any other object): never linked, the object's type is unknown.
Matching names is not proof (shadowing, dynamic dispatch): every resolved call stays a Hypothesis."""

from collections import defaultdict

from umbra_engine.claims import StoredClaim


def resolve_calls(
    calls: list[StoredClaim], definitions: dict[str, str], imports: dict[str, set[str]]
) -> list[tuple[str, str, StoredClaim]]:
    """`(caller key, callee key, claim)`; `definitions` maps each definition key to its kind."""
    top_level: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key in definitions:
        file, _, qualified = key.partition("::")
        name = qualified.split("~", 1)[0]
        if "." not in name:
            top_level[(file, name)].append(key)
    resolved = []
    for claim in calls:
        target = _target(claim, definitions, imports, top_level)
        if target is not None and target != claim.subject:
            resolved.append((claim.subject, target, claim))
    return resolved


def _target(
    claim: StoredClaim, definitions: dict[str, str], imports: dict[str, set[str]], top_level
) -> str | None:
    called = claim.object
    caller_file, _, caller_name = claim.subject.partition("::")
    if called.startswith("."):
        return None
    if called.startswith("self."):
        owner = caller_name.split("~", 1)[0].split(".", 1)[0]  # `Repo.load` → class `Repo`
        candidate = f"{caller_file}::{owner}.{called[5:]}"
        return (
            candidate
            if definitions.get(f"{caller_file}::{owner}") == "class" and candidate in definitions
            else None
        )
    nested = f"{claim.subject}.{called}"
    if nested in definitions:
        return nested
    for files in ([caller_file], sorted(imports.get(caller_file, ()))):
        candidates = [k for f in files for k in top_level.get((f, called), [])]
        if candidates:  # the nearest scope that knows the name decides: one candidate or nothing
            return candidates[0] if len(candidates) == 1 else None
    return None

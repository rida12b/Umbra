"""Calls between definitions: a call names a function (`get_collection`); it is linked to a definition
only when exactly one candidate exists in the caller's file or in the files it imports. Matching
names is not proof (shadowing, dynamic dispatch): every resolved call stays a Hypothesis."""

from collections import defaultdict

from umbra_engine.claims import StoredClaim


def resolve_calls(
    calls: list[StoredClaim], definitions: set[str], imports: dict[str, set[str]]
) -> list[tuple[str, str, StoredClaim]]:
    """`(caller key, callee key, claim)` for every call that names exactly one reachable definition."""
    by_file_and_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key in definitions:
        file, _, qualified = key.partition("::")
        by_file_and_name[(file, qualified.split("~", 1)[0].rsplit(".", 1)[-1])].append(key)
    resolved = []
    for claim in calls:
        caller_file = claim.subject.split("::", 1)[0]
        for files in ([caller_file], sorted(imports.get(caller_file, ()))):
            candidates = [k for f in files for k in by_file_and_name.get((f, claim.object), [])]
            if len(candidates) == 1 and candidates[0] != claim.subject:
                resolved.append((claim.subject, candidates[0], claim))
                break
            if candidates:
                break  # ambiguous here: do not guess further away
    return resolved

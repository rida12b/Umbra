"""The Project model Claude Code returns after a study, checked against the code it cites.

Everything in it is an LLM's reading (a Hypothesis). What Umbra can check, it checks: each cited
file must exist in the guarded copy and each line range must fit in it ("verifie"); each block's
code path must exist on the map. Nothing unchecked is dropped silently: it stays, marked.
"""

import json
import re

BLOCK_TYPES = (
    "user", "frontend", "backend", "worker", "database", "storage", "queue", "external",
    "ml_model", "device", "cli", "library", "docs", "tests", "infra",
)  # fmt: skip
SECTIONS = ("blocs", "flux", "composants", "parcours")


class ModelFormatError(ValueError):
    """Claude's answer was not the expected JSON object."""


def parse_answer(answer: str) -> dict:
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    try:
        raw = json.loads(match.group(0)) if match else None
    except ValueError as error:
        raise ModelFormatError(f"invalid JSON: {error}") from error
    if not isinstance(raw, dict):
        raise ModelFormatError("no JSON object in the answer")
    return raw


def checked_model(
    raw: dict, line_counts: dict[str, int], directories: set[str], known_blocks: set[str] | None = None
) -> dict:
    """A complete model, every field in its expected shape, every citation checked."""
    if not isinstance(raw.get("resume"), str):
        raise ModelFormatError("missing resume")
    model = {
        "resume": raw["resume"],
        "blocs": [
            b for b in (_block(item, line_counts, directories) for item in _list(raw.get("blocs"))) if b
        ],
        "composants": [
            c for c in (_component(item, line_counts) for item in _list(raw.get("composants"))) if c
        ],
        "modules": {
            p: r for p, r in _dict(raw.get("modules")).items() if p in line_counts and isinstance(r, str)
        },
        "dossiers": {
            p.strip("/"): r
            for p, r in _dict(raw.get("dossiers")).items()
            if p.strip("/") in directories and isinstance(r, str)
        },
        "incertitudes": _texts(raw.get("incertitudes")),
    }
    # An update returns some blocks only: its journeys and flows may name blocks kept from before.
    block_ids = {b["id"] for b in model["blocs"]} | (known_blocks or set())
    model["parcours"] = [
        j for j in (_journey(item, line_counts, block_ids) for item in _list(raw.get("parcours"))) if j
    ]
    model["flux"] = _flows(raw.get("flux"), block_ids)
    return model


def updated_model(model: dict, raw_patch: dict, line_counts: dict[str, int], directories: set[str]) -> dict:
    """Entries returned by an update session replace the ones with the same id; `supprime` removes."""
    known = {b["id"] for b in model["blocs"]}
    patch = checked_model({"resume": model["resume"], **raw_patch}, line_counts, directories, known)
    removed = _dict(raw_patch.get("supprime"))
    merged = dict(model)
    for section in ("blocs", "composants", "parcours"):
        gone = set(_texts(removed.get(section))) | {entry["id"] for entry in patch[section]}
        merged[section] = [e for e in model[section] if e["id"] not in gone] + patch[section]
    gone_modules = set(_texts(removed.get("modules")))
    merged["modules"] = {
        p: r for p, r in model["modules"].items() if p not in gone_modules and p in line_counts
    }
    merged["modules"] |= patch["modules"]
    merged["dossiers"] = model.get("dossiers", {}) | patch["dossiers"]
    if isinstance(raw_patch.get("resume"), str):
        merged["resume"] = raw_patch["resume"]
    # New flows may join blocks that were not returned again: check them against every block.
    new_flows = _flows(raw_patch.get("flux"), {b["id"] for b in merged["blocs"]})
    replaced = {(f["de"], f["vers"]) for f in new_flows}
    merged["flux"] = [f for f in model["flux"] if (f["de"], f["vers"]) not in replaced] + new_flows
    merged["incertitudes"] = patch["incertitudes"] or model["incertitudes"]
    # Citations of untouched entries may point to lines that moved: check them all again.
    return checked_model(merged, line_counts, directories)


def _citation(item: dict, line_counts: dict[str, int]) -> dict:
    file = item.get("fichier") if isinstance(item.get("fichier"), str) else None
    file = file.strip().removeprefix("./") if file else None
    lines = item.get("lignes")
    valid_lines = (
        isinstance(lines, list) and len(lines) == 2 and all(isinstance(n, int) and n >= 1 for n in lines)
        and lines[0] <= lines[1]
    )  # fmt: skip
    verified = (
        file is not None and isinstance(lines, list) and valid_lines and lines[1] <= line_counts.get(file, 0)
    )
    return {"fichier": file, "lignes": lines if valid_lines else None, "verifie": verified}


def _block(item: object, line_counts: dict[str, int], directories: set[str]) -> dict | None:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("nom"), str)
    ):
        return None
    code = []
    written = [c.get("chemin") if isinstance(c, dict) else c for c in _list(item.get("code"))]
    for path in [p for p in written if isinstance(p, str)]:
        clean = path.strip().strip("/").removeprefix("./")
        if clean in line_counts:
            code.append({"chemin": clean, "element": clean})
        elif clean in directories:
            code.append({"chemin": clean, "element": f"dir:{clean}" if clean else "app:"})
    return {
        "id": item["id"],
        "nom": item["nom"],
        "type": item.get("type") if item.get("type") in BLOCK_TYPES else "library",
        "role": str(item.get("role", "")),
        "techno": str(item.get("techno", "")),
        "code": code,
        "indices": str(item.get("indices", "")),
    }


def _component(item: object, line_counts: dict[str, int]) -> dict | None:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("nom"), str)
    ):
        return None
    exposed = [
        {"quoi": str(e.get("quoi", "")), **_citation(e, line_counts)}
        for e in _list(item.get("expose"))
        if isinstance(e, dict)
    ]
    return {
        "id": item["id"],
        "nom": item["nom"],
        "bloc": str(item.get("bloc", "")),
        "role": str(item.get("role", "")),
        "responsabilites": _texts(item.get("responsabilites")),
        "expose": exposed,
        "utilise": _texts(item.get("utilise")),
        "fichiers": [f for f in _texts(item.get("fichiers")) if f in line_counts],
    }


def _journey(item: object, line_counts: dict[str, int], block_ids: set[str]) -> dict | None:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("nom"), str)
    ):
        return None
    steps = [
        {
            "texte": str(s.get("texte", "")),
            "composant": str(s.get("composant", "")),
            "touche": [b for b in _texts(s.get("touche")) if b in block_ids],
            **_citation(s, line_counts),
        }
        for s in _list(item.get("etapes"))
        if isinstance(s, dict) and s.get("texte")
    ]
    return {
        "id": item["id"],
        "nom": item["nom"],
        "declencheur": str(item.get("declencheur", "")),
        "etapes": steps,
        "resultat": str(item.get("resultat", "")),
    }


def _flows(value: object, block_ids: set[str]) -> list[dict]:
    return [
        {"de": f["de"], "vers": f["vers"], "quoi": str(f.get("quoi", ""))}
        for f in _list(value)
        if isinstance(f, dict)
        and f.get("de") in block_ids
        and f.get("vers") in block_ids
        and f["de"] != f["vers"]
    ]


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _texts(value: object) -> list[str]:
    return [v for v in _list(value) if isinstance(v, str)]

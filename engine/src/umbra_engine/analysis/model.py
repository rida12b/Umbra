"""The Project model Claude Code returns after a study, checked against the code it cites.

Everything in it is an LLM's reading (a Hypothesis). What Umbra can check, it checks: each cited
file must exist in the guarded copy and each line range must fit in it ("verifie"); each block's
code path must exist on the map. Nothing unchecked is dropped silently: it stays, marked.
"""

import json
import re

from umbra_engine.analysis import model_v17 as v17
from umbra_engine.analysis.literal import cut

BLOCK_TYPES = (
    "user", "frontend", "backend", "worker", "database", "storage", "queue", "external",
    "ml_model", "device", "cli", "library", "docs", "tests", "infra",
)  # fmt: skip
SECTIONS = ("blocs", "flux", "composants", "parcours")
MAX_ACTION = 60  # a label on the diagram, not a sentence
MAX_SHORT = 90  # a block's "en bref": a few words under its name
MAX_SIMPLE = 400
MAX_VERB = 50
IMPORTANCE = ("coeur", "secondaire", "ancien")
ZONES = ("utilise", "recoit", "traite", "range", "exterieur", "atelier")
MAX_IO = 4


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
    raw: dict,
    line_counts: dict[str, int],
    directories: set[str],
    known_blocks: set[str] | None = None,
    texts: dict[str, str] | None = None,
) -> dict:
    """A complete model, every field in its expected shape, every citation checked. `texts` are the files
    the Secret Guard released: settings are checked word for word in them (never in the Project folder)."""
    if not isinstance(raw.get("resume"), str):
        raise ModelFormatError("missing resume")
    texts = texts or {}
    model = {
        "pitch": str(raw.get("pitch", "")),
        "resume": raw["resume"],
        "blocs": [
            b for b in (_block(item, line_counts, directories) for item in _list(raw.get("blocs"))) if b
        ],
        "composants": [
            c for c in (_component(item, line_counts, texts) for item in _list(raw.get("composants"))) if c
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
    v17.main_journey(model["parcours"], model["composants"], block_ids)
    v17.derived_blocks(model["blocs"], model["composants"], model["parcours"])
    model["donnee"] = v17.data(raw.get("donnee"), block_ids)
    model["reglages_projet"] = v17.project_settings(raw.get("reglages_projet"), texts)
    model["pour_changer"] = v17.levers(
        raw.get("pour_changer"), model["composants"], model["blocs"], model["reglages_projet"], texts
    )
    return model


def updated_model(
    model: dict,
    raw_patch: dict,
    line_counts: dict[str, int],
    directories: set[str],
    texts: dict[str, str] | None = None,
) -> dict:
    """Entries returned by an update session replace the ones with the same id; `supprime` removes."""
    known = {b["id"] for b in model["blocs"]}
    patch = checked_model({"resume": model["resume"], **raw_patch}, line_counts, directories, known, texts)
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
    for text in ("resume", "pitch"):
        if isinstance(raw_patch.get(text), str):
            merged[text] = raw_patch[text]
    # New flows may join blocks that were not returned again: check them against every block.
    new_flows = _flows(raw_patch.get("flux"), {b["id"] for b in merged["blocs"]})
    replaced = {(f["de"], f["vers"], f["nature"]) for f in new_flows}
    merged["flux"] = [f for f in model["flux"] if (f["de"], f["vers"], f.get("nature", "donnee")) not in replaced]
    merged["flux"] += new_flows
    merged["incertitudes"] = patch["incertitudes"] or model["incertitudes"]
    if any(_dict(j).get("principal") is True for j in _list(raw_patch.get("parcours"))):
        returned = {j["id"] for j in patch["parcours"] if j["principal"]}
        merged["parcours"] = [j | {"principal": j["id"] in returned} for j in merged["parcours"]]
    for section, key in PROJECT_SECTIONS:
        merged[section] = _merged_rows(model.get(section, []), raw_patch, section, key)
    components = {c["id"] for c in merged["composants"]}
    merged["pour_changer"] = [p for p in merged["pour_changer"] if p.get("composant") in components]
    # Citations of untouched entries may point to lines that moved: check them all again.
    return checked_model(merged, line_counts, directories, texts=texts)


PROJECT_SECTIONS = (("donnee", ("nom",)), ("reglages_projet", ("fichier", "code")), ("pour_changer", ("composant", "intention")))


def _merged_rows(stored: list[dict], raw_patch: dict, section: str, key: tuple[str, ...]) -> list[dict]:
    """Rows of a Project-level section: the patch's replace stored ones with the same key; `supprime`
    removes by the key's first field (a data name, a file, a component)."""
    new = [r for r in _list(raw_patch.get(section)) if isinstance(r, dict)]
    gone = set(_texts(_dict(raw_patch.get("supprime")).get(section)))
    fresh = {tuple(r.get(k) for k in key) for r in new}
    kept = [r for r in stored if tuple(r.get(k) for k in key) not in fresh and r.get(key[0]) not in gone]
    return kept + new


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
        "en_bref": str(item.get("en_bref", ""))[:MAX_SHORT],
        "importance": item.get("importance") if item.get("importance") in IMPORTANCE else "coeur",
        "zone": item.get("zone") if item.get("zone") in ZONES else "",
        "entre": [t[:MAX_SHORT] for t in _texts(item.get("entre"))][:MAX_IO],
        "sort": [t[:MAX_SHORT] for t in _texts(item.get("sort"))][:MAX_IO],
        "techno": str(item.get("techno", "")),
        "code": code,
        "indices": str(item.get("indices", "")),
    }


def _component(item: object, line_counts: dict[str, int], texts: dict[str, str]) -> dict | None:
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
        "en_bref": str(item.get("en_bref", ""))[:MAX_SHORT],
        "bloc": str(item.get("bloc", "")),
        "role": str(item.get("role", "")),
        "responsabilites": _texts(item.get("responsabilites")),
        "expose": exposed,
        "utilise": _texts(item.get("utilise")),
        "fichiers": [f for f in _texts(item.get("fichiers")) if f in line_counts],
        "entre": v17.io(item.get("entre")),
        "sort": v17.io(item.get("sort")),
        "reglages": v17.settings(item.get("reglages"), texts),
        "termes": v17.terms(item.get("termes")),
    }


def _journey(item: object, line_counts: dict[str, int], block_ids: set[str]) -> dict | None:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("nom"), str)
    ):
        return None
    raw_steps = _list(item.get("etapes"))
    kept_at = [n for n, s in enumerate(raw_steps, 1) if isinstance(s, dict) and s.get("texte")]
    old_to_new = {old: new for new, old in enumerate(kept_at, 1)}  # branch and phase numbers follow
    steps = [_step(raw_steps[n - 1], line_counts, block_ids) for n in kept_at]
    return {
        "id": item["id"],
        "nom": item["nom"],
        "declencheur": str(item.get("declencheur", "")),
        "depart": str(item.get("depart", ""))[:MAX_SIMPLE],
        "fin": str(item.get("fin", ""))[:MAX_SIMPLE],
        "etapes": steps,
        "resultat": str(item.get("resultat", "")),
        "branches": [
            {
                "quand": str(b.get("quand", "")),
                "alors": str(b.get("alors", "")),
                "quand_simple": cut(b.get("quand_simple"), MAX_SIMPLE),
                "alors_simple": cut(b.get("alors_simple"), MAX_SIMPLE),
                "etape": v17.step_index(old_to_new, b.get("etape")),
                **_citation(b, line_counts),
            }
            for b in _list(item.get("branches"))
            if isinstance(b, dict) and b.get("quand")
        ],
        "principal": item.get("principal") is True and not item.get("principal_deduit"),  # deduced: picked again
        "entree": item.get("entree") if item.get("entree") in block_ids else None,
        "sortie": [b for b in _texts(item.get("sortie")) if b in block_ids],
        "phases": v17.phases(item.get("phases"), old_to_new, len(steps)),
    }


def _step(s: dict, line_counts: dict[str, int], block_ids: set[str]) -> dict:
    manual = s.get("manuel") is True
    composant = s.get("composant")
    return {
        "texte": str(s.get("texte", "")),
        "action": str(s.get("action", ""))[:MAX_ACTION],
        "simple": str(s.get("simple", ""))[:MAX_SIMPLE],
        # A step done by hand may have no component; otherwise a missing one is "", never "None".
        "composant": None if composant is None and manual else (composant if isinstance(composant, str) else ""),
        "touche": [b for b in _texts(s.get("touche")) if b in block_ids],
        "conditions": _texts(s.get("conditions")),
        "manuel": manual,
        **_citation(s, line_counts),
    }


def _flows(value: object, block_ids: set[str]) -> list[dict]:
    return [
        {
            "de": f["de"],
            "vers": f["vers"],
            "quoi": str(f.get("quoi", "")),
            "verbe": str(f.get("verbe", ""))[:MAX_VERB],
            "nature": f.get("nature") if f.get("nature") in v17.NATURES else "donnee",
        }
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

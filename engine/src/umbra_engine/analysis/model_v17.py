"""What method v1.7 adds to the Project model (#78, ADR-0006), checked the same way as the rest.

Per component: what comes in and goes out, the settings a person would change (each checked word for word
in the code it cites), the plain word ↔ code word bridge. For the Project: one name for the data that
flows, the settings of its config files, a « je veux changer… » index, and one main journey.
"""

from umbra_engine.analysis.literal import checked_setting, cited_lines, cut, read_by_code, safe_code

MAX_SHORT = 90
MAX_SIMPLE = 400
MAX_IO = 3
MAX_SETTINGS = 6
MAX_TERMS = 3
MAX_LEVERS = 3
SORTS = ("env", "entete", "constante", "champ", "limite", "branchement")
NATURES = ("donnee", "controle")
MIN_PHASES, MAX_PHASES, PHASED_FROM = 3, 5, 10


def _rows(value: object) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _texts(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def io(value: object) -> list[str]:
    return [cut(t, MAX_SHORT) for t in _texts(value)][:MAX_IO]


def terms(value: object) -> list[dict]:
    pairs = [
        {"simple": cut(t.get("simple"), MAX_SHORT), "code": cut(t.get("code"), MAX_SHORT)}
        for t in _rows(value)
    ]
    return [p for p in pairs if p["simple"] and p["code"]][:MAX_TERMS]


def settings(value: object, texts: dict[str, str]) -> list[dict]:
    return [
        {
            "nom": cut(row.get("nom"), MAX_SHORT),
            "code": str(row.get("code", "")),
            "sorte": row.get("sorte") if row.get("sorte") in SORTS else "",
            "effet": cut(row.get("effet"), MAX_SHORT),
            **checked_setting(row, texts),
        }
        for row in _rows(value)
        if isinstance(row.get("code"), str)
    ][:MAX_SETTINGS]


def project_settings(value: object, texts: dict[str, str]) -> list[dict]:
    rows = []
    for row in _rows(value):
        if not isinstance(row.get("code"), str):
            continue
        checked = checked_setting(row, texts)
        file, lines, _ = cited_lines(row, texts)
        line = (
            texts[file].splitlines()[lines[0] - 1]
            if file in texts and lines and 1 <= lines[0] <= len(texts[file].splitlines())
            else None
        )
        read = row.get("lu_par_le_code") == "oui" and read_by_code(row["code"], file, line, texts)
        rows.append(
            {
                "nom": cut(row.get("nom"), MAX_SHORT),
                "code": row["code"],
                **checked,
                "lu_par_le_code": "oui" if read else "non",
            }
        )
    return rows


def data(value: object, block_ids: set[str]) -> list[dict]:
    known = lambda b: b if b in block_ids else None  # noqa: E731
    return [
        {
            "nom": cut(row.get("nom"), MAX_SHORT),
            "dans_le_code": cut(row.get("dans_le_code"), MAX_SHORT),
            "entre_par": known(row.get("entre_par")),
            "finit_dans": known(row.get("finit_dans")),
        }
        for row in _rows(value)
        if isinstance(row.get("nom"), str) and row["nom"]
    ]


def levers(
    value: object, components: list[dict], blocks: list[dict], project: list[dict], texts: dict[str, str]
) -> list[dict]:
    """« Je veux changer… » → component and setting, at most MAX_LEVERS per core component. A lever naming
    a setting of its component takes that setting's citation; one naming an unread project setting is
    kept but never shown as verified."""
    core = {b["id"] for b in blocks if b.get("importance", "coeur") == "coeur"}
    owner = {c["id"]: c for c in components}
    per_component: dict[str, int] = {}
    kept = []
    for row in _rows(value):
        component = owner.get(row.get("composant"))
        if not component or component["bloc"] not in core or not isinstance(row.get("intention"), str):
            continue
        if per_component.get(component["id"], 0) >= MAX_LEVERS:
            continue
        per_component[component["id"]] = per_component.get(component["id"], 0) + 1
        code = safe_code(str(row.get("reglage", "")))  # matched against settings already cut
        own = next((s for s in component.get("reglages", []) if s["code"] == code), None)
        own = own or next((s for s in project if s["code"] == code), None)  # a project setting (.env, config)
        unread = next((s for s in project if s["code"] == code and s["lu_par_le_code"] == "non"), None)
        cited = (
            {k: own[k] for k in ("fichier", "lignes", "verifie")}
            if own
            else checked_setting({**row, "code": code}, texts)
        )
        lever = {
            "intention": cut(row["intention"], MAX_SIMPLE),
            "composant": component["id"],
            "reglage": code,
        }
        lever |= {
            "fichier": cited["fichier"],
            "lignes": cited["lignes"],
            "verifie": cited["verifie"] and not unread,
        }
        if unread:
            lever["motif"] = "non lu par le code"
        kept.append(lever)
    return kept


def step_index(old_to_new: dict[int, int], value: object) -> int | None:
    """A 1-based step number from Claude's list, renumbered after the steps without text were dropped."""
    return old_to_new.get(value) if isinstance(value, int) and not isinstance(value, bool) else None


def phases(value: object, old_to_new: dict[int, int], steps: int) -> list[dict]:
    """Kept only whole: 3 to 5 phases that cover a long journey's steps in order, no gap, no overlap."""
    rows = [
        {
            "nom": cut(p.get("nom"), MAX_SHORT),
            "de": step_index(old_to_new, p.get("de")),
            "a": step_index(old_to_new, p.get("a")),
        }
        for p in _rows(value)
    ]
    if steps < PHASED_FROM or not MIN_PHASES <= len(rows) <= MAX_PHASES:
        return []
    expected = 1
    for row in rows:
        if row["de"] != expected or row["a"] is None or row["a"] < row["de"]:
            return []
        expected = row["a"] + 1
    return rows if expected == steps + 1 else []


def main_journey(journeys: list[dict], components: list[dict], block_ids: set[str]) -> None:
    """Exactly one journey is the main one. Without one declared, the floor's own rule picks it (most
    components that have a part, then most steps, then model order), marked as deduced."""
    declared = [j for j in journeys if j.get("principal")]
    for journey in journeys:
        journey["principal"] = False
        journey.pop("principal_deduit", None)
    if declared:
        declared[0]["principal"] = True
        return
    owner = {c["id"]: c["bloc"] for c in components}

    def score(j: dict) -> tuple[int, int]:
        parts = {
            s["composant"]
            for s in j["etapes"]
            if s["composant"] and owner.get(s["composant"], s["composant"]) in block_ids
        }
        return len(parts), len(j["etapes"])

    if journeys:
        best = max(enumerate(journeys), key=lambda pair: (score(pair[1]), -pair[0]))[1]
        best["principal"] = True
        best["principal_deduit"] = True


def touched_blocks(journeys: list[dict], components: list[dict]) -> set[str]:
    owner = {c["id"]: c["bloc"] for c in components}
    touched: set[str | None] = set()
    for journey in journeys:
        touched |= {journey.get("entree")} | set(journey.get("sortie") or [])
        for step in journey["etapes"]:
            touched |= set(step["touche"]) | {owner.get(step["composant"] or "", step["composant"])}
    return {b for b in touched if isinstance(b, str) and b}


def derived_blocks(blocks: list[dict], components: list[dict], journeys: list[dict]) -> None:
    """A part no journey touches cannot sit in a data zone (it is the workshop); what « Entrer » shows
    in a part without components is derived from its type, never asked."""
    touched = touched_blocks(journeys, components)
    with_parts = {c["bloc"] for c in components}
    for block in blocks:
        # Without any journey nothing says what runs: zones stay as written.
        if journeys and block["id"] not in touched and block["zone"] in ("recoit", "traite", "range"):
            block["zone"] = "atelier"
        if block["id"] in with_parts:
            block["interieur"] = ""
        elif block["type"] == "user":
            block["interieur"] = "personne"
        elif block["type"] in ("external", "ml_model"):
            block["interieur"] = "externe"
        else:
            block["interieur"] = "fichiers"

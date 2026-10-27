"""The Level 0 project map from hard signals, without any LLM (ADR-0007): who comes in, the parts that
run (≤ 6 boxes), what they call, what leaves (◉), and what sits around. Layout is placed apart
(`system_layout`) and stored, so the map never moves."""

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.system_around import DB_ADMIN, PROXIES, around_items, image_name
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_links import Externals, unit_links
from umbra_engine.projection.system_model import (
    Proof,
    SystemBox,
    SystemLink,
    SystemMap,
    SystemOutput,
    proof_of,
)
from umbra_engine.projection.system_units import TOOLING_SERVICE, Unit, find_units, test_service

MAX_BOXES = 6  # running parts; the actors come on top (ADR-0007: ≤ 5 by default, hard max 7)
TITLES = {"web": "Application web", "server": "Serveur", "cli": "Commande", "library": "Bibliothèque"}
STORES = {
    "postgres": "PostgreSQL", "postgis": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB",
    "mongo": "MongoDB", "redis": "Redis", "valkey": "Valkey", "clickhouse": "ClickHouse",
}  # fmt: skip
MAIL_CATCHERS = ("mailcatcher", "mailhog", "mailpit", "maildev", "smtp4dev")
FORMATS = {"json": "JSON", "csv": "CSV", "table": "tableau"}


def system_map(facts: Facts, branch: str, last_change: str) -> SystemMap:
    units = find_units(facts)
    result = SystemMap(facts.name, "", branch, last_change)
    boxes = {u.id: _unit_box(facts, u) for u in units}
    prestart: list[str] = []
    others: list[SystemBox] = []
    stand_ins: list[StoredClaim] = []
    for service in facts.services.values():
        image = image_name(service)
        if service.code_root is not None:
            if service.name.lower().startswith(TOOLING_SERVICE):
                prestart.append(service.name)
        elif image.startswith(tuple(STORES)):
            engine = next(STORES[k] for k in STORES if image.startswith(k))
            title = "Cache" if engine in ("Redis", "Valkey") else "Base"
            role = "Garde les données en mémoire." if title == "Cache" else "Garde les données du projet."
            boxes[f"store:{service.name}"] = SystemBox(
                f"store:{service.name}", "box", title, engine, "", role, _declared(service.declared)
            )
        elif image.startswith(MAIL_CATCHERS):
            stand_ins += service.declared[:1]
        elif not test_service(service.name) and not _around_service(image, service.name):
            proofs = _declared(service.declared)
            others.append(SystemBox(f"service:{service.name}", "box", service.name, image or "service", "",
                                    "Un service déclaré dans compose.", proofs))  # fmt: skip
    externals = Externals(boxes, stand_ins)
    links = unit_links(facts, units, externals)
    boxes.update(externals.boxes)
    for box in others:
        boxes.setdefault(box.id, box)
    links = _actors(units, boxes) + links
    running = [b for b in boxes.values() if b.kind != "actor"]
    overflow = running[MAX_BOXES:]
    result.boxes = [boxes[k] for k in boxes if k not in {b.id for b in overflow}]
    shown = {b.id for b in result.boxes}
    result.links = [link for link in links if link.source in shown and link.target in shown]
    result.outputs = [o for o in _outputs(facts, units, result.links, boxes) if o.box in shown]
    extra = [(b.title, b.detail, b.proofs) for b in overflow]
    if stand_ins and "mail" not in boxes:
        catchers = ", ".join(c.object.split(":", 1)[1] for c in stand_ins)
        extra.append(("Courriel de test", catchers, _declared(stand_ins)))
    result.around = around_items(facts, prestart, extra)
    result.actions = sum(len(facts.signal("route", u.files)) for u in units if u.role == "server") + sum(
        len(facts.commands(u.files)) for u in units if u.role == "cli"
    )
    result.sentence = _sentence(units, result.links)
    return result


def _around_service(image: str, name: str) -> bool:
    """Tools listed in « + N autour » (see `around_items`), never boxes."""
    return image.startswith(DB_ADMIN + PROXIES) or name.lower() == "proxy"


def _declared(claims: list[StoredClaim]) -> list[Proof]:
    return [proof_of(c) for c in claims[:3]]


def _unit_box(facts: Facts, unit: Unit) -> SystemBox:
    services = [c for s in unit.services for c in facts.services[s].declared[:1]]
    proofs = [proof_of(c) for c in unit.proofs[:3] + services[:2]]
    title = TITLES.get(unit.role) or unit.root.rsplit("/", 1)[-1] or facts.name
    roles = {
        "web": "Les écrans dans le navigateur.",
        "server": "Reçoit les appels et y répond.",
        "cli": "Lit ce qui est tapé dans le terminal et fait le travail demandé.",
        "library": "Le code que d'autres programmes importent.",
        "folder": "Un dossier de code : son rôle n'est pas lu dans le code (supposé).",
    }
    return SystemBox(unit.id, "box", title, unit.detail, unit.folder, roles[unit.role], proofs, unit.inferred)


def _actors(units: list[Unit], boxes: dict[str, SystemBox]) -> list[SystemLink]:
    """Who comes in, for each kind of entry. A person is never read in the code: always « supposé »."""
    links: list[SystemLink] = []

    def actor(
        key: str, title: str, detail: str, role: str, target: Unit, verb: str, back: str, how: str
    ) -> None:
        proofs = [proof_of(c) for c in target.proofs[:2]]
        boxes[key] = SystemBox(key, "actor", title, detail, "", role, proofs, inferred=True)
        links.append(SystemLink(f"{key}>{target.id}", key, target.id, verb, back, how, proofs))

    roles = {u.role: u for u in reversed(units)}
    guess = "Supposé : déduit"
    if "web" in roles:
        role = f"Une personne dans un navigateur. {guess} de l'application web."
        actor(
            "actor:user",
            "Utilisateur",
            "navigateur",
            role,
            roles["web"],
            "clique",
            "affiche",
            "clavier et souris",
        )
    elif "server" in roles:
        role = f"Un programme qui appelle le serveur. {guess} du serveur."
        actor("actor:client", "Client", "appel HTTP", role, roles["server"], "appelle", "répond", "HTTP")
    if "cli" in roles:
        cli = roles["cli"]
        role = f"Tape la commande. {guess} de la commande déclarée."
        actor("actor:terminal", "Personne", "dans un terminal", role, cli, "tape", "", cli.detail)
    if "library" in roles:
        lib = roles["library"]
        title = "Programme Python" if any(f.endswith(".py") for f in lib.files) else "Programme"
        role = f"Un autre programme qui utilise la bibliothèque. {guess} de ce qu'elle exporte."
        actor(
            "actor:program",
            title,
            f"import {lib.root.rsplit('/', 1)[-1]}",
            role,
            lib,
            "importe",
            "",
            "import",
        )
    return links


def _outputs(
    facts: Facts, units: list[Unit], links: list[SystemLink], boxes: dict[str, SystemBox]
) -> list[SystemOutput]:
    outputs: list[SystemOutput] = []
    for unit in units:
        if unit.role == "web":
            proofs = [proof_of(c) for c in facts.signal("ui-render", unit.files)[:3]] or boxes[unit.id].proofs
            outputs.append(SystemOutput(f"out:{unit.id}", unit.id, "écran mis à jour", "", proofs))
        if unit.role == "server" and not any(u.role == "web" for u in units):
            proofs = [proof_of(c) for c in facts.signal("route", unit.files)[:3]]
            outputs.append(SystemOutput(f"out:{unit.id}", unit.id, "réponse envoyée", "", proofs))
        prints = facts.signal("print", unit.files)
        if unit.role == "cli" and prints:
            formats = [FORMATS[k] for k in FORMATS if facts.signal(f"format:{k}", unit.files)]
            proofs = [proof_of(c) for c in prints[:3]]
            outputs.append(
                SystemOutput(f"out:{unit.id}", unit.id, "résultat affiché", ", ".join(formats), proofs)
            )
    for link in links:
        if link.target.startswith("store:") and link.verb == "écrit":
            outputs.append(
                SystemOutput(f"out:{link.target}", link.target, "ligne enregistrée", "", link.proofs)
            )
        elif link.target == "mail":
            outputs.append(SystemOutput("out:mail", "mail", "courriel envoyé", "", link.proofs))
        elif link.target == "sqlite-file" and "écrit" in link.verb:
            outputs.append(
                SystemOutput("out:sqlite-file", "sqlite-file", "fichier .db modifié", "", link.proofs)
            )
    return list({o.id: o for o in outputs}.values())


def _sentence(units: list[Unit], links: list[SystemLink]) -> str:
    """One plain sentence from the boxes found (Claude's own sentence comes with #108)."""
    roles = [u.role for u in units]
    if "web" in roles and "server" in roles:
        subject, last = "Une application web et son serveur", "server"
    elif "cli" in roles and "library" in roles:
        python = any(f.endswith(".py") for u in units if u.role == "library" for f in u.files)
        subject, last = f"Une commande et une bibliothèque{' Python' if python else ''}", "library"
    else:
        named = {"web": "Une application web", "server": "Un serveur", "cli": "Une commande",
                 "library": "Une bibliothèque"}  # fmt: skip
        first = next((r for r in ("server", "web", "cli", "library") if r in roles), None)
        if first is None:
            return f"{len(units)} parties trouvées dans les dossiers du projet." if units else ""
        subject, last = named[first], first
    owner = {u.id for u in units if u.role == last}
    does = []
    for link in links:
        if link.source in owner and link.target.startswith("store:"):
            does.append("écrit dans une base" if link.verb == "écrit" else "lit une base")
        elif link.source in owner and link.target == "sqlite-file":
            does.append(f"{link.verb} un fichier SQLite")
        elif link.source in owner and link.target == "mail":
            does.append("envoie des courriels")
    does = list(dict.fromkeys(does))
    return f"{subject}, qui {' et '.join(does)}." if does else f"{subject}."

"""Arrows between the running parts, and the outside things they reach (a database, a mail server, an
SQLite file), each from the lines that do it: an HTTP client, an import, a driver, an SMTP call."""

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.system_around import TEST_FILE
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_model import Proof, SystemBox, SystemLink, proof_of
from umbra_engine.projection.system_units import Unit

ENGINES = {
    "psycopg": "PostgreSQL", "psycopg2": "PostgreSQL", "asyncpg": "PostgreSQL", "pg": "PostgreSQL",
    "pymysql": "MySQL", "MySQLdb": "MySQL", "mysql2": "MySQL", "pymongo": "MongoDB", "motor": "MongoDB",
    "mongoose": "MongoDB", "better-sqlite3": "SQLite",
}  # fmt: skip
LIBRARIES = {
    "sqlmodel": "SQLModel", "sqlalchemy": "SQLAlchemy", "django.db": "Django", "@prisma/client": "Prisma",
    "typeorm": "TypeORM", "sequelize": "Sequelize", "knex": "Knex", "drizzle-orm": "Drizzle",
}  # fmt: skip
GENERATED = ("/client/", ".gen.", "/generated/")
SHOWN = 3


class Externals:
    """The outside boxes met while reading the parts: made once, shared by every part that reaches them."""

    def __init__(self, existing: dict[str, SystemBox], stand_ins: list[StoredClaim]) -> None:
        self.existing = existing
        self.stand_ins = stand_ins
        self.boxes: dict[str, SystemBox] = {}

    def stores(self, drivers: list[StoredClaim]) -> list[SystemBox]:
        declared = [b for b in self.existing.values() if b.id.startswith("store:") and b.title == "Base"]
        if declared:
            return declared
        names = [_driver(c) for c in drivers]
        engine = next((ENGINES[n] for n in names if n in ENGINES), "SQL")
        role = "Garde les données. Supposé : aucune base déclarée, déduite du code qui s'y connecte."
        box = SystemBox("store:code", "box", "Base", engine, "", role, ranked(drivers), inferred=True)
        return [self.boxes.setdefault(box.id, box)]

    def sqlite(self, opens: list[StoredClaim]) -> SystemBox:
        role = "La base est un simple fichier, ouvert avec sqlite3."
        box = SystemBox(
            "sqlite-file", "box", "Fichier SQLite", "un .db sur le disque", "", role, ranked(opens)
        )
        return self.boxes.setdefault(box.id, box)

    def mail(self, sends: list[StoredClaim]) -> SystemBox:
        catchers = [c.object.split(":", 1)[1] for c in self.stand_ins]
        role = "Envoie les courriels." + (
            f" En local, {', '.join(catchers)} les attrape." if catchers else ""
        )
        proofs = ranked(sends) + [proof_of(c) for c in self.stand_ins]
        box = SystemBox("mail", "external", "Courriel", "service externe", "", role, proofs)
        return self.boxes.setdefault(box.id, box)


def unit_links(facts: Facts, units: list[Unit], externals: Externals) -> list[SystemLink]:
    links: list[SystemLink] = []
    servers = [u for u in units if u.role == "server"]
    for web in (u for u in units if u.role == "web"):
        calls = facts.signal("http-client", web.files)
        if calls and servers:
            target = servers[0]
            links.append(
                _link(web, target.id, "appelle", "répond", "HTTP + JSON", ranked(calls), len(servers) > 1)
            )
    libraries = [u for u in units if u.role == "library"]
    for cli in (u for u in units if u.role == "cli"):
        for library in libraries:
            imports = [c for c in facts.module_links if c.subject in cli.files and c.object in library.files]
            if imports:
                links.append(
                    _link(cli, library.id, "appelle", "", f"{len(imports)} imports", ranked(imports))
                )
    for unit in units:
        writes = facts.signal("db-write", unit.files)
        drivers = facts.signals_starting("db-driver:", unit.files)
        if drivers:
            verb = "écrit" if writes else "lit"
            names = list(dict.fromkeys(LIBRARIES.get(_driver(c), _driver(c)) for c in drivers))
            proofs = (ranked(writes)[:2] + ranked(drivers))[:SHOWN]
            for store in externals.stores(drivers):
                links.append(_link(unit, store.id, verb, "", f"SQL via {', '.join(names[:2])}", proofs))
        opens = facts.signal("sqlite", unit.files)
        if opens:
            verb = "lit et écrit" if writes else "lit"
            proofs = (ranked(opens)[:2] + ranked(writes))[:SHOWN]
            links.append(
                _link(unit, externals.sqlite(opens).id, verb, "", "sqlite3.connect(fichier)", proofs)
            )
        sends = facts.signal("smtp", unit.files)
        if sends:
            how = "SMTP" + (", attrapé en local" if externals.stand_ins else "")
            links.append(_link(unit, externals.mail(sends).id, "envoie", "", how, ranked(sends)))
    return links


def ranked(claims: list[StoredClaim]) -> list[Proof]:
    """The lines a person would open first: hand-written code before generated code and tests."""

    def rank(claim: StoredClaim) -> tuple[bool, bool, str, int]:
        generated = any(g in claim.file for g in GENERATED)
        return bool(TEST_FILE.search(claim.file)), generated, claim.file, claim.line_start

    order = sorted(claims, key=rank)
    return [proof_of(c) for c in order[:SHOWN]]


def _driver(claim: StoredClaim) -> str:
    return claim.object.removeprefix("signal:db-driver:")


def _link(
    unit: Unit, target: str, verb: str, back: str, how: str, proofs: list[Proof], guess: bool = False
) -> SystemLink:
    return SystemLink(f"{unit.id}>{target}", unit.id, target, verb, back, how, proofs, guess)

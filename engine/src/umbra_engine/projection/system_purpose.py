"""The sentence under the project's name: what the project is FOR, from hard signals only (no LLM,
ADR-0007). It must add to the map, never repeat its boxes: who uses it (accounts) and what they handle
(the tables of the code), or what a tool does to its data. Claude's own sentence comes with #108."""

from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_model import SystemLink
from umbra_engine.projection.system_units import Unit

ACCOUNT_TABLES = {"user", "account", "profile", "session", "token", "role", "permission", "group"}
MAX_THINGS = 3


def purpose(facts: Facts, units: list[Unit], links: list[SystemLink]) -> str:
    roles = {u.role for u in units}
    python = any(f.endswith(".py") for u in units if u.role == "library" for f in u.files)
    library = f"une bibliothèque{' Python' if python else ''}"
    if "web" in roles or "server" in roles:
        subject = "Une appli web" if "web" in roles else "Un serveur"
        return _accounts_and_things(facts, subject)
    if "cli" in roles and "library" in roles:
        subject = f"Un outil en ligne de commande et {library}"
    elif "cli" in roles:
        subject = "Un outil en ligne de commande"
    elif "library" in roles:
        subject = library[0].upper() + library[1:]
    else:
        return f"{len(units)} parties trouvées dans les dossiers du projet." if units else ""
    return f"{subject}{_for_data(links)}."


def _accounts_and_things(facts: Facts, subject: str) -> str:
    """« Une appli web avec comptes : on se connecte, on gère ses « items ». »"""
    kept = things(facts)
    named = " et ".join(f"« {t} »" for t in kept)
    if facts.signal("auth"):
        return f"{subject} avec comptes : on se connecte" + (f", on gère ses {named}." if kept else ".")
    return f"{subject} : on gère des {named}." if kept else f"{subject}."


def things(facts: Facts) -> list[str]:
    """What the app keeps, from its table classes (SQLModel, Django, SQLAlchemy), accounts left out."""
    names = [c.object.split(":", 2)[2] for c in facts.signals_starting("table:")]
    names += [c.object.split(":", 2)[2] for c in facts.signals_starting("tablename:")]
    found: list[str] = []
    for name in names:
        word = name.lower()
        if word.rstrip("s") in ACCOUNT_TABLES:
            continue
        plural = word if word.endswith("s") else f"{word}s"
        if plural not in found:
            found.append(plural)
    return found[:MAX_THINGS]


def _for_data(links: list[SystemLink]) -> str:
    """What a tool does to the data it reaches: « pour remplir et modifier des fichiers SQLite »."""
    for link in links:
        does = "remplir et modifier" if "écrit" in link.verb else "lire"
        if link.target == "sqlite-file":
            return f" pour {does} des fichiers SQLite"
        if link.target.startswith("store:"):
            return f" pour {does} une base"
    return ""

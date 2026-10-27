"""The words of a part inside a box (Level 1): one plain French role word as its title, repo names under
it, and one sentence on hover. Only what the code shows: table names, page files, screen folders."""

import posixpath
from collections import Counter

from umbra_engine.projection.inside_parts import Group, is_generated
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_purpose import ACCOUNT_TABLES, things
from umbra_engine.projection.system_units import main_classes

TITLES = {
    "entry": "Porte d'entrée", "routes": "Routes", "access": "Contrôle d'accès", "models": "Modèles",
    "data": "Accès aux données", "pages": "Pages", "screens": "Écrans", "client": "Client",
    "session": "Connexion", "plugins": "Extensions",
}  # fmt: skip
STEM_TITLES = {
    "utils": "Outils", "util": "Outils", "helpers": "Outils", "tools": "Outils", "common": "Outils",
    "migrations": "Migrations", "cli": "Commande", "__main__": "Lancement", "config": "Réglages",
    "settings": "Réglages", "parser": "Lecture", "templates": "Modèles de pages", "static": "Fichiers fixes",
}  # fmt: skip
ROLES = {
    "access": "Vérifie qui appelle avant de répondre.",
    "models": "La forme des données : champs, longueurs, tables.",
    "data": "Lit et écrit les données.",
    "screens": "Formulaires, tableaux, menus de chaque page.",
    "session": "Garde la preuve de connexion dans le navigateur.",
    "plugins": "D'autres paquets s'y branchent pour ajouter ce qu'ils font.",
}
PAGE_WORDS = {
    "login": "connexion", "signin": "connexion", "sign-in": "connexion", "signup": "inscription",
    "sign-up": "inscription", "register": "inscription", "settings": "réglages", "home": "accueil",
    "dashboard": "tableau de bord", "profile": "profil",
}  # fmt: skip
SCREEN_WORDS = {"usersettings": "Profil", "user-settings": "Profil", "profile": "Profil", "account": "Compte"}
NOT_A_PAGE = {"", "index", "page", "layout", "root", "route", "+page", "+layout", "app", "_app", "_document"}
NOT_A_SCREEN = {
    "ui",
    "common",
    "shared",
    "layout",
    "layouts",
    "pending",
    "sidebar",
    "icons",
    "utils",
    "hooks",
}
SHOWN = 3


def title_of(group: Group, web: bool) -> str:
    if group.kind == "entry" and web:
        return "Démarrage"
    if group.kind in TITLES:
        return TITLES[group.kind]
    stem = posixpath.splitext(group.kind.split(":", 1)[1])[0]
    word = STEM_TITLES.get(stem.lower()) or next(
        (w for k, w in STEM_TITLES.items() if stem.endswith(f"_{k}")), ""
    )
    return word or stem


def detail_of(facts: Facts, group: Group) -> str:
    if group.kind == "models":
        names = [c.object.split(":", 2)[2] for c in group.claims]
        return " · ".join(list(dict.fromkeys(names))[:SHOWN])
    if group.kind == "data":
        return _tables_handled(facts, group) or main_classes(facts, group.files)[0]
    if group.kind == "pages":
        return " · ".join(_pages(facts, group.files))
    if group.kind == "screens":
        return " · ".join(_screens(facts, group.files))
    if group.kind == "client":
        return "généré" if any(is_generated(f) for f in group.files) else ""
    if group.kind == "session":
        return "garde la preuve"
    if group.kind.startswith("code:") or group.kind == "plugins":
        classes = main_classes(facts, group.files)[0]
        return "" if classes.lower() == title_of(group, False).lower() else classes  # never said twice
    return ""


def role_of(group: Group, web: bool, routes: int) -> str:
    if group.kind == "entry":
        if web:
            return "Lance l'appli et branche les pages."
        if routes:
            return "Crée l'appli et passe les appels aux routes."
        return "Le premier fichier lu : ce que le code donne à qui l'importe."
    if group.kind == "routes":
        return f"Une adresse = une fonction. {routes} adresses en {len(group.chips)} fichiers."
    if group.kind == "pages":
        return f"Une adresse du navigateur = une page. {len(group.files)} fichiers."
    if group.kind == "client":
        made = " Recréées depuis le serveur, pas écrites à la main." if detail_is_generated(group) else ""
        return f"Fonctions d'appel au serveur.{made}"
    return ROLES.get(group.kind, "Une partie du code, rangée à part dans le dossier.")


def detail_is_generated(group: Group) -> bool:
    return any(is_generated(f) for f in group.files)


def table_words(facts: Facts) -> dict[str, str]:
    """Table class name (lower case) → its plain word: « user » → « comptes », « item » → « items »."""
    names = [c.object.split(":", 2)[2] for c in facts.signals_starting("table:")]
    names += [c.object.split(":", 2)[2] for c in facts.signals_starting("tablename:")]
    words: dict[str, str] = {}
    for name in names:
        word = name.lower().rstrip("s")
        words[word] = "comptes" if word in ACCOUNT_TABLES else f"{word}s"
    return words


def _tables_handled(facts: Facts, group: Group) -> str:
    """The tables a data part handles, by the names of its functions: « create_user » → comptes."""
    words = table_words(facts)
    counts: Counter[str] = Counter()
    for claim in facts.functions:
        if claim.file in group.files:
            name = claim.object.split("::", 1)[-1].lower()
            counts.update({words[t] for t in words if t in name.split("_")})
    if not counts:
        return ""
    top = max(counts.values())
    return " · ".join(w for w, n in counts.most_common() if n * 2 >= top)


def _pages(facts: Facts, files: set[str]) -> list[str]:
    """Page names: sign-in first, then the things the app keeps, then the others in alphabetical order."""
    names: list[str] = []
    for f in sorted(files):
        stem = posixpath.splitext(posixpath.basename(f))[0]
        if stem.lower() in NOT_A_PAGE:
            stem = posixpath.basename(posixpath.dirname(f))
        stem = stem.lstrip("_$[(").rstrip("])").lower()
        if stem not in NOT_A_PAGE and not stem.startswith("_"):
            names.append(PAGE_WORDS.get(stem, stem))
    kept = things(facts)
    order = sorted(
        set(names), key=lambda n: (n != "connexion", n not in kept, kept.index(n) if n in kept else 0, n)
    )
    return order[:SHOWN]


def _screens(facts: Facts, files: set[str]) -> list[str]:
    """Screen folders: the things the app keeps first, then the biggest; shared kits left out."""
    sizes: Counter[str] = Counter()
    for f in files:
        parts = f.split("/")
        inside = [
            i for i, p in enumerate(parts[:-1]) if p.lower() in ("components", "features", "screens", "views")
        ]
        if inside and inside[0] + 2 < len(parts) and parts[inside[0] + 1].lower() not in NOT_A_SCREEN:
            sizes[parts[inside[0] + 1]] += 1
    kept = things(facts)

    def rank(name: str) -> tuple[bool, int, str]:
        return name.lower() not in kept, -sizes[name], name

    return [SCREEN_WORDS.get(n.lower(), n) for n in sorted(sizes, key=rank)][:SHOWN]

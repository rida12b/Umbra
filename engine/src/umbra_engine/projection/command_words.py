"""Plain French words for a command (#108, ADR-0008), read in its name as the CLI declares it, never written
by a model. A verb then a thing reads as the two (« create-table » → « Créer une table »); a thing alone is
listed (« tables » → « Lister les tables »); a verb alone stays a verb (« vacuum » → « Compacter »). A word
no rule knows leaves the command unnamed (« »): the panel then shows the command as typed."""

VERBS = {
    "add": "Ajouter", "analyze": "Analyser", "build": "Construire", "convert": "Convertir", "create": "Créer",
    "delete": "Supprimer", "disable": "Désactiver", "drop": "Supprimer", "dump": "Exporter",
    "duplicate": "Copier", "enable": "Activer", "export": "Exporter", "extract": "Extraire",
    "import": "Importer", "index": "Indexer", "init": "Initialiser", "insert": "Insérer",
    "install": "Installer", "list": "Lister", "migrate": "Migrer", "optimize": "Optimiser",
    "populate": "Remplir", "rebuild": "Reconstruire", "remove": "Retirer", "rename": "Renommer",
    "reset": "Remettre à zéro", "run": "Lancer", "search": "Chercher", "show": "Voir",
    "transform": "Transformer", "uninstall": "Désinstaller", "update": "Mettre à jour",
    "upsert": "Insérer ou mettre à jour", "vacuum": "Compacter",
}  # fmt: skip
ADDING = {"add", "create", "import", "insert", "install", "upsert"}  # « des colonnes », not « les colonnes »
ALONE = {"query": "Lancer une requête SQL", "schema": "Voir le schéma"}

# a thing: (one, its article), (many) — the article of « many » is chosen by the verb
THINGS = {
    "column": ("colonne", "une"), "database": ("base", "une"), "file": ("fichier", "un"),
    "foreign-key": ("clé étrangère", "une"), "geometry-column": ("colonne géométrique", "une"),
    "index": ("index", "un"), "package": ("paquet", "un"), "plugin": ("extension", "une"),
    "row": ("ligne", "une"), "spatial-index": ("index spatial", "un"), "table": ("table", "une"),
    "trigger": ("déclencheur", "un"), "user": ("compte", "un"), "view": ("vue", "une"),
}  # fmt: skip
MANY = {
    "columns": "colonnes", "databases": "bases", "files": "fichiers", "foreign-keys": "clés étrangères",
    "indexes": "index", "packages": "paquets", "plugins": "extensions", "rows": "lignes",
    "tables": "tables", "triggers": "déclencheurs", "users": "comptes", "views": "vues",
}  # fmt: skip
WHOLE = {
    "counts": "les compteurs",
    "fts": "la recherche plein texte",
    "schema": "le schéma",
    "wal": "le mode WAL",
}


def label(command: str) -> str:
    name = command.lower().replace("_", "-")
    if name in ALONE:
        return ALONE[name]
    if name in MANY:
        return f"Lister les {MANY[name]}"
    verb, _, rest = name.partition("-")
    if verb not in VERBS:
        return ""
    if not rest:
        return VERBS[verb]
    thing = _thing(rest, verb in ADDING)
    return f"{VERBS[verb]} {thing}" if thing else ""


def _thing(rest: str, adding: bool) -> str:
    if rest in THINGS:
        one, article = THINGS[rest]
        return f"{article} {one}"
    if rest in MANY:
        return f"{'des' if adding else 'les'} {MANY[rest]}"
    return WHOLE.get(rest, "")

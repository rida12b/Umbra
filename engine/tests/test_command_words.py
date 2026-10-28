"""#108 (ADR-0008): the commands of sqlite-utils get plain French words from their names alone, with no
model; a name no rule knows stays unnamed and the panel shows it as typed."""

from umbra_engine.projection.command_words import label

# every command sqlite-utils declares (`sqlite_utils/cli.py`) → its words; « » = unnamed
SQLITE_UTILS = [
    ("tables", "Lister les tables"),
    ("views", "Lister les vues"),
    ("optimize", "Optimiser"),
    ("rebuild-fts", "Reconstruire la recherche plein texte"),
    ("analyze", "Analyser"),
    ("vacuum", "Compacter"),
    ("dump", "Exporter"),
    ("add-column", "Ajouter une colonne"),
    ("add-foreign-key", "Ajouter une clé étrangère"),
    ("add-foreign-keys", "Ajouter des clés étrangères"),
    ("index-foreign-keys", "Indexer les clés étrangères"),
    ("create-index", "Créer un index"),
    ("drop-index", "Supprimer un index"),
    ("enable-fts", "Activer la recherche plein texte"),
    ("populate-fts", "Remplir la recherche plein texte"),
    ("disable-fts", "Désactiver la recherche plein texte"),
    ("enable-wal", "Activer le mode WAL"),
    ("disable-wal", "Désactiver le mode WAL"),
    ("enable-counts", "Activer les compteurs"),
    ("reset-counts", "Remettre à zéro les compteurs"),
    ("insert", "Insérer"),
    ("upsert", "Insérer ou mettre à jour"),
    ("bulk", ""),
    ("create-database", "Créer une base"),
    ("create-table", "Créer une table"),
    ("duplicate", "Copier"),
    ("rename-table", "Renommer une table"),
    ("drop-table", "Supprimer une table"),
    ("create-view", "Créer une vue"),
    ("drop-view", "Supprimer une vue"),
    ("query", "Lancer une requête SQL"),
    ("memory", ""),
    ("search", "Chercher"),
    ("rows", "Lister les lignes"),
    ("triggers", "Lister les déclencheurs"),
    ("indexes", "Lister les index"),
    ("schema", "Voir le schéma"),
    ("transform", "Transformer"),
    ("extract", "Extraire"),
    ("insert-files", "Insérer des fichiers"),
    ("analyze-tables", "Analyser les tables"),
    ("install", "Installer"),
    ("uninstall", "Désinstaller"),
    ("convert", "Convertir"),
    ("add-geometry-column", "Ajouter une colonne géométrique"),
    ("create-spatial-index", "Créer un index spatial"),
    ("plugins", "Lister les extensions"),
]


def test_every_sqlite_utils_command_gets_its_words():
    for command, words in SQLITE_UTILS:
        assert label(command) == words, command


def test_a_python_name_reads_as_the_typed_command():
    assert label("create_table") == label("create-table") == "Créer une table"


def test_a_known_verb_on_an_unknown_thing_stays_unnamed():
    assert label("create-widget") == ""
    assert label("frobnicate") == ""
    assert label("") == ""

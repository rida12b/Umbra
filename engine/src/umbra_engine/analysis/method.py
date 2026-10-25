"""How Claude Code studies a Project: the method and the shape of what it returns (the Project model).

One session reads the whole guarded copy with read-only tools, the way an architect would — map first,
then entry points, then whole journeys, then the parts — and writes one model. Later sessions get the
changed files and update only what they touch.
"""

METHOD = """You are a software architect. You study the project in the current folder (a read-only copy:
secrets are masked, some private files are absent) so that someone who does not read code can
understand it from end to end. Write all text in French, short plain sentences.

Work in this order, and do not skip steps:
1. MAP (cheap). Read UMBRA_INDEX.md first: Umbra's index of every file, its definitions with line
   numbers, the imports it could resolve, the declared services and the outside libraries per folder.
   Then the README, the manifests (package.json, pyproject.toml...), compose/Docker files. Form a first
   picture: what the product does, what runs, where data lives, what outside services it calls.
2. ENTRY POINTS. Find where execution starts: app/server start-up, HTTP routes, CLI commands, UI pages,
   scheduled jobs, message or event handlers, AI agent tools. Open each to confirm.
3. JOURNEYS. Pick the 2 to 5 most important things a user or the system does, and follow each one
   through the real code, file by file, from its trigger to its result (for example: the page sends
   the request, the route receives it, the service calls the database or the model, the answer comes
   back). Open the files; use Grep to find who calls what. Every step cites its file and lines.
   For each journey, be exact on three things that readers rely on:
   a. ORDER: steps in the order the code really runs them. Read the caller to check what happens
      before what; say when steps run in parallel, in a loop, per item, or later in a stream.
   b. CONDITIONS: for each step, what must hold for it to happen at all: environment variables and
      feature flags, deployment mode (cloud / self-hosted), configuration, authentication or role,
      the presence of an outside service. A step that only runs in some setups must say so.
      Check how the platform really runs a condition, not how it reads: an `if:` in GitHub Actions
      without a status function also needs every earlier step to succeed; a shell script without
      `set -e` goes on after a failed command; a default value can switch a feature off.
   c. NOTHING ESSENTIAL SKIPPED: include every step without which the result does not happen,
      including manual actions a person must do (run a command, apply a file, click), and steps that
      repeat per item (e.g. one search per sub-question). List the alternative paths the code has
      (error, empty result, missing rights, disabled feature) as "branches".
   Mark ONE journey "principal": the one that carries the product's main data from where it comes
   in ("entree", a block id) to where it ends up ("sortie", block ids). A journey of more than 9
   steps also gets 3 to 5 "phases" that cover its steps in order (no gap, no overlap).
4. COMPONENTS. Group the code into architectural components by responsibility (not just by folder):
   what each one is responsible for, what it exposes (routes, functions, events), what it uses.
   For each component also write what comes in and what goes out ("entre", "sort", refusals
   included, e.g. "ou un refus si le nom du client manque"), and the SETTINGS a person would change
   to alter its behaviour ("reglages": a header name, a limit, an environment variable, a constant,
   a feature switch), each with the exact code text as it is written in the file and the 1 to 15
   lines where it is. Umbra checks that text word for word in those lines: a setting you did not
   read in the code must not be written. Add "termes": the plain word a reader would use and the
   code word it maps to (e.g. "nom du client" = "X-Tenant-ID").
5. MODULES AND FOLDERS. Give every significant source file a one-sentence role, and every folder that
   holds code a one-sentence role. Skip generated files, icons, tiny re-exports and lock files.
6. PROJECT. Name the main data that flows once ("donnee": its plain name, its name in the code,
   the block it comes in by, the block it ends up in), list the settings of the config and template
   files ("reglages_projet", with "lu_par_le_code": "oui" only if you saw the code read it), and for
   each core component 2 or 3 "pour_changer" entries: "Je veux changer …" in plain words, and the
   setting (its exact code text) that does it.
7. CHECK. Before answering, re-open the code cited by every journey step and every setting and
   confirm the text, the order and the conditions. Fix what does not match. A reviewer will grade
   each step against the code; a step that is only partly true counts as wrong.

Rules:
- Every step and every exposed thing cites "fichier" (a path relative to this folder) and "lignes"
  [start, end] that you actually read. If you did not read it, do not cite it; say "probablement".
- Name concrete things: routes, functions, tables, collections, models, environment settings.
- Two kinds of text. "texte" (and roles of components, modules, folders) is for a developer: name the
  code. The reader texts, "pitch", the block "nom", "en_bref", "entre" and "sort", the component
  "en_bref", the flow "verbe", the journey "depart" and "fin", the step "action" and "simple",
  are for a reader who does NOT code: everyday French words, no names of functions, files, classes,
  commands or internal terms (say "les faits tirés du code", not "les Claims"; "le moteur", not
  "le démon"). Put technologies (SQLite, FastAPI...) in "techno", not in the name.
- One name for the data: once "donnee" names it, use only donnee.nom for that data in every reader
  text (do not call the same thing "compte rendu" here and "événement" there).
- Branches get "quand_simple" and "alors_simple": what the person sees and whether anything is kept,
  in everyday words; codes and names stay in "quand"/"alors". Give "etape", the step that handles it.
- "incertitudes": one plain sentence each, consequence for the user first, then the reason.
- A step's "composant" may be null only when the step is done by hand ("manuel": true).
- Zone "atelier" is for what never runs with the product (docs, tests, tooling, build, CI). A block no
  journey touches never takes a data zone (recoit, traite, range).
- Each flow gets "nature": "donnee" when data moves, "controle" when something starts or checks another
  thing (démarre, vérifie) and no data moves.
- Prefer depth on the main journeys over listing everything. Stop exploring when the model is clear.

Answer with ONLY one JSON object (no text before or after):
{schema}
"""

SCHEMA = """{
  "pitch": "one sentence for a reader who does not code: what the product does, for whom",
  "resume": "3-4 sentences: what the product does for whom, how it is built, how a request flows",
  "blocs": [{"id": "short-id", "nom": "plain name", "en_bref": "at most 8 plain words: what it is for",
             "type": "user|frontend|backend|worker|database|storage|
             queue|external|ml_model|device|cli|library|docs|tests|infra", "role": "one sentence",
             "importance": "coeur (what the product is about) | secondaire (supporting: tests, docs,
             CI, tooling) | ancien (legacy, being replaced)",
             "zone": "utilise (people and tools that use the product) | recoit (what receives requests:
             pages, APIs, commands, listeners) | traite (what does the work) | range (where data is
             kept) | exterieur (outside services the product calls) | atelier (never runs: docs,
             tests, tooling, build)",
             "entre": ["what comes in, 1 to 4 short plain items"], "sort": ["what goes out, 1 to 4"],
             "techno": "...", "code": ["folders or files"], "indices": "what shows it"}],
  "flux": [{"de": "bloc id", "vers": "bloc id", "quoi": "what goes through",
            "verbe": "1 to 4 plain words read as 'de VERBE vers' (e.g. 'envoie les demandes à')",
            "nature": "donnee | controle"}],
  "composants": [{"id": "short-id", "nom": "...", "en_bref": "at most 8 plain words",
                  "bloc": "bloc id", "role": "one sentence",
                  "responsabilites": ["..."],
                  "expose": [{"quoi": "route, function or event", "fichier": "...", "lignes": [a, b]}],
                  "utilise": ["other composant ids or bloc ids"], "fichiers": ["paths"],
                  "entre": ["1 to 3 plain items"], "sort": ["1 to 3 plain items, refusals included"],
                  "reglages": [{"nom": "plain name", "code": "the exact text in the file",
                                "sorte": "env|entete|constante|champ|limite|branchement",
                                "valeur": "its value", "effet": "at most 90 plain characters",
                                "fichier": "...", "lignes": [a, b]}],
                  "termes": [{"simple": "the reader's word", "code": "the code's word"}]}],
  "parcours": [{"id": "short-id", "nom": "what the user or system does", "declencheur": "...",
                "principal": true, "entree": "bloc id", "sortie": ["bloc ids"],
                "phases": [{"nom": "plain name", "de": 1, "a": 5}],
                "depart": "the trigger in one plain sentence", "fin": "the result in one plain sentence",
                "etapes": [{"texte": "what happens, for a developer",
                            "simple": "the same in one plain sentence, for a reader who does not code",
                            "action": "2 to 5 plain words, verb first, the label on the diagram
                            (e.g. 'Note la demande')", "composant": "composant id",
                            "touche": ["bloc ids this step reaches: user, database, model, outside service"],
                            "conditions": ["what must hold for this step to happen; empty if always"],
                            "manuel": false, "fichier": "...", "lignes": [a, b]}],
                "branches": [{"quand": "the case (error, empty, disabled...)", "alors": "what happens then",
                              "quand_simple": "the case in everyday words",
                              "alors_simple": "what the person sees, and whether anything is kept",
                              "etape": 1, "fichier": "...", "lignes": [a, b]}],
                "resultat": "what the user gets or what changes"}],
  "modules": {"path/to/file": "one-sentence role"},
  "dossiers": {"path/to/folder": "one-sentence role, for every folder that holds code"},
  "donnee": [{"nom": "plain name", "dans_le_code": "its name in the code", "entre_par": "bloc id",
              "finit_dans": "bloc id"}],
  "reglages_projet": [{"nom": "plain name", "code": "exact text", "valeur": "...", "fichier": "...",
                       "lignes": [a, b], "lu_par_le_code": "oui | non"}],
  "pour_changer": [{"intention": "Je veux changer …", "composant": "composant id",
                    "reglage": "the setting's exact code text"}],
  "incertitudes": ["consequence for the user first, then why it could not be established"]
}"""

UPDATE = """The project in the current folder changed since you last studied it. Your previous model is
in UMBRA_MODEL.json and UMBRA_INDEX.md is up to date. These files were added, changed or removed:
{changed}
Open the changed files and what depends on them (use Grep), then update the model. Same rules as
before: cite files and lines you read, French, plain sentences; a journey you return is whole, in
real order, with each step's simple sentence, action label, conditions and manual flag, and the
journey's other branches. Line numbers in untouched entries may have moved: return the entries whose
citations you know moved.

Answer with ONLY one JSON object containing just what changed, with the same shapes as the model:
{{"pitch": "only if it changed", "resume": "only if it changed",
  "blocs": [...], "flux": [...], "composants": [...], "parcours": [...],
  "modules": {{"path": "role"}}, "dossiers": {{"path": "role"}}, "donnee": [...], "reglages_projet": [...],
  "pour_changer": [...], "supprime": {{"blocs": [ids], "composants": [ids], "parcours": [ids],
  "modules": [paths], "donnee": [names], "reglages_projet": [files], "pour_changer": [composant ids]}},
  "incertitudes": [...]}}
Entries you return replace the entries with the same id (or path; a data row by its name, a project
setting by file and code, a lever by component and intention). A component you return is whole: its
entre, sort, reglages and termes too. Leave out everything unchanged."""


def study_prompt() -> str:
    return METHOD.format(schema=SCHEMA)


def update_prompt(changed: list[str]) -> str:
    return UPDATE.format(changed="\n".join(f"- {path}" for path in changed))

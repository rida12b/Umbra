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
4. COMPONENTS. Group the code into architectural components by responsibility (not just by folder):
   what each one is responsible for, what it exposes (routes, functions, events), what it uses.
5. MODULES AND FOLDERS. Give every significant source file a one-sentence role, and every folder that
   holds code a one-sentence role. Skip generated files, icons, tiny re-exports and lock files.

Rules:
- Every step and every exposed thing cites "fichier" (a path relative to this folder) and "lignes"
  [start, end] that you actually read. If you did not read it, do not cite it; say "probablement".
- Name concrete things: routes, functions, tables, collections, models, environment settings.
- Prefer depth on the main journeys over listing everything. Stop exploring when the model is clear.

Answer with ONLY one JSON object (no text before or after):
{schema}
"""

SCHEMA = """{
  "resume": "3-4 sentences: what the product does for whom, how it is built, how a request flows",
  "blocs": [{"id": "short-id", "nom": "...", "type": "user|frontend|backend|worker|database|storage|
             queue|external|ml_model|device|cli|library|docs|tests|infra", "role": "one sentence",
             "techno": "...", "code": ["folders or files"], "indices": "what shows it"}],
  "flux": [{"de": "bloc id", "vers": "bloc id", "quoi": "what goes through"}],
  "composants": [{"id": "short-id", "nom": "...", "bloc": "bloc id", "role": "one sentence",
                  "responsabilites": ["..."],
                  "expose": [{"quoi": "route, function or event", "fichier": "...", "lignes": [a, b]}],
                  "utilise": ["other composant ids or bloc ids"], "fichiers": ["paths"]}],
  "parcours": [{"id": "short-id", "nom": "what the user or system does", "declencheur": "...",
                "etapes": [{"texte": "what happens", "composant": "composant id",
                            "fichier": "...", "lignes": [a, b]}],
                "resultat": "what the user gets or what changes"}],
  "modules": {"path/to/file": "one-sentence role"},
  "dossiers": {"path/to/folder": "one-sentence role, for every folder that holds code"},
  "incertitudes": ["what could not be established, and why"]
}"""

UPDATE = """The project in the current folder changed since you last studied it. Your previous model is
in UMBRA_MODEL.json and UMBRA_INDEX.md is up to date. These files were added, changed or removed:
{changed}
Open the changed files and what depends on them (use Grep), then update the model. Same rules as
before: cite files and lines you read, French, plain sentences. Line numbers in untouched entries
may have moved: return the entries whose citations you know moved.

Answer with ONLY one JSON object containing just what changed, with the same shapes as the model:
{{"resume": "only if it changed", "blocs": [...], "flux": [...], "composants": [...], "parcours": [...],
  "modules": {{"path": "role"}}, "dossiers": {{"path": "role"}}, "supprime": {{"blocs": [ids],
  "composants": [ids], "parcours": [ids], "modules": [paths]}}, "incertitudes": [...]}}
Entries you return replace the entries with the same id (or path). Leave out everything unchanged."""


def study_prompt() -> str:
    return METHOD.format(schema=SCHEMA)


def update_prompt(changed: list[str]) -> str:
    return UPDATE.format(changed="\n".join(f"- {path}" for path in changed))

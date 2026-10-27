# Umbra engine (System Explorer V1, in development)

Local daemon that registers Projects, keeps one isolated store per Project and exposes them through a local API. See `../SPEC.md` for the V1 scope.

## Try it on your project (Windows, macOS, Linux)

You need Python 3.11–3.13, [pipx](https://pipx.pypa.io) and [Claude Code](https://claude.com/claude-code) signed in
with a claude.ai subscription (run `claude` once). Umbra asks your own Claude Code to study the project.

```bash
pipx install https://github.com/rida12b/Umbra/releases/download/engine-v0.1.0/umbra_engine-0.1.0-py3-none-any.whl
umbra-engine start path/to/your/project
```

`start` registers the folder, indexes it, runs the engine and opens your browser on the project. The first study
takes a few minutes. Next time, run the same command: only changed files are read again.

**On a server or a VM without a screen**, the engine only answers on `127.0.0.1`, on purpose: it shows your code.
Run `umbra-engine start <folder> --no-browser` there, open a tunnel from your own computer with
`ssh -L 7811:127.0.0.1:7811 you@server`, then open the printed link in your browser (it works once, for 2 minutes;
`umbra-engine open` on the server prints a new one).

## Install from the repository (to work on Umbra)

Requirements: Python 3.11–3.13, Git and Node.js 20.19+ (for the web app), all on `PATH`.

```powershell
git clone https://github.com/rida12b/Umbra.git
cd Umbra
python -m pip install -e ".\engine[dev]"
cd ui; npm ci; npm run build; cd ..   # builds the web app into the engine package
umbra-engine --help
```

The command is `umbra-engine` while the v0.7 `umbra` command still exists; it becomes `umbra` when v0.7 is removed.

A tag `engine-v<version>` (matching `version` in `engine/pyproject.toml`) builds the wheel with the web app inside,
checks a clean install opens a project, and attaches it to a GitHub Release (`.github/workflows/engine-release.yml`).

## Use

```powershell
umbra-engine start C:\path\to\your\project # add + index + serve, browser on the Project
umbra-engine add C:\path\to\your\project   # register a Project (idempotent)
umbra-engine list                          # registered Projects
umbra-engine index C:\path\to\your\project # register if needed, then index
umbra-engine serve                         # local API and web app on http://127.0.0.1:7811
umbra-engine open [folder]                 # new browser login link for a running engine (on that folder's map)
umbra-engine mcp                           # MCP server for Claude Code (stdio): the `show` tool
umbra-engine token                         # local token for API clients
```

`serve` prints a one-time login link (`http://127.0.0.1:7811/#login=…`) and opens it. The code is
in the URL fragment, which browsers never send to the server; it works once, for 2 minutes, and opens
a browser session: a secret the page keeps in its own storage and sends in a header (no cookie, which
browsers would also send to other servers on 127.0.0.1). The API token itself never goes in a URL.
Restarting the engine signs every browser out: run `umbra-engine open`.

In the web app a project opens on its map (ADR-0007, `GET /v1/projects/<id>/system`), built from what the
files say without any LLM: who comes in (ENTRÉE), the parts that run left to right, the arrows between them
(each a verb), what leaves the project (◉ SORTIES), and the tools around (`+ N outils autour`). Hover any box,
arrow or output for its proof (file and lines); dashed means deduced, not read. Boxes keep their place across
reloads and re-indexing.

## Ask in Claude Code, see the answer on the map (`/umbra`)

The Claude Code plugin in `plugin/` registers the `umbra` MCP server (`umbra-engine mcp`, so `umbra-engine` must
be on `PATH`) and the `/umbra` skill. In a repo, type `/umbra`: Claude runs `umbra-engine open .` (or starts the
engine) and the map opens. Then ask a question about the repo, e.g. « où j'ajoute un champ prix à Item ? »: Claude
answers in at most 3 lines and calls `show({caption, path, parts})`. The open tab lights up to 6 numbered places
under their boxes, dims the rest, and shows one bar with « copier pour Claude » (the question and the files, ready
for an agent) and « effacer ». ← → move along the numbers. The engine runs no model for this: Claude Code is the
only one. A name that is not on the map is refused with the list of valid boxes, so Claude corrects itself.

Under the hood: `POST /v1/projects/<id>/show` checks the request against the map and the indexed files and pushes
it to the open tabs over `/events`; `GET` returns what is lit now; `DELETE` clears it.

Every `/v1/projects` endpoint needs the token, as `Authorization: Bearer <token>`. `POST /v1/projects` only accepts absolute paths.

```powershell
Invoke-RestMethod -Headers @{ Authorization = "Bearer $(umbra-engine token)" } http://127.0.0.1:7811/v1/projects
```

## What indexing gives you

`umbra-engine index <id|path>` passes every file through the Secret Guard, then through the Analyzers, and stores Claims:

| Relation | Status | Example |
|---|---|---|
| `defines` | Fact (Python, JS/TS, Go, Java, C#, Elixir), Hypothesis (other languages) | `app/api.py` defines `app/api.py::login` at lines 24-42 |
| `imports` | Fact | `web/auth.ts` imports `@tanstack/react-query` |
| `calls` | Hypothesis (names are matched, not resolved) | `app/api.py::login` calls `create_session` |

C, C++ and Kotlin definitions are not extracted yet (the parser gets them wrong); their imports are. Every Claim keeps its file, line range, producer and, when the working tree is clean, the git commit.

```powershell
umbra-engine verify-facts <id> --sample 30   # re-read the cited lines and check each Fact
Invoke-RestMethod -Headers @{ Authorization = "Bearer $(umbra-engine token)" } "http://127.0.0.1:7811/v1/projects/<id>/claims?relation=defines&status=fact"
```

**Network note:** the first time a language is indexed, tree-sitter-language-pack downloads that language's grammar (a compiled parser) into its cache. Only the grammar is fetched; no code, path or Claim leaves the machine.

## Where data lives

- `%USERPROFILE%\.umbra\registry.sqlite` — registered Projects.
- `%USERPROFILE%\.umbra\projects\<id>\store.sqlite` — one store per Project. Nothing is written inside your project folder.
- `%USERPROFILE%\.umbra\token` — local API token.

Set `UMBRA_HOME` to use another folder and `UMBRA_PORT` to change the port.

## Develop

```powershell
cd engine
python -m pytest
ruff check .
pyright src tests
```

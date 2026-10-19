# Umbra engine (System Explorer V1, in development)

Local daemon that registers Projects, keeps one isolated store per Project and exposes them through a local API. See `../SPEC.md` for the V1 scope.

## Install on Windows (from the repository)

Requirements: Python 3.11–3.13, Git and Node.js 20.19+ (for the web app), all on `PATH`.

```powershell
git clone https://github.com/rida12b/Umbra.git
cd Umbra
python -m pip install -e ".\engine[dev]"
cd ui; npm ci; npm run build; cd ..   # builds the web app into the engine package
umbra-engine --help
```

The command is `umbra-engine` while the v0.7 `umbra` command still exists; it becomes `umbra` when v0.7 is removed.

## Use

```powershell
umbra-engine add C:\path\to\your\project   # register a Project (idempotent)
umbra-engine list                          # registered Projects
umbra-engine index C:\path\to\your\project # register if needed, then index
umbra-engine serve                         # local API and web app on http://127.0.0.1:7811
umbra-engine open                          # new browser login link for a running engine
umbra-engine token                         # local token for API clients
```

`serve` prints a one-time login link (`http://127.0.0.1:7811/#login=…`) and opens it. The code is
in the URL fragment, which browsers never send to the server; it works once, for 2 minutes, and opens
a browser session: a secret the page keeps in its own storage and sends in a header (no cookie, which
browsers would also send to other servers on 127.0.0.1). The API token itself never goes in a URL.
Restarting the engine signs every browser out: run `umbra-engine open`.

In the web app: click an element for its details and Evidence (file, lines, version, guarded excerpt),
double-click (or **Open**) to go one level down, click a `+N more` group to show everything. Line
style tells the status: solid = Fact, dashed = Hypothesis, dotted = Declared (configuration, not proof
that anything runs). Below 720 px wide the graph becomes a list.

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

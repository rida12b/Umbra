# Umbra engine (System Explorer V1, in development)

Local daemon that registers Projects, keeps one isolated store per Project and exposes them through a local API. See `../SPEC.md` for the V1 scope.

## Install on Windows (from the repository)

Requirements: Python 3.11–3.13 and Git, both on `PATH`.

```powershell
git clone https://github.com/rida12b/Umbra.git
cd Umbra
python -m pip install -e ".\engine[dev]"
umbra-engine --help
```

The command is `umbra-engine` while the v0.7 `umbra` command still exists; it becomes `umbra` when v0.7 is removed.

## Use

```powershell
umbra-engine add C:\path\to\your\project   # register a Project (idempotent)
umbra-engine list                          # registered Projects
umbra-engine serve                         # local API on http://127.0.0.1:7811
umbra-engine token                         # local token for API clients
```

Every `/v1/projects` endpoint needs the token, as `Authorization: Bearer <token>`. `POST /v1/projects` only accepts absolute paths.

```powershell
Invoke-RestMethod -Headers @{ Authorization = "Bearer $(umbra-engine token)" } http://127.0.0.1:7811/v1/projects
```

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

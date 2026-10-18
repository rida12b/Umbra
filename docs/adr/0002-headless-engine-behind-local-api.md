# Headless engine behind a local API, one store per Project

Status: accepted (2026-10-18)

Umbra will later be embedded in a central dashboard that groups all of Rida's projects. So the engine runs as a single local daemon per machine and is reachable only through a versioned local API (REST `/v1` + SSE event stream, FastAPI). The Umbra UI, the MCP server used by Claude Code and the future dashboard are three clients of that same API; none reads the store directly. Each Project has its own SQLite store outside the repo (`~/.umbra/projects/<id>/`), listed in a registry, so Projects stay isolated. The API binds to 127.0.0.1 and requires a local token, because any web page in the browser can otherwise call localhost.

## Considered Options

- **One daemon per Project**: simpler, but the dashboard would have to discover N ports.
- **UI reading the store directly**: faster to build, but blocks any external client.
- **Store inside the repo (`.umbra/`)**: shareable through git, but pollutes repos and risks committing private data.
- **GraphQL / WebSocket**: more flexible or bidirectional, neither needed; REST + SSE is enough and works everywhere.

## Consequences

- The UI is a React component library plus a thin standalone app, so the dashboard can import components or use an iframe.
- Every feature must exist in the API first; the UI never gets private shortcuts.

# Claude Code studies a guarded copy of the Project in one session, then updates what changed

Status: accepted (2026-10-19). Amends ADR-0003 condition 7 ("`--tools ""`, empty working directory") for study sessions only.

Explaining a Project one element at a time (one `claude -p` call per card, shown only an excerpt) gave each answer a keyhole view: Claude could not follow a request from one file to the next, and a Project cost one call per element. An architect reads a project as a whole: map, entry points, whole journeys, then the parts.

So Umbra runs **one study session** per Project: Claude Code, with read-only tools, explores a copy of the Project and returns one model (architecture blocks and flows, components, end-to-end journeys with cited lines, one-sentence roles for modules, uncertainties). After a change, an **update session** gets the diff of the changed files and its previous model, reads what the change touches, and returns only the entries that changed.

## How the Secret Guard stays the only reader (ADR-0004)

- Claude never reads the Project folder. Umbra writes a fresh temporary copy holding only text released by the Secret Guard (secrets masked, excluded files absent), plus `UMBRA_INDEX.md`, Umbra's static map (files, definitions with lines, resolved imports, declared services, outside libraries).
- The session runs in that copy with `--tools Read,Grep,Glob` (no shell, no write, no web), `--permission-prompts none` (anything that would ask — a read outside the copy — is refused), `--safe-mode`, no saved session, API-key variables removed. The folder is passed by its long path: a Windows short name makes every read ask for permission.
- Proven on 2026-10-19: asked to read a file next to the copy (by absolute and relative path), the session answered that the read was blocked; the sentinel never appeared.

## Consequences

- A study takes minutes and many tool turns, but one session replaces hundreds of calls, and journeys can cross files.
- The model is an LLM's reading: shown as Hypothesis. Umbra checks every cited file and line range against the index and marks citations it cannot find.
- Per-element cards stay available on demand for a deeper look at one function or file.

## Considered options

- **One call per element, no tools** (ADR-0003 as written): safest, but keyhole understanding and one call per card.
- **Claude reads the real Project folder**: simplest, but secrets and excluded files would reach the model, breaking ADR-0004.

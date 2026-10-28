# The Explorer becomes one zoomable project map, and Claude Code draws its answers on it

Status: accepted (2026-10-27, decided by Rida: "oui c nickel ca"). Supersedes ADR-0006 (factory floor). Amended by ADR-0008 (names from rules, no Claude naming call). Need: `docs/need.md`.

## Context

Umbra's job, in the owner's words (`docs/need.md`): he lands on client repos he does not know, he will not read thousands of lines, and his only window is the Claude Code terminal, which "explains, but with no diagram". He wants to launch a tool and navigate the project: structure, components, entry, output, where it stands. It is not an audit.

Seven iterations missed this need between 2026-10-25 and 2026-10-27:
- the factory floor (ADR-0006): "pas intuitif du tout", invented words, the same fact shown 3 times, a map that did not fit;
- five "guided reading" mock-ups (v2–v6): long pages built from a hand-written study of one project, ending in an architect verdict the owner never asked for.

Root cause: each iteration answered the last remark instead of the need, and all of them were documents to read, not a place to move around in. A converge workflow (5 personas: newcomer, prior-art over 11 tools, information designer, AI orchestrator, inverter; a judge; 2 critiques) produced one concept, recorded in `docs/design/2026-10-27-project-map/concept.md`, with a clickable mock-up and a 4-panel storyboard in the same folder.

## Options

- **Wiki pages per project** (DeepWiki, Google Code Wiki): rich, but brings back the long-page problem, and reviews call their diagrams arbitrary.
- **File or call graph** (CodeSee, Understand Anything): exact, but becomes an unreadable hairball on a real repo.
- **Keep the factory floor and fix it**: keeps the engine work, but the metaphor is a vocabulary tax and the owner rejected it cold.
- **One project map in C4-style zoom levels, driven from the terminal**: box diagram that fits one screen, entry on the left, outputs on the right; click to zoom; a question asked in Claude Code lights up the answer on the same map. Proven patterns (Structurizr/CodeViz zoom, CodeSee tours, GitDiagram's check against the file tree). Risk: cutting any unknown repo into ≤ 5 boxes automatically.

## Decision

One project map, three zoom levels, Claude Code as the only chat. Rida, 2026-10-27.

- Level 0: one sentence, ≤ 5 boxes (hard max 7) left → right, ENTRÉE on the left edge, SORTIES as ◉ markers (response, stored row, outbound call) on the right; tooling folds into "+ N autour". Fits 1280 px with no scroll.
- Level 1: inside one box, ≤ 7 parts, neighbours as grey stubs. Level 2: a 4-line card (Reçoit / Renvoie / Appelé par / Appelle) plus function names; code opens in VS Code only. Nothing below.
- One highlight mechanism, two triggers: an action from "Ce qu'on peut faire", or a question in Claude Code answered in ≤ 3 lines plus an MCP call `umbra.show({parts, path, caption})`; ≤ 6 numbered parts light up, "copier pour Claude" copies the file list.
- Skeleton from hard signals without an LLM (deployable units → manifests → top folders; HTTP, DB, SMTP calls); Claude only names boxes and actions, drawn dashed "supposé".
- Words: repo names plus one plain French role word, no metaphor. Nothing judges: colour means selected, on this path, or changed.
- "Où on en est" = what is finished and what is not in the project (Rida's answer "b", 2026-10-27). Its screen is mocked and validated before it is built.

## Consequences

- Easier: the same map answers every question; no per-project study is needed to open a repo; the terminal stays the interface.
- Harder: the engine must find the entry, the outputs and the client → server link on any repo shape (today it finds compose services and "dépend de" links only, see `p-moteur.png`).
- Removed from scope: risks, debt, verdicts, hand-written journeys, reading pages, the factory floor vocabulary. The study-method fields added for ADR-0006 stay in the engine until the map replaces the floor, then dead code goes in the same PR.
- Watch: the cold test, at least one public repo that neither Rida nor Umbra has opened; Rida names entry, boxes and outputs in under 2 minutes from the map alone. A fail there reopens this ADR.

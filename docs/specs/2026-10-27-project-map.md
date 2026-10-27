# Project map driven from the terminal (ADR-0007)

## Need

`docs/need.md`. Done = on 3 repos, at least one public repo that neither Rida nor Umbra has ever opened, Rida opens Umbra cold and names the entry, the boxes and the outputs from the map alone in under 2 minutes, without reading code or text blocks.

## Visual contract

`docs/design/2026-10-27-project-map/` — `prototype.html` (clickable), `storyboard.html`, and the PNGs. Every UI PR puts a real screenshot beside the matching PNG (rule in `CLAUDE.md`).

## Decisions

- Level 0 (`p-carte.png`): sentence, ≤ 5 boxes left → right, ENTRÉE, ◉ SORTIES, "+ N autour", factual line (branch · last commit date), button "Ce qu'on peut faire (N)". Fits 1280×720.
- Level 1 (`p-serveur.png`, `p-web.png`): ≤ 7 parts, stubs to neighbours, Esc goes up, breadcrumb.
- Level 2 (`p-items.png`): 4-line card + function names with line numbers, "ouvrir le code" (vscode:// link).
- Lit path (`p-chemin.png`, `p-question.png`): same layout, rest dimmed, ≤ 6 numbered parts, one caption bar, ← →, "copier pour Claude", "effacer".
- Terminal bridge: MCP tool `umbra.show({parts, path, caption})` on the engine, pushed to the open tab over the existing SSE stream; the `/umbra` skill opens the map and makes Claude answer repo questions in ≤ 3 lines plus a `show` call.
- Skeleton without LLM from hard signals; Claude names boxes and actions once, drawn dashed "supposé" with the proof on hover.
- Layout computed once and stored; positions never move between levels or days.
- "Où on en est" = finished / not finished. Mocked first, validated by Rida, then built.

## Out of scope

Risks, debt, verdicts, scores; hand-written journeys and their failure cases; reading pages; a chat box or search bar in the UI; file-level or call graphs; deployment view; export.

## Done when

- Each slice has its screenshot beside the matching mock PNG, differences listed and fixed or OK'd.
- Level 0 reads as well on a repo without compose (sqlite-utils: `p-sqlite.png`) as on full-stack-fastapi-template.
- The cold test above passes, run by Rida.

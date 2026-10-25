# Factory-floor Explorer (ADR-0006)

## Need

A newcomer understands a project without reading code. Done = a human answers Q1–Q5 on Watchdog in 5 minutes:
Q1 what it does, for whom · Q2 where data comes in and ends up · Q3 the 3–7 main parts · Q4 one real action, part by part, in order · Q5 what to change where (part, file, setting).

## Decisions

- Base = factory floor (mockup `docs/design/2026-10-25-factory-floor/b-factory-floor.html`): rooms on one conveyor from ENTRÉE to SORTIE, ordered by the main journey; parts touched by no journey go to an "Autour du projet (ne tourne pas)" strip.
- "Entrer" opens the room in place on the same canvas: machines (components) left to right in the order the data visits them, neighbours as labelled doors, wiring (start-up assembly) as a grey band, refusals as red chutes. Room + doors fit the width left of the panel; anything out of view is signalled ("N hors champ →").
- The journey is played as numbered stations on the machines (from mockup `a-metro-line.html`): the highlight follows `etape.composant`, so every step moves.
- Bottom level = the machine plate, fixed slots: Fait / Reçoit / Rend / Réglages / Où / Vu dans. A slot the model does not fill says so ("pas encore dans le modèle"); the UI never invents it.
- Visual grammar from `blocs[].type`: person glyph, service with side stripe, storage cylinder, external dashed, docs/tools as grey tags; ▶ ENTRÉE and SORTIE ■ badges; thick = data, dashed = reply, thin grey = control, red = refusal; a key listing only kinds present. Dark theme default, AA contrast in light.
- Layout is Umbra's own code (no ELK) for the floor and rooms.
- Study method v1.7 adds: `composants[].entre/sort/reglages/termes`, project `donnee`, zone `atelier`, `flux.nature`, one `parcours.principal`, `phases` above 9 steps, `branches[].quand_simple/alors_simple`, `pour_changer`. `reglages[].verifie` is computed: citation in range and literal `code` found in the cited lines.
- Search indexes components, settings, plain/code terms and `pour_changer`.

## Out of scope

Claude cost plumbing, attribution, lifecycle, install (issues #52–#73 except #51, #59). Metro view with all journeys at once. Human Overrides (#19).

## Done when

1. Watchdog and JusticIA re-studied with v1.7 (two bounded sessions started by hand).
2. Screens checked at 1440 and 375, dark and light, every interaction exercised, e2e green, pyright + tsc clean.
3. A timed 5-minute Q1–Q5 test by Rida on Watchdog passes. An agent-judged test does not count.

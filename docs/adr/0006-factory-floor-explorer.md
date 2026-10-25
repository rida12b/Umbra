# The Explorer becomes a factory floor that opens rooms in place, with the journey played as a numbered line

Status: accepted (2026-10-25, decided by Rida: "je suis ta recommandation"). Supersedes the Explorer layout of #50 (zone rows, ELK import graph inside a part). Requires study method v1.7.

## Context

Umbra's job: a newcomer understands a project they did not write, without reading code. Measured as a 5-minute test: Q1 what it does and for whom, Q2 where data comes in and ends up, Q3 the 3–7 main parts, Q4 one real action part by part in order, Q5 what to change where (part, file, setting).

On 2026-10-25 the owner found the Explorer "unreadable, incomprehensible". An improvement arena (6 personas, judge, 3 mockups; record in `docs/design/2026-10-25-factory-floor/arena-verdict.md`) found five root causes, re-measured on the real Watchdog and JusticIA models:

1. Parts are placed by a type→zone table, not by the data: docs and lint tools sit between the entry and the store.
2. Journeys are written per component but played per part: 5 of 7 step changes on Watchdog (17 of 26 on JusticIA) leave the same box lit.
3. "Enter" shows a different picture (import graph, flipped direction, wiring as the hub), clipped under the side panel (`READABLE_ZOOM = 0.75`, right overflow not signalled).
4. Components carry 0 input, output or setting fields: Q5 has no answer on screen.
5. No visual grammar: identical cards, no key, no ENTRÉE/SORTIE.

## Options

- **A, metro line (journeys first)**: every journey is a coloured line ENTRÉE → SORTIE, parts are stations. Q4 at a glance; but long journeys (16 steps) need folding, and overlapping lines grow heavy on big projects.
- **B, factory floor (parts first, zoom in place)**: a few rooms on one conveyor from IN to OUT; "Enter" grows the room on the same canvas, machines in data order, neighbours as doors, a settings plate at the bottom. Matches the owner's ask (macro → drill-down → parameters) without losing place; the order of one action reads less directly than in A.
- **C, question sheet**: a page headed by Q1–Q5 with an outline and search. Simplest and safest, but read rather than seen, against the "visual" requirement.

## Decision

**B as the base, with A's numbered line played on the conveyor**: rooms open in place and the lit journey shows numbered stations on the machines it visits. Mockups: `docs/design/2026-10-25-factory-floor/b-factory-floor.html` (base) and `a-metro-line.html` (the line).

## Consequences

- The study model must start writing what the floor needs (method v1.7): per component `entre`, `sort`, `reglages` (literal code + file:lines, checked), `termes`; project `donnee`; zone `atelier`; `flux.nature`; one `principal` journey; `phases` above 9 steps; plain `branches`; `pour_changer`. Until a project is re-studied, the UI shows what it lacks instead of inventing it.
- The floor is laid out by Umbra's own code (conveyor order from the main journey), not by ELK: predictable for ≤12 parts per level.
- Search must index components and settings, or Q5 stays unreachable.
- Acceptance is a timed 5-minute Q1–Q5 test by a human on Watchdog. An agent-judged reader test no longer counts (the 2026-10-22 PASS was invalidated by real use).
- Revisit if the human test fails on Q4 (then A's line becomes primary) or on a large project the floor cannot hold.

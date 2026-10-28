# Names on the map come from rules read in the code; no Claude call names anything

Status: accepted (2026-10-28, decided by Rida: "b"). Amends ADR-0007 ("Claude only names boxes and actions, drawn dashed « supposé »"). Ticket: #108.

## Context

ADR-0007 planned one bounded Claude naming call per import (ADR-0003 conditions) to name boxes and actions in plain French. Since then:

- #114 removed the engine's Claude pipeline: the engine never runs `claude`.
- #103–#107 named everything from hard signals: box and part titles, role words per file of routes (« items », « comptes »), and every route of full-stack-fastapi-template (`projection/route_words.py`, 23 of 23).

Measured on 2026-10-28 on the two demo repos: the only unnamed things left were the 47 commands of sqlite-utils, shown as typed (`create-table`).

## Options

- **A — one Claude call per import names boxes and actions**: more natural words, but it costs the owner's subscription on each import, can invent a wrong name, adds a call that can fail, and brings `claude` back into the engine #114 just cleaned.
- **B — rules only**: a name is read in the code (address, decorator, command name) and translated by a fixed dictionary. Free, instant, the same each time, every word traceable to a line. Some names stay technical or unnamed.

## Decision

B. Rida, 2026-10-28 ("b"), on the lead's recommendation.

- Commands get their words from their name alone (`projection/command_words.py`): a verb then a thing (« create-table » → « Créer une table »), a thing alone is listed (« tables » → « Lister les tables »), a verb alone stays a verb (« vacuum » → « Compacter »). 45 of 47 sqlite-utils commands are named; `bulk` and `memory` stay as typed.
- A name no rule knows stays unnamed and the screen shows the code's own word (address or command). Nothing is guessed, so nothing is drawn dashed « supposé » for a name.
- The panel shows a command's French words with the command as typed beside it, always (it is what one types, and a phone has no hover).

## Consequences

- Easier: no model in the naming path; tests pin every name; a renamed box cannot move, since names never change between reads of the same code.
- Harder: each new repo shape may need dictionary words; English names the dictionary does not know show as typed.
- Watch: #111 cold test. If Rida, cold on an unknown repo, is slowed down by unnamed or technical names, reopen this ADR with option A, bounded as ADR-0003 requires.

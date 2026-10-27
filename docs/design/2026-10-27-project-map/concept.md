# Umbra — converged concept: "la carte du projet"

Judge: neutral. Inputs: BRIEF.md + 5 proposals (newcomer, prior-art, visual, orchestrator, inverter) + 2 critiques (critique-newcomer.md, critique-inverter.md). Revision 2 (2026-10-27): §3-§5 rewritten after the critiques, §9 "Agreement" added.
Example repo for every mock: `full-stack-fastapi-template` (facts checked in the repo on 2026-10-27). A second mock repo of a different shape is required (see §9).
UI text in mocks is French (Rida reads it). This document is English.

---

## 1. The need in 5 lines

1. Rida lands on client repos he does not know: "je peux pas ouvrir chaque page du repo, comprendre chaque fichier, chaque fonction".
2. He orchestrates AI and decides architecture; he will not read "des milliers de lignes".
3. His only window today is the Claude Code terminal, and it explains badly: "visuellement, c'est dur à comprendre… j'aurai pas de schéma".
4. He wants a tool: "j'arrive sur un projet, je lance mon outil, je peux naviguer dans le projet" — structure, components, "quelle est l'entrée, quelle est la sortie", "où on en est".
5. It is NOT an audit: "un outil d'analyse qui va donner les points faibles… c'est pas ça que je te demande".

Test of success: on 3 repos, **at least 1 public repo that neither Rida nor Umbra has ever opened**, Rida drives cold and names the entry, the boxes and the outputs from the map alone in under 2 minutes, without reading code or text blocks.

---

## 2. Scoring of the 5 proposals

Scale 1-5. Weighted total = fit x3 + clarity x2 + any repo + buildable + simplicity (max 40).

| Proposal | Fit to need (x3) | First-glance clarity (x2) | Works on any repo | Buildable on engine + React UI | Simplicity | Total |
|---|---|---|---|---|---|---|
| **inverter** — one map, 3 zoom levels, Claude draws on it | 4 (12) | 5 (10) | 5 | 5 | 5 | **37** |
| **newcomer** — one map, every question = a highlight | 5 (15) | 4 (8) | 3 | 4 | 4 | **34** |
| **orchestrator** — "the terminal draws" (MCP `show`) | 5 (15) | 4 (8) | 4 | 3 | 3 | **33** |
| **prior-art** — C4 zoom + tours + search, grounded in 9 tools | 4 (12) | 4 (8) | 4 | 4 | 4 | **32** |
| **visual** — strict diagram grammar, stable layout | 4 (12) | 5 (10) | 3 | 4 | 3 | **32** |

Verdict: **inverter is the skeleton**; orchestrator gives the terminal bridge (now the core, see §9); visual gives the drawing rules; newcomer gives the change-impact view and the output markers; prior-art gives the acceptance test and the "validate against real files" rule.

---

## 3. The converged experience (5 steps)

1. **Lancer.** In the client repo, in Claude Code, Rida types `/umbra`. The engine indexes locally (no LLM for the skeleton), Claude names the boxes once (names drawn dashed = "supposé"), a browser tab opens beside the terminal on `127.0.0.1`.
2. **Voir (10 s).** Screen 1 — La carte: one sentence, ≤ 5 boxes left → right, ENTRÉE on the left edge, output markers where things leave or are stored. One factual line: branch · last commit date. Fits 1280 px with no scroll.
3. **Zoomer.** Double-click a box → Screen 2 (its inside, ≤ 7 parts, neighbours as grey stubs). Click a part → Screen 3 (4-line card). That is the floor; code opens in VS Code only.
4. **Allumer un chemin.** Two triggers, one mechanism (Screen 4): (a) Rida picks an action in "Ce qu'on peut faire", or (b) Rida asks Claude Code a question; Claude answers in ≤ 3 lines and calls `umbra.show(...)`. The same map dims, ≤ 6 parts light up, numbered, one verb + one file per arrow. "Why" text exists only when Claude writes it in the terminal for that question.
5. **Préparer la tâche.** On a lit path, "copier pour Claude" copies the list of files → Rida hands it to an agent.

Rules for every screen:
- One map, one layout, computed once; positions never move between screens or between days.
- Default ≤ 5 boxes at Level 0, hard max 7 per level; more → group, never shrink. Everything around (tests, CI, Adminer, optional services, prestart) folds into one "+ N autour" item, unfolded on hover.
- Flow left → right. Arrow = a verb. Box = something that runs or stores.
- **ENTRÉE = where something comes in. SORTIE = where something leaves or is stored**, drawn as end markers ◉ with one word, detected from hard signals: response to the client, DB writes, outbound calls (SMTP, HTTP, queues, files). Same rule on every repo.
- The word "entrée" is used only on the map edge. The list of routes/commands/jobs is called "Ce qu'on peut faire".
- Words = repo names + one plain French role word. No metaphor.
- Max 1 sentence per box, 4 lines per card, 1 caption bar. Proof (file:lines) on hover or click only.
- Nothing judges: no colour means "bad", no adjective about activity. Colour = selected / on this path / changed.
- Anything inferred (names, groupings, French labels of actions) is drawn dashed, "supposé" on hover.
- **Mocks show only what the engine can produce.** Screens 1-2 are filled from a real engine run on the repo; if the engine cannot do it yet, the mock shows the rough version and says so.

---

## 4. The screens to mock

### Screen 1 — La carte (Level 0)
**Question it answers:** what is this project, what goes in, what comes out?

```
+------------------------------------------------------------------------------------------+
| full-stack-fastapi-template                   branche master · dernier commit 16/04/2026 |
| Une appli web avec comptes : on se connecte, on gère ses « items ».                      |
+------------------------------------------------------------------------------------------+
| ENTRÉE                                                                                   |
|                                                                                          |
|  +-------------+ remplit +-----------------+ appelle +-------------+ écrit +----------+   |
|  | Utilisateur |-------->| Application web |-------->| Serveur     |------>| Base     |   |
|  | navigateur  |<--------| React           |<--------| FastAPI     |       | Postgres |   |
|  +-------------+ affiche +-----------------+ répond  +------+------+       +----------+   |
|   ◉ écran mis à jour                                        | envoie        ◉ ligne      |
|                                                             v                 enregistrée|
|                                                      +-------------+                     |
|                                                      | Courriel    |  ◉ courriel envoyé  |
|                                                      | SMTP        |                     |
|                                                      +-------------+                     |
|                                                                          + 7 autour      |
+------------------------------------------------------------------------------------------+
| [ Ce qu'on peut faire (23) ]                                                             |
+------------------------------------------------------------------------------------------+
```

Visible at first open: 1 sentence, 5 boxes, 3 output markers, 1 button, "+ 7 autour". Acceptance: a cold reader names the boxes in 10 s.
- "+ 7 autour" (hover): Suivi des erreurs (Sentry, optional) · Préparation au démarrage (prestart) · Tests · CI GitHub · Adminer · Copier · Docs.
- "Ce qu'on peut faire (23)": the 23 `@router` routes, grouped by box/file, each with a French label named by Claude (dashed) and the route on hover (`POST /api/v1/items/` → "Créer un item").
Interactions: hover box → role + folders; double-click → Screen 2; click arrow → protocol + route + "voir le code".

### Screen 2 — Dans une boîte (Level 1): "Serveur"
**Question it answers:** how is this box cut, where does a request enter it, where does it leave?

Layout: breadcrumb `Système > Serveur (backend/app)` + Esc; grey stub "depuis Application web" on the left edge, "vers Base" and "vers Courriel" on the right; ≤ 7 parts left → right: Porte d'entrée (`main.py`) → Routes (`api/routes/`: login · users · items · utils · private) → Modèles (`models.py`) → stub Base; below: Contrôle d'accès (`deps.py`, `core/security.py`), Réglages (`core/config.py`), Accès aux données (`crud.py`), Migrations (`alembic/`, 5).
Interactions: click a part → Screen 3; click a stub → back to that neighbour on Screen 1.

### Screen 3 — Une pièce (Level 2): `items.py`
**Question it answers:** what does this piece do, who uses it, what does it use?

Layout: breadcrumb + "ouvrir le code"; one 4-line card: Reçoit `GET · POST · PUT · DELETE /api/v1/items/ + jeton` / Renvoie `un item ou une erreur` / Appelé par `Application web (frontend/src/client/sdk.gen.ts)` / Appelle `deps.py · models.Item · Base`; then the 5 function names (`read_items` l.14, `read_item` l.49, `create_item` l.62, `update_item` l.76, `delete_item` l.100), each opens VS Code at the line; then "Ce qu'on peut faire ici" → Screen 4. Nothing below this level.

### Screen 4 — Un chemin allumé (one mechanism, two triggers)
**Question it answers:** "when someone does X" or "Claude, where is / where would I change X?" — answered as a lit path on the same map, not a text wall.

Layout: the current map (Screen 1 or 2 layout), rest dimmed to 30 %; ≤ 6 lit parts numbered; each arrow = verb + file; one caption bar on top = the action or the question, with "copier pour Claude" and "effacer"; ← → moves the focus along the path.

Mock A — triggered by clicking "Créer un item" (generated from the static call chain, label "généré, pas étudié"):
`1 POST /api/v1/items/` (Application web, `sdk.gen.ts`) → `2 create_item` (`routes/items.py`) → `3 vérifie le jeton` (`deps.py: get_current_user`) → `4 valide` (`models.py: Item`) → `5 écrit` (`session.commit`) → ◉ `ligne enregistrée` (table `item`). Note: this route does not go through `crud.py`; the mock must follow the real chain, not the guessed one.

Mock B — triggered from the terminal (split screen, this is the pitch image):
```
 TERMINAL (Claude Code)                        |  NAVIGATEUR (Umbra)
 > où j'ajoute un champ prix à Item ?          |  Question : « où j'ajoute un champ prix à Item ? »
 Claude : 5 endroits, du modèle à l'écran.     |  [App web]  1 Items (form, tableau)  2 client (régénérer)
   Modèle, migration, route, client, page.     |  [Serveur]  3 models.py  4 alembic/ (nouvelle migration)
   → montré sur la carte                       |             5 routes/items.py
                                               |  reste grisé      [ copier pour Claude ] [ effacer ]
```
Files: `backend/app/models.py` · `backend/app/alembic/versions/` · `backend/app/api/routes/items.py` · `frontend/src/client/` · `frontend/src/components/Items/`. Hover a lit part → one line "pourquoi ici" written by Claude for this question.

### Screen 5 — Où on en est: NOT mocked yet (open, see §9)
Only the header line exists now (branch · last commit date, no adjective). Before any mock, Rida answers one question.

---

## 5. Storyboard (4 panels, 1 sentence each — this is what Rida sees)

1. **La carte.** Lundi, nouveau client : `/umbra` → 5 boîtes, l'entrée à gauche, les sorties à droite. *« En 10 secondes, tu sais ce que fait le projet. »*
2. **Dans une boîte.** Double-clic sur Serveur → ses 7 parties, puis une carte de 4 lignes. *« Tu ne lis pas de code, tu zoomes. »*
3. **La question dessinée.** Split screen : il demande « où j'ajoute un champ prix ? », Claude répond en 3 lignes, 5 parties s'allument sur la carte. *« Le terminal parle, la carte montre. »*
4. **La tâche pour l'agent.** Il clique « copier pour Claude » et lance l'agent sur ces 5 fichiers. *« Tu décides l'architecture, l'agent code. »*

How the bridge works (build plan only, not shown to Rida): Umbra engine exposes one MCP tool `umbra.show({parts, path, caption})` next to its REST + SSE API; the browser tab already listens to SSE, so a `show` call redraws the highlight. The `/umbra` skill tells Claude Code to answer in ≤ 3 lines and to call `show` by default for any "où / comment / quoi" question about the repo. Umbra never runs its own chat.

---

## 6. What is cut, and why

| Cut | Why |
|---|---|
| Risks, debt, weak points, "verdict d'architecte", scores, judgement words ("calme") | Owner: "c'est pas ça que je te demande". Orientation, not audit. |
| Reading pages, chapters, tabs of prose, folds with counters (v2-v6) | He navigates; he does not read. |
| Visible file:line proofs everywhere | Proof = hover / "voir le code". |
| Hand-written journeys (10-step trajet, "why" and failure cases per step) | Cannot exist on an unknown repo on day 1. Paths come from the static call chain; "why" only from Claude, on a question. |
| Two highlight mechanisms (journey screen + answer screen) | One lit-path mechanism, two triggers. |
| Factory floor / metro metaphors | Invented words = a tax. |
| Same fact on map + side panel + list | One map, one caption bar. |
| Separate chat box in the UI | Claude Code is the chat. |
| Search bar in the UI | The terminal question is the search. |
| Status strip with adjective, commit list on Screen 1 | Only branch + date until "où on en est" is answered. |
| Sentry, prestart, tooling as boxes at Level 0 | Folded into "+ 7 autour". |
| Export HTML, pinned-question sidebar, deployment view | Later, if asked. |
| File-level / function-level graph | Hairball. Floor = 4-line card + function names. |

---

## 7. Ideas grafted from each runner-up

- **newcomer** → lit path for "where do I change X?"; output markers ◉; "Ce qu'on peut faire" naming; "copier pour Claude".
- **orchestrator** → the terminal drives the map through MCP `show` (now build slice 1).
- **prior-art** → C4 zoom levels; ≤ 7 boxes; validate every box/arrow against the real file tree; the cold acceptance test.
- **visual** → left → right, stable layout, grey stubs, "+ N autour", one caption bar, arrow keys.
- **inverter** → 3 levels and a hard floor; Level 0 from hard signals; no precomputed journeys; fewer things on screen.

---

## 8. Open risk to settle before build

The Level 0 cut on a repo with no compose file (monolith, monorepo, library, notebooks). Decision: hard signals first (deployable units → manifests → top folders), inferred items dashed "supposé", Rida can drag a box into another to regroup (stored, never re-shuffled). Proven only when the second mock repo (different shape) reads as well as the template.

---

## 9. Agreement

### Accepted objections (all proven against BRIEF.md)
| # | Objection | Source | Brief evidence | Change made |
|---|---|---|---|---|
| A1 | Screen 1 too full | newcomer 1, inverter 2 | miss 2: "trop d'infos d'un coup", map did not fit | ≤ 5 boxes, "+ 7 autour", no strip adjective, no search, real HTML at 1280 px with screenshot |
| A2 | "Entrée" means two things | newcomer 1 | "quelle est l'entrée" must be unambiguous | Button renamed "Ce qu'on peut faire (23)" |
| A3 | SORTIE is a label, not an answer | newcomer 2 | "quelle est l'entrée, quelle est la sortie" | ◉ output markers from hard signals, one rule for every repo |
| A4 | Screen 4 brings back the study | newcomer 3, inverter 1 | "works on ANY unknown repo"; misses 4-7 = study pages | Screens 4+5 merged into one lit-path mechanism, ≤ 6 parts, from the static call chain, labelled "généré" |
| A5 | Terminal bridge is the core | newcomer 4 | "ma seule fenêtre… c'est mon terminal… j'aurai pas de schéma" | Build slice 1 = Screen 1 + `umbra.show` end to end; skill makes `show` the default |
| A6 | "Où on en est" guessed; "calme" judges | newcomer 5, inverter 3 | 10 misses from guessing; "pas un outil d'analyse" | Screen 6 removed from mocks and from first build; one question to Rida |
| A7 | Mocks fed by a curated study | inverter 4 | miss 3: "dans la data y'a rien" after a pretty mock | Screens 1-2 filled from a real engine run; rough if needed |
| A8 | Single-repo proof, known repos | newcomer 5, inverter 5 | "on ANY unknown repo" | Second mock repo of a different shape; cold test on ≥ 1 never-opened public repo |
| A9 | Presentation too big | inverter 5 | "Rida reads one screen at most" | Show Rida 3 images + 1 split-screen, 1 sentence each (§5) |

### Rejected (one line each)
- Newcomer: status line on hover only → rejected: "où on en est" is in the brief; one factual line (branch · date) costs nothing and judges nothing.
- Newcomer: Claude writes a caption every time a path is opened → rejected: an LLM call per click slides back toward a study; captions come only when Rida asks in the terminal.
- Newcomer: Screen 4 chain "deps → crud → model" → corrected: `create_item` does not call `crud.py` (checked in `backend/app/api/routes/items.py:61-72`); the mock follows the real chain.

### What all agreed
- One map, one fixed layout, 3 zoom levels, hard floor at the 4-line card, code only in VS Code.
- Left → right, ≤ 7 boxes per level (≤ 5 by default at Level 0), repo names + one French role word, no metaphor.
- No audit: colour = selected / on path / changed only.
- Proof behind hover/click; inferred = dashed "supposé"; Level 0 from hard signals, LLM only names.
- Claude Code is the chat; Umbra only draws; one MCP tool `show` first.
- Mocks = only what the engine can produce, rendered as real HTML.
- Build order: Screen 1 + `umbra.show` (slice 1) → Screen 2 → Screen 3 → Screen 4 (both triggers) → cold test on an unknown repo → "où on en est" once answered.

### What stays open
1. **The one question for Rida** (asked with the images in front of him): « "Où on en est", c'est l'activité récente (ce qui a bougé, les branches et PR en cours), ou ce qui est fini / pas fini dans le projet ? »
2. Which second mock repo (different shape: no compose, CLI or library) and which never-opened public repo for the cold test.
3. Whether the current engine produces Screen 1-2 well enough on both repos; if not, the rough version is shown and the gap becomes the first build task.
4. The Level 0 cut without compose (§8), proven or not by item 2.

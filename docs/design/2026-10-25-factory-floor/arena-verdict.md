# Verdict — Umbra improvement arena (round 1)

Judge: neutral judge + red team. Date: 2026-10-25.
I did not start the Umbra engine and did not call `claude -p`. I only wrote this file.

## 1. What I checked myself (fresh, not from the proposals)

Everything below was re-measured or re-read by me. Proposal claims that I could not check are marked.

**Screenshots (read as images)**
- 01: the row "Ce qui traite" holds only the group "Autres traitements — Outils de contrôle du code, Documents de vision". Its arrow "vérifie" points up into "Porte d'entrée du service". The real data arrow "range l'événement dans" goes round it in a right-hand lane. All 5 cards look the same. The kind of part is a small grey word at the bottom left. The orange "Entrer dedans" is the loudest thing on screen.
- 02: at step 1 of 5, only "Assistant d'IA surveillé" and "Porte d'entrée du service" are lit. The side panel shows the branch text as raw developer text: `401 {"detail": "Missing X-Tenant-ID header"}`. The player bar does not show file:line. The player bar covers "Mémoire temporaire".
- 03: inside the part, the hub is "Assemblage de l'application", with arrows labelled "utilise". "Contrôle du nom" and "Réception des co…" are cut at x≈1040 by the panel. "Forme attendue d'un compte rendu" is not on screen. "Assistant d'IA surveillé" is missing. About 60% of the canvas is empty.

**Models (Python script over both JSON files)**
- Watchdog has 6 blocs and 5 components (api 4, memoire 1). JusticIA has 15 blocs and 12 components.
- Component keys in both models: bloc, en_bref, expose, fichiers, id, nom, responsabilites, role, utilise. There are 0 input, output or parameter fields.
- The blocs touched by no journey are `docs` and `outillage`, in both models.
- Journey steps mapped to blocs (component → bloc):
  - Watchdog: 5 of 7 step-to-step transitions do not move. At component level, 2 of 7 do not move.
  - JusticIA: 17 of 26 do not move. At component level, 11 of 26 do not move.
  - JusticIA `courrier-pdf`: `touche` is `[]` on 4 of 4 steps. Its declencheur says "le site actuel ne l'appelle plus".
- `X-Tenant-ID` appears 13 times in watchdog-model.json, always inside prose.
- In Watchdog, no string contains both "nom du client" and "tenant". The data object is named "compte(s) rendu(s)" 20 times and "événement(s)" 26 times.
- **Red-team catch:** two Watchdog journeys tie on distinct blocs. `envoi-evenement` touches {agent-surveille, api, memoire} and `demarrage` touches {operateur, api, memoire}. So NouveauVenu's rule "main line = the journey with the most distinct blocs" is ambiguous, and could pick "Installer et démarrer" as the main line. Counting distinct components breaks the tie (envoi 4 vs demarrage 1), but the method should simply declare the main journey.

**Umbra code (read only)**

| Proposal claim | Where I checked it | Verdict |
|---|---|---|
| Wrapping at 3 boxes per row | `rowLayout.ts:33` `PER_ROW = 3` | true |
| Zoom never goes below a readable size; overflow is flagged at the bottom only | `ExplorerCanvas.tsx:24` `READABLE_ZOOM = 0.75`; `frame()` l.51-62 clamps the zoom, sets `x = MARGIN` and returns only the bottom overflow | true: right overflow is silently clipped |
| The inner level is drawn from the import graph | `levels.ts:271` builds edges from `c.utilise` | true |
| A cross-part arrow is lost | `neighbour()` l.255-262 looks ids up in `model.blocs` only, so route-events → stockage-events draws nothing | true |
| The zone enum has no value for off-path things | `method.py` SCHEMA l.68-70: zone = utilise / recoit / traite / range / exterieur | true |
| The kind label is faint | `mapParts.tsx` ~l.51 `text-[13px] text-faint` | true |
| Search ignores components | `CommandPalette.tsx` ~l.56-65 searches journeys and blocs only | true |
| Developer details are collapsed; file paths are plain text | `InfoPanel.tsx` l.127-141 (collapsed `<details>`) and l.160-171 (`Files` = plain `<li>`) | true |

**Watchdog source (read only).** Every value the proposals quote is real:

| Value | Where |
|---|---|
| Header name `X-Tenant-ID` | `tenant_auth.py:33` |
| Refusal code `401` | `tenant_auth.py:36` |
| Refusal message | `tenant_auth.py:37` |
| Output `request.state.tenant_id` | `tenant_auth.py:39` |
| Global middleware | `main.py:20` |
| `schema_version "1.0"` | `schemas.py:16` |
| `status` Literal of 5 values | `schemas.py:35` |
| Route returns 201 | `events.py:19` |
| In-memory list `_events` | `storage/events.py:9` |

`grep environ|getenv|BaseSettings` over the Python code returns 0 hits. So the `.env.example` variables are not read, as the model says.

**Not verified by me (web):** Roberts et al. "up to 50% faster", Kedro-Viz expand-in-place, and the n8n node view. They are cited as supporting basis only. No verdict rests on them alone: each retained proposal also has a measurement on the real data.

**Sketches.** I opened all 18 sketches.
- I checked that the 9 HTML sketches use the model's own names (grep for the component names, X-Tenant-ID and tenant_auth.py).
- I looked at the Chercheur p1/p2/p3, Designer and Inverseur screenshots.
- The Inverseur fiche is rendered in a **white theme**, which the owner already called unreadable. Its "Q3" section lists 5 components, not the 3–7 main parts. Both are fixable, but they are noted.
- The Chercheur JusticIA metro labels "Un programme" and "PDF prêt à envoyer" are shortened from the courrier-pdf `depart`/`fin` texts. They are not bloc names, which is acceptable.

## 2. Ranking (merged)

The 18 proposals collapse into 6 retained ideas, called **M1** to **M6** in the table.

| # | Owner | Title (short) | Verdict | Merged into | Why |
|---|---|---|---|---|---|
| 1 | Chercheur | Journey as one numbered line that opens the parts it crosses | RETENU | M2 drill/journey across levels | 5/7 and 17/26 no-move transitions verified. Component-level stations do move. No method change needed. |
| 2 | Chercheur | Macro transit diagram IN→OUT, one line per journey, Atelier shelf | RETENU | M1 data spine + shelf | Docs/tools in "traite" verified on screenshot 01 and in both models. JusticIA interchanges verified (3 of 4 journeys). |
| 3 | Chercheur | Leaf inspector Entre / Réglages / Sort + "Je veux changer…" | RETENU | M3 spec plate | 0 parameter fields verified. Every value verified in the source. |
| 4 | NouveauVenu | Data line + "Autour du projet" rail | RETENU (rule amended) | M1 | Evidence holds. The "most distinct blocs" rule ties on Watchdog: replace it with `parcours.principal` in the method, or count distinct components. |
| 5 | NouveauVenu | "Entrer dedans" opens the box in place, ordered by data path | RETENU | M2 | Screenshot 03 clipping verified, and the cause is verified in `frame()`. |
| 6 | NouveauVenu | Plain word ↔ code word chips + knobs table | RETENU | M3 (+ `termes`) | "nom du client" and "tenant" never appear in the same string: verified. |
| 7 | Pedagogue | Path opens the part on the same map; steps grouped by part | RETENU | M2 | Duplicate of #1 and #5. Chapter grouping kept, as the answer to JusticIA's 16 steps. |
| 8 | Pedagogue | Data spine, tooling off path, one name for the data | RETENU | M1 (+ `donnee`) | The 20/26 name split is verified and visible on screen ("comptes rendus" vs "événements"). |
| 9 | Pedagogue | Six fixed slots on every component card | RETENU | M3 | The fixed order (Fait / Reçoit / Rend / Réglages / Où / Vu dans) becomes the plate layout. |
| 10 | Designer | Visual grammar: shape and colour per kind, key, ENTRÉE/SORTIE | RETENU | M4 grammar | Identical cards and the faint kind label verified. `blocs[].type` exists, so this is cost S. Best value per effort. |
| 11 | Designer | Metro macro, journey as a glowing line, Atelier shelf | RETENU | M1 + M2 | Duplicate. Its finding that courrier-pdf has no entry bloc is verified and goes into the method changes. |
| 12 | Designer | Drill-down keeps the line, ghost IN/OUT neighbours, wiring band, parameter card | RETENU | M2 + M3 | Direction flip, Assemblage hub and empty canvas verified on screenshot 03. |
| 13 | Navigation | The part as a "room" that fits the screen, neighbour "doors" | RETENU | M2 | Root cause verified in code (zoom clamp; overflow reported at the bottom only; `neighbour()` resolves blocs only). Its fit claim was computed, not seen. |
| 14 | Navigation | Spec plate + structured `reglages` with a literal check | RETENU | M3 (schema base) | Best schema of the lot. "verifie = literal name found in the cited lines" keeps the Fact/Hypothesis model honest. |
| 15 | Navigation | Synced outline + one search over every level | RETENU | M5 | The palette ignoring components is verified. Without this, "nom du client" never reaches the component (Q5). |
| 16 | Inverseur | Macro = data line of parts, docs off the map | RETENU (method part rejected) | M1 | Evidence holds. The new `ligne` field is not needed: stations can be derived from `etapes.composant`. A field that copies a derivable fact is drift risk. |
| 17 | Inverseur | Parameters and the flowing data as first-class model fields | RETENU | M3 + `donnee` | Duplicate of #14 and #8. The `pour_changer` index is kept. |
| 18 | Inverseur | Landing = one static sheet that answers Q1–Q5 in order | RETENU (as an alternative to test) | M6 | Works today, cost S, and is shown rendered. But it is white-themed and lists components as "Q3", against the owner's "visual" wish. So it is kept as a competing direction, not as the default. |

There are no outright rejections: every proposal met the evidence standard on data I could re-check. The red-team corrections are amendments: #4 (ambiguous main-line rule), #16 (redundant `ligne` field) and #18 (theme and Q3 granularity).

## 3. Foundation diagnosis (why Q1–Q5 fail today)

1. **The map follows a type→zone table, not the data.** docs and outillage sit in "Ce qui traite" (method zone enum, method.py l.68-70), between the entry and the store. Q2 and Q3 are answered wrong.
2. **Two granularities do not match.** Journeys are written per component, but they are played per bloc. In Watchdog, 5 of 7 transitions do not move; in JusticIA, 17 of 26. courrier-pdf lights nothing. Q4 can only be read in a text list.
3. **Drill-down is a different picture.** It is an ELK import graph ("utilise"), the direction flips, wiring ("Assemblage") is the hub, the map is clipped under the panel (zoom clamped at 0.75, with no right-edge signal), and the cross-part arrow is dropped. Q4 and Q5 break one level down.
4. **The bottom level has no data.** The 17 components have 0 entre, sort or réglages fields. X-Tenant-ID exists only in prose, and search skips components. Q5 has no on-screen answer.
5. **There is no visual grammar.** The cards look identical, there is no key and no ENTRÉE/SORTIE, the navigation link is the loudest element, and the flowing data has 2 names. Only Q1 (the pitch) passes.

## 4. Study-method changes (what the model must start writing)

1. `composants[].entre` and `composants[].sort`: 1–3 plain items each, refusals included (e.g. "ou un refus 401").
2. `composants[].reglages = [{nom (plain), code (literal), sorte: env|entete|constante|champ|limite|branchement, valeur, effet (≤90 chars), fichier, lignes}]`, with 0–6 rows. `verifie` is computed by model.py: the citation must be in range AND `code` must be found literally in those lines. There is also one project-level list built from .env/config files, with a column "lu par le code: oui/non".
3. `composants[].termes = [{simple, code}]`: the bridge between plain words and code words ("nom du client" = tenant / X-Tenant-ID). Reader check: each plain term must be findable by search together with its file.
4. A top-level `donnee = [{nom, dans_le_code, entre_par, finit_dans}]`, plus a rule: use only that name in en_bref, simple and verbe.
5. A new zone value `atelier` (docs, tests, tooling, build). A bloc touched by no journey may not take a data zone. Each flux gets `nature: donnee|controle`, so "démarre" and "vérifie" are not drawn as data.
6. On parcours: exactly one `principal: true`, an explicit `entree` bloc and `sortie` blocs, and every journey must start at a bloc (this closes the courrier-pdf gap). A step with `manuel: true` may have `composant: null`. The UI highlight comes from `composant`, not from `touche`.
7. `branches[].quand_simple` and `alors_simple`, so a non-developer never sees raw `401 {"detail": …}`.
8. A journey with more than 9 steps writes `phases = [{nom, de, a}]`, 3–5 phases (JusticIA poser-question has 16 steps).
9. Optional: `pour_changer = [{intention, composant, reglage, fichier, lignes}]`, 2–3 per core component. The search indexes it.
10. A bloc with no component declares `interieur: externe|fichiers`, so "Entrer" never lands on an empty level by accident.
11. Acceptance gate: a timed human 5-minute Q1–Q5 test on the same Watchdog data. An agent-judged reader test is not accepted.

## 5. Mockup directions (2–3 distinct ones; each is ONE self-contained HTML file on the real Watchdog texts)

The three directions differ in what is primary on screen:
- **A, journeys:** the lines come first; the parts are stations on them.
- **B, places:** the parts come first, as rooms; a journey is a conveyor through rooms that open in place.
- **C, questions:** the five questions come first; the maps are small figures and the outline is the index.

### Shared building blocks (used by all three)

**Spec plate (M3).** For a component, in this order:

| Slot | Content |
|---|---|
| Fait | en_bref |
| Reçoit | entre |
| Rend | sort |
| Réglages | the reglages table |
| Où | expose.quoi + fichier:lignes + "vérifié" |
| Vu dans | computed from parcours, each entry clickable to play from that step |

Values that the model does not hold yet are shown under a badge **"pas encore dans le modèle — lu dans le code"**, with file:line.

**"Pas encore dans le modèle" facts for Watchdog** (all verified in `the Watchdog repository`):
- **Contrôle du nom du client**
  - Reçoit: header `X-Tenant-ID`, `watchdog_ai/api/middleware/tenant_auth.py:33`
  - Rend: `request.state.tenant_id` (tenant_auth.py:39), or refus `401` (:36) `{"detail": "Missing X-Tenant-ID header"}` (:37)
  - Portée: global, `app.add_middleware`, `watchdog_ai/main.py:20` (includes /docs)
- **Forme attendue d'un compte rendu** (`watchdog_ai/ingestion/schemas.py`)
  - `agent_id` 1–128 chars (:15); `schema_version="1.0"` (:16); `latency_ms ≥ 0` (:20)
  - `provider` 1–64 chars (:23); `model` 1–128 chars (:24); token counts ≥ 0 (:29-31); `cost_usd ≥ 0` (:32)
  - `status` ∈ success / error / timeout / content_filter / rate_limit (:35); `metadata` default `{}` (:36)
- **Réception des comptes rendus** (`watchdog_ai/api/routes/events.py`)
  - prefix `/api/v1` (:13); path `/events` (:17); response EventOut (:18); code `201` (:19)
- **Rangement des événements** (`watchdog_ai/storage/events.py`)
  - list `_events` in memory (:9); `received_at = datetime.now(UTC)` (:17); no duplicate check, plain append (:19)
- **Assemblage de l'application** (`watchdog_ai/main.py`)
  - title `"Watchdog"` (:15); version `"0.1.0"` (:17)
- **Project settings**
  - `.env.example:2-4`: `APP_ENV=development`, `APP_PORT=8000`, `LOG_LEVEL=INFO`, marked **"non lu par le code"** (0 hits for environ / getenv / BaseSettings)
  - The real port comes from `README.md:38` (`--port 8000`).

**Visual grammar (M4)**, built from `blocs[].type`:

| Kind | Shape |
|---|---|
| person | person glyph, green |
| service | rounded rectangle with a blue side stripe |
| database / storage | amber cylinder |
| external | dashed outline |
| docs / tools | small grey tags on the Atelier shelf |

Other marks:
- Green **▶ ENTRÉE** badge on the `entree` bloc of the main journey (derived from step 1 for now).
- Amber **SORTIE ■** badge on the bloc that keeps the data (memoire), with « Tout est perdu au redémarrage. » taken from the bloc role.
- Line styles: thick = data, dashed = reply, grey thin = control ("démarre"), red square = refusal.
- A permanent key lists only the kinds present.
- "Entrer" becomes a quiet "4 étapes ici · Entrer ›".
- Dark theme by default.

### Direction A — "Ligne de métro" (journey-first transit map)

*One line:* the project drawn as a metro plan: each data journey is a coloured line running left (ENTRÉE) to right (SORTIE). Parts are stations, interchanges are the parts to learn first, and clicking a station opens its spec plate.

**Screen 1, Plan** (1440×900; canvas 1040, panel 400):
- **Top band:** the pitch (Q1), then one chip per journey, as a legend: "Recevoir et garder le compte rendu d'un appel d'IA" (yellow, main), "Installer et démarrer le service" (violet), "Toute requête sans nom de client est refusée" (red).
- **Canvas columns:**
  - D'OÙ ÇA VIENT: Assistant d'IA surveillé, Personne qui installe et lance
  - PAR OÙ ÇA ENTRE ET CE QUI CONTRÔLE: the "Porte d'entrée du service" frame
  - OÙ ÇA FINIT: the Mémoire temporaire cylinder
- **Inside the frame:** wherever a bloc holds more than one step of the lit journey, the bloc is drawn as a dashed frame holding its component stations.
  - ① Contrôle du nom du client
  - ② Forme attendue d'un compte rendu
  - ③ Réception des comptes rendus
  - ④ Rangement des événements, inside the cylinder frame
  - ⑤ a dashed reply line back to the agent, labelled with the flux verbe "répond à" and quoi "201 avec l'EventOut, 401…, 422…"
- **Branches:** red dead-end spurs under ① ("Si l'en-tête X-Tenant-ID manque ou est vide" → 401) and ② ("Si le corps ne respecte pas EventIn" → 422).
- **Data chip:** on the main line, "compte rendu (dans le code : EventIn)". The code alias is shown as "pas encore dans le modèle" until `donnee` exists.
- **Atelier shelf** at the bottom: Documents de vision, Outils de contrôle du code (no line touches them).
- **Interchange rings:** stations used by 2 or more lines get a thick ring. In Watchdog that is Porte d'entrée (3 lines) and Contrôle du nom (2 lines: envoi step 1, acces-sans-client step 2).
- **Data sources:**

| Element | Model field |
|---|---|
| Station order | `parcours.etapes[].composant` → `composants[].bloc` (back-and-forth hops folded) |
| Line chosen | the journey with the most distinct composants (→ envoi-evenement), until `principal` exists |
| Station label | `etape.action` |
| Station sublabel | `composant.nom` |
| Spurs | `branches[]` |
| Arrows | `flux[]`, with `outillage→api` drawn as grey control |

**Screen 2, Ride** (same canvas, no navigation): press ▶ or a station.
- The bottom player bar shows "étape N sur 5 · action — simple · fichier:lignes" (e.g. `watchdog_ai/api/middleware/tenant_auth.py l.28-40`), using step `simple` and `fichier`/`lignes`.
- The lit station moves on every step: 4 of the 4 forward moves change station.
- A particle travels along the line, turned off under prefers-reduced-motion.
- ←/→ keys move between steps. Chips switch lines; the other lines dim.

**Screen 3, Station plate:** click a station. The side panel becomes the spec plate (shared block) for that component, with the 6 slots. The "Vu dans" entries jump to that step of that line.

**Where Q1–Q5 are answered:**
- Q1: the pitch in the top band.
- Q2: ENTRÉE/SORTIE badges and columns, plus the data chip.
- Q3: the stations and frames on the line, the interchange rings, and the shelf that says what is NOT a part of the flow.
- Q4: Ride mode, numbered stations ①–⑤.
- Q5: the station plate, Réglages row "Nom de l'en-tête X-Tenant-ID · tenant_auth.py:33".

**Built from:** Chercheur P1, P2; Designer P1, P2; NouveauVenu P1; Pedagogue P2; Inverseur P1.

**Risk:** a JusticIA-sized line (16 steps) needs `phases` to fold into ≤9 stations.

### Direction B — "Plan d'usine" (part-first rooms with zoom in place)

*One line:* a factory floor: a few big rooms (the core blocs) on one conveyor belt from IN to OUT. Entering a room opens it in place, on the same map and in the same direction, with its machines (components) in the order the data visits them and its neighbours as doors. The bottom level is the machine's spec plate.

**Screen 1, Floor:**
- One horizontal conveyor: ENTRÉE door "Assistant d'IA surveillé" → room "Porte d'entrée du service" (en_bref "Reçoit, contrôle et range les comptes rendus") → room/cylinder "Mémoire temporaire des événements" → SORTIE (with « Tout est perdu au redémarrage. »).
- The return belt "répond à" runs underneath.
- Each room shows a count badge, "4 machines · 4 étapes ici".
- "Personne qui installe et lance" is a side door with a grey control arrow "démarre".
- An "Autour du projet (ne tourne pas)" strip holds docs and tools.
- The pitch sits above the floor.
- **Data sources:**

| Element | Model field |
|---|---|
| Conveyor order | the main journey's bloc sequence |
| Rooms | `blocs` (importance coeur, on a journey) |
| Strip | blocs touched by no journey |
| Arrows | `flux` (verbe) |

**Screen 2, Room opened in place** (click "Entrer" or play the main journey):
- The room grows on the same canvas (semantic zoom). Neighbours shrink to labelled doors at the edges:
  - left door: "depuis Assistant d'IA surveillé — envoie ses comptes rendus à"
  - right door: "vers Mémoire temporaire — range l'événement dans"
- Inside, the machines are placed left to right in order of first appearance in the main journey: Contrôle du nom du client → Forme attendue d'un compte rendu → Réception des comptes rendus. The 401 and 422 refusal chutes hang below the first two.
- "Assemblage de l'application — Monte le service et branche ses morceaux · watchdog_ai/main.py" is a grey wiring band at the top, marked "câblage, au démarrage". It is not a machine on the belt.
- Fit rule: the room plus its doors always fit the canvas width minus the panel, and only vertical scroll is allowed. If anything is out of view, an edge indicator says "N hors champ →".
- The handoff route-events → stockage-events is drawn through the right door, which fixes the dropped cross-part arrow.
- The step list in the panel is grouped into chapters: "Dans « Porte d'entrée du service »" (steps 1–3), "Dans « Mémoire temporaire »" (step 4), "Retour à l'expéditeur" (step 5).

**Screen 3, Machine plate:** click a machine. A card slides up from the bottom of the room: the shared spec plate, with Reçoit and Rend drawn as small in/out arrows on the machine itself.

**Where Q1–Q5 are answered:**
- Q1: the pitch above the floor.
- Q2: the conveyor from the ENTRÉE door to the SORTIE cylinder.
- Q3: the rooms (2 core rooms plus 1 person) with their en_bref, and the strip for what is not a part.
- Q4: the room opened in place, machines numbered in journey order, chapters in the panel.
- Q5: the machine plate (Réglages + Où).

**Built from:** NouveauVenu P2; Pedagogue P1; Navigation P1; Designer P3, P1; plus the spec plate (Navigation P2, Chercheur P3, Pedagogue P3).

**Difference from A:** containment and places are primary, and only one journey is on the floor at a time. A shows all journeys as overlapping lines.

### Direction C — "Fiche + atlas" (question-first sheet with a synced outline and universal search)

*One line:* a dark one-page sheet whose headings ARE the five questions, each answered with a small diagram. A persistent outline on the left (zone › part › component › file › function) and one search over every level take you anywhere, and the plate opens on the right.

**Layout:** three panes.
- **Left: outline** (260px).
  - Grouped as: Qui l'utilise / Ce qui reçoit / Ce qui traite / Où c'est rangé / Atelier.
  - Hierarchy: Pièce › Composant › Fichier › Fonction (from `expose`, with file:line).
  - Flags "pas de composant" on Assistant d'IA surveillé, Personne qui installe et lance, Documents de vision, Outils de contrôle du code.
  - Footer count: "6 pièces · 5 composants · 9 fichiers décrits".
- **Centre: the sheet.** Each section is headed by the literal question:
  - "Q1 Ce que fait ce projet, pour qui": the pitch.
  - "Q2 D'où vient la donnée, où elle finit": a mini ENTRÉE → SORTIE strip, using the `depart`/`fin` of the main journey and the flux verbes.
  - "Q3 Les pièces principales": the core blocs as cards with grammar shapes and en_bref, plus the line "Pas sur le chemin : Documents de vision, Outils de contrôle du code". Parts, not components; this fixes the Inverseur Q3 issue.
  - "Q4 Une action réelle, pièce par pièce": a compact numbered station strip ①–⑤ (component names), with action + simple + file:lines under each, and branches as red notes using quand/alors (quand_simple once it exists).
  - "Q5 Pour changer quelque chose": a table "Je veux changer… → pièce → composant → réglage → fichier:ligne". Rows come from `pour_changer`. Today they are filled from verified code facts under the "pas encore dans le modèle" badge, e.g. "le contrôle du nom du client → Porte d'entrée › Contrôle du nom du client → X-Tenant-ID → tenant_auth.py:33-38".
- **Right: plate** (380px). The shared spec plate for whatever is selected.

**Search** (Ctrl K, top):
- Indexes blocs, composants, expose functions, files, journey steps, branches, incertitudes and (later) reglages, termes and pour_changer.
- Results are grouped by kind. Each shows its full address, e.g. "Porte d'entrée du service › Contrôle du nom du client".
- "nom du client" returns the component plus 6 steps (Navigation measured this in node; I did not re-run it).
- Selecting a result syncs the outline and opens the plate.

**Interaction:**
- Every name in the sheet is a link that selects it in the outline and plate.
- Q4 has a "▶ rejouer sur la carte" button that animates the strip in place. No separate canvas, so no "a click sent me somewhere else".

**Where Q1–Q5 are answered:** literally under the headings Q1–Q5. Search and the outline back up Q3 and Q5.

**Built from:** Inverseur P3 (sheet, made dark, Q3 at part level); Navigation P3 (outline and search); NouveauVenu P3 (termes chips in the plate); Inverseur P2 (`pour_changer`).

**Why it is a real alternative:** it bets that comprehension comes first from answered questions plus an index, with the visual as support. A and B bet on the map. The 5-minute human test (method change 11) should run A or B against C on the same Watchdog data.

## 6. Order of work I recommend

1. Grammar (M4, cost S) and the Atelier shelf. These are UI-only, cost S each, and remove the false Q2/Q3 reading at once.
2. One of A or B as the canvas, plus the spec plate with the "pas encore dans le modèle" fallback.
3. Method changes 1, 2, 5, 6 and 7.
4. Search over components (Navigation P3). Cheap, and it unlocks Q5.
5. A timed human test of the chosen direction against C.

---
name: umbra
description: Open the Umbra map of this repo in the browser, then answer every question about the repo in at most 3 lines plus one `show` call that lights the answer on the map. Use when the user types /umbra, and for "où / comment / quoi / qui appelle" questions about the repo once the map is open.
---

# Umbra: the map answers, the terminal stays short

Umbra draws this repo as one map in a browser tab (boxes left to right, ENTRÉE, ◉ SORTIES). You answer
questions in the terminal in a few lines and light the answer on that map with the `show` tool of the
`umbra` MCP server. Umbra never runs a model itself: you are the only one.

## 1. Open the map

Run, from the repo root:

```bash
umbra-engine open "<repo root>"
```

- It prints a link and opens the tab on this repo's map. Say one line, in French: `Carte de <repo> ouverte`
  and the link.
- `no engine answers`: start it in the background (Bash `run_in_background`) with
  `umbra-engine start "<repo root>"`; it reads the repo and opens the tab itself. Tell the user the first
  open of a new repo reads it first (a few seconds to a minute).
- `umbra-engine: command not found`: say Umbra is not installed and point to
  https://github.com/rida12b/Umbra/blob/main/engine/README.md. Stop there.

## 2. Answer each repo question on the map

For every question about where, how or what in this repo:

1. Find the answer in the code first (Read, Grep). Name only places that exist; a new file is fine when its
   folder exists.
2. Answer in French in **at most 3 lines**. No file list in the terminal: the map shows it.
3. Call `show` once:
   - `caption`: the question as the user asked it, one line.
   - `path`: up to 6 places, in the order to read or change them. Each `{part, note, why}`: `part` is a repo
     path (file, or folder ending with `/`) or a box of the map; `note` is 2-4 French words
     (« ajouter le champ », « nouvelle migration », « vérifier »); `why` is one French sentence shown on hover.
   - `parts`: boxes the answer reaches without a step of its own (e.g. `Base`).
   - When the whole answer sits inside one box, name its parts as « Box/Part » (« Serveur/Contrôle d'accès »,
     « Serveur/Base »): the map opens that box and numbers its parts. Every step must then be in that box.
4. If `show` refuses a name, it lists the valid boxes: correct the call and send it again.
5. End with « → regarde la carte. »

Example, « où j'ajoute un champ prix à Item ? » on a FastAPI + React template:

```
Du modèle à l'écran : le modèle, une migration, les routes à vérifier,
le client à recréer, le formulaire et le tableau. → regarde la carte.
```

then `show` with `caption` « où j'ajoute un champ prix à Item ? », `parts` `["Base"]` and `path`
`backend/app/models.py` (ajouter le champ), `backend/app/alembic/versions/` (nouvelle migration),
`backend/app/api/routes/items.py` (vérifier), `frontend/src/client/` (recréé automatiquement),
`frontend/src/components/Items/` (formulaire, tableau).

The user's « copier pour Claude » button copies the path's files with the question, ready for an agent.

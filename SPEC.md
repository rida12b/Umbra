# Umbra — System Explorer (V1)

Vocabulary: `GLOSSARY.md`. Structural decisions: `docs/adr/`. Prior art: `docs/research/2026-10-18-prior-art.md`. Feasibility: `docs/spikes/m0-results.md`.

## Who and why

An engineer (first the author, later any engineer) must understand an unknown software system — what it does, its Journeys, its Components — without reading the code by hand, then follow how it evolves while Claude Code works on it. Today that understanding lives in terminal scrollback, AI conversations and thousands of lines of code.

"It works" means: the engineer opens a Project, understands it from the Application level down, follows a Journey end to end, and sees each Claude Code change appear on the map with its reason, while every Claim shows whether it is a Fact, a Hypothesis or an Observation.

## Core promise

Understand any software system by its behaviour, Journeys and Components, then follow its evolution automatically while Claude Code works — not just a code graph.

Success conditions (all must hold):
- Navigation from Application to Function on every Validation Corpus Project, nothing permanently hidden.
- Every Claim carries its status and Evidence (ADR-0001).
- At least one complete Journey per corpus Project.
- Claude Code edits appear on the structural map without the user asking, with their attribution.
- The engine, the map and the sync work with zero LLM calls.
- No code or data leaves the machine except through Claude Code on the user's own subscription, with secrets excluded.

## Architecture (fixed)

- **Engine**: one local Python daemon per machine (ADR-0002). Versioned REST `/v1` + SSE on 127.0.0.1 with a local token. Clients: Umbra UI, MCP server for Claude Code, future dashboard. None reads the store directly.
- **Claim Store**: one SQLite store per Project in `~/.umbra/projects/<id>/`. A Claim = subject → relation → object + status + Evidence + producer@version + git commit. Views, Journeys and history are computed from Claims.
- **Secret Guard**: the only way the engine reads Project files (ADR-0004). Analyzers receive guarded content, never paths to open.
- **Declarations**: configuration (compose, k8s, Terraform, manifests) produces Declarations — Facts about what is declared. A Declaration is never shown as proof that something runs or is deployed; only an Observation can say that.
- **Analyzers** (pluggable, contract `detect(project) → bool`, `analyze(files) → claims`): language (tree-sitter tags queries), framework (ast-grep rules), artifacts (compose, k8s, Terraform, manifests, OpenAPI), runtime (test runs with tracing → Observations).
- **Projection**: five Zoom Levels; Components with stable IDs, formed from facts first (deployable units → packages/manifests → directories), clustering only for flat code, named by the LLM (Hypothesis); ~12 elements per view as a UX preference; Human Overrides on top.
- **Journey engine**: from Entry Points, follow calls and branches; named by behaviour.
- **Sync**: file watcher = detection; Claude Code hooks = attribution (session, prompt, Claude's final message) through a persistent local event journal; incremental reanalysis of changed files only.
- **LLM enrichment**: batched, budget per Project, through the user's official `claude` CLI (`-p --safe-mode`, conditions in ADR-0003) or an interactive Claude Code session. Never blocks Facts.
- **UI**: React component library + thin standalone app (embeddable or iframe).
- **Code layout**: new engine built next to the v0.7 package; v0.7 removed in a separate PR after V1 validation.

## Scenarios (= implementation order)

### S1 — Index a Project and expose its claims
- **Trigger**: the user registers a folder (`umbra add <path>`) or the API receives `POST /v1/projects`.
- **Steps**: detect languages and artifacts → run every matching analyzer → write claims with status, evidence and commit → list Coverage Gaps.
- **Done when**:
  - 100 % of tracked files are either covered by an analyzer or listed as a Coverage Gap with a reason.
  - 30 Facts sampled at random per corpus Project point to the right file and line range (100 %).
  - Secrets and sensitive files (`.env*`, keys, certificates, gitleaks patterns, `.umbraignore`) are never stored as content and never sent to an LLM; a test fixture with planted secrets proves it.
  - Initial index of a ≤ 80k-LOC Project < 2 min without LLM, on the reference machine described in the validation report (Windows 11 laptop, CPU and RAM recorded).
- **Out of scope**: names and summaries (S4), Journeys (S3).

### S2 — Navigate from Application to Function
- **Trigger**: the user opens a Project in the UI (or a client calls the view endpoints).
- **Steps**: Application → Architecture → Component → Module → Function; each element shows status, evidence link, Coverage Gaps; the user can apply Human Overrides (move, rename, merge, split), see their history and revert them.
- **Done when**:
  - All five levels are reachable on every corpus Project; no element is unreachable.
  - ≥ 90 % of real deployable parts (checked against compose/k8s/Terraform/README) appear at Architecture level.
  - A Human Override wins for display, survives reindexing, is reversible, and a contradicting Fact is shown next to it with a conflict flag.
  - Editing one file never changes the Component of an unrelated Module (stable IDs, tested).
  - Screenshots desktop (1280 px) and mobile (375 px), light and dark.
- **Out of scope**: animated Journeys (S3), cross-Project views.

### S3 — Follow a Journey end to end
- **Trigger**: the user picks a Journey from the list (named by behaviour, e.g. "Login").
- **Steps**: start at an Entry Point → follow calls → show inputs, processing, outputs and condition branches (`if`/`try`/`match`/early `return`) → mark each step Fact / Hypothesis / Observation → show alternative paths (error, empty result, missing rights) when the code has them.
- **Done when**:
  - ≥ 1 Complete Journey per corpus Project, checked by a reviewer other than its producer (an independent agent, then the author) against the code with a checklist: Entry Point exists, every step has Evidence or a label, every final output is reached, every branch in the code is listed.
  - On ≥ 2 corpus Projects, Journey steps are confirmed as Observations by running the Project's tests with tracing.
  - Projects needing external keys are analysed statically only and say so.
  - Unresolved hops (queues, dependency injection, dynamic dispatch) appear as Hypothesis or Coverage Gap, never as Facts.
- **Entry Point kinds**: the model defines HTTP route, CLI command, screen action, pipeline run, deployment, event, async job, message queue, AI agent tool and game loop/event. V1 analyzes the first five in depth (FastAPI / Express / Next.js, click / typer / argparse, React / React Native, dbt, Terraform / k8s); the others are recognized where possible and shown as Hypothesis or Coverage Gap. Each kind keeps its own shape (a pipeline is a DAG, a deployment is a resource graph), never forced into a request/response.
- **Branch analysis**: Python and TS/JS in V1; other languages follow calls without branches, marked as Coverage Gap.
- **Honesty rule**: a Journey is never invented to meet a criterion. Unresolved parts are Hypothesis or Coverage Gap, and an incomplete Journey is labelled incomplete.
- **Out of scope**: Journeys spanning several Projects, production traces.

### S4 — Enrich with AI under a budget
- **Trigger**: Project import, end of a Claude Code session (changed Components only), or the "Enrich" action.
- **Steps**: build batches → call the user's `claude -p --safe-mode` (one at a time, stdin only, no tools, API-key variables stripped, `authMethod` must be `claude.ai`) → store results as Hypotheses with producer and inputs.
- **Done when**:
  - Default budget 40 calls per import, configurable per Project; the budget is never exceeded (tested).
  - 30 Hypotheses sampled per corpus Project are judged correct ≥ 80 % by an independent reviewer against the code (correct / partly correct / wrong; partly correct counts as wrong).
  - With enrichment disabled, S1–S3 and S5 still pass.
  - The UI lists what Umbra itself sent to Claude (files, time). It does not claim to know what Claude Code reads in the user's own sessions.
- **Out of scope**: API keys, other LLM providers, local models.

### S5 — Follow Claude Code live
- **Trigger**: Claude Code edits files in a registered Project (terminal or VS Code), or the user edits them.
- **Steps**: watcher detects → incremental reanalysis → SSE `map.updated` → hooks append to the event journal (session, tool, files, prompt, Claude's final message) → the change is attributed on the map and in a timeline; architectures before/after can be compared.
- **Done when** (experimental objectives, p95 over ≥ 20 samples per scenario, structural map only):
  - Edit → detection < 3 s; edit → updated map < 5 s; hook cost < 50 ms per tool call.
  - ≥ 95 % of Claude edits in a sample of ≥ 20 are linked to their prompt and Claude's final message.
  - Event journal: unique event IDs, idempotent processing (replaying the journal twice gives the same store), resume after daemon restart, safe concurrent writers (several hooks and sessions at once). Fault tests: daemon killed mid-burst, daemon down during edits, power-cut simulation (truncated last line), 2 parallel Claude sessions. **Measured loss is reported per fault; no zero-loss claim beyond what the tests show.**
  - Validated live on Watchdog **in the terminal and in the VS Code extension** before V1 delivery: the same measures and the linking criterion, on ≥ 20 edits in each.
- **Out of scope**: task/test/metric dashboard, pushing notifications into Claude.

### S6 — Validate on the corpus
- **Trigger**: S1–S5 done.
- **Corpus**: full-stack-fastapi-template, miurla/morphic, chatwoot/chatwoot-mobile-app, assafelovic/gpt-researcher, matsonj/nba-monte-carlo, aws-containers/retail-store-sample-app, open-telemetry/opentelemetry-demo, aws-ia/terraform-aws-eks-blueprints (IaC only), + Watchdog live.
- **Done when**: every criterion above holds on every corpus Project, and the final judge passes — **on a repo they have never seen, the author answers correctly 5 questions about how it works in 15 minutes, without opening the code.** The questions and their answer key are written beforehand by an independent agent from the repo, and graded by it.

## Known limits

- Dynamic languages give fewer Facts: name-matched calls stay Hypotheses until a resolver (V2) confirms them.
- Static Journeys break on queues, dependency injection, events and reflection; these hops are shown as Hypothesis or Coverage Gap.
- Observations need tests that run locally; mobile and games get little or none in V1.
- The Application level is always Hypothesis: business purpose is not in the code.
- Umbra cannot see what Claude Code reads during the user's own sessions.
- Enrichment shares the user's 5-hour and weekly Claude limits with interactive work.
- Windows 8.3 short paths must never reach Claude Code (it blocks edits).
- Each tree-sitter grammar has its own license; to audit before bundling.
- Anthropic's usage policy has a new version effective 2026-11-12 (per its page on 2026-10-18); the `claude -p` conditions must be re-checked then.
- Monorepos above ~80k LOC are not a V1 target; behaviour there is measured, not promised.

## Non-goals (V1)

- Central multi-project dashboard — later, as an API client.
- Deep game-engine analysis (Unity, Godot) — engine stays universal, analyzers in V2.
- SCIP/LSP precision resolvers, codebase-memory-mcp adapter — V2.
- Pedagogical coach, simulations, exercises — V2.
- Task / test / metrics dashboard (latency, memory, CPU before/after) — V2.
- Stale-explanation detection across versions — V2.
- Team sharing, hosted mode — never without a new decision (privacy, Anthropic terms).
- API keys or extra billing — excluded by decision.

## Installation (V1)

From the repository only: one documented, reproducible procedure on Windows covering the Python engine, the React UI and the Claude Code plugin (`git clone` → install → `umbra` starts the daemon and serves the UI → plugin loaded from the repo). Publishing to PyPI / a plugin marketplace comes after V1 validation.

## Open questions

- Umbra stays MIT — revisit if a dependency or contributor model requires it.

# M0 spike — measurement protocol

Goal: prove (or disprove) that Umbra can follow Claude Code edits live, before writing SPEC.md. The spike code is throwaway (branch `spike/m0`, folder `spike/m0/`). Only this protocol and the results report survive.

Targets are **experimental objectives, not guarantees**. The map measured here is the **structural map only** (tree-sitter claims), never waiting for LLM enrichment.

## Measures (each reported separately)

| Id | What | Start (t0) | End (t1) | Target p95 |
|---|---|---|---|---|
| T-detect-hook | Edit → daemon receives the hook event | file mtime after the write | daemon receive timestamp | < 1 s |
| T-detect-watch | Edit → daemon receives the file-watcher event | file mtime | daemon receive timestamp | < 3 s |
| T-visible | Edit → updated structural map available to a client | file mtime | client got SSE `map.updated` **and** fetched a map containing the change (content check) | < 5 s |
| T-hook-cost | Cost of our hooks on Claude Code | — | A/B: `duration_ms − duration_api_ms` of the same `claude -p` task, hooks on vs off; plus the hook process wall time | < 50 ms per tool call |
| T-reparse | Analyzer time for one changed file | analyzer start | claims written | < 1 s |
| C-child | `claude -p --safe-mode` works on the Team subscription login on Windows, without triggering our hooks | — | result returned, 0 hook events tagged as child | pass/fail |

All timestamps come from one clock (`time.time_ns()` on the same machine). p50, p95 and max are reported; p95 needs ≥ 20 samples per scenario.

## Scenarios

| Id | Scenario | Channel | Samples |
|---|---|---|---|
| S1 | Small edit in one existing file | hook + watcher | 50 |
| S2 | New file created | hook + watcher | 20 |
| S3 | Burst: 10 files edited within 2 s | hook + watcher | 10 bursts |
| S4 | Edit in the largest source file of the repo | hook + watcher | 20 |
| S5 | Delete / rename through the shell (no hook) | watcher only | 20 |
| S6 | Real Claude Code edits (`claude -p` with the spike plugin) | hook + watcher | ≥ 20 edits |

S1–S5 are scripted: the harness writes the file, then calls the real hook script with a payload shaped like Claude Code's `PostToolUse` input. S6 uses the real Claude Code CLI.

## Repos

Two representative repos, copied into a scratch directory (never edited in place):

- `fastapi/full-stack-fastapi-template` — Python + TypeScript web app.
- `open-telemetry/opentelemetry-demo` — polyglot monorepo (TS, Go, Python, C#, Java, Elixir…).

T-reparse runs on every source file of both repos.

## Known limits of the spike

- The VS Code extension cannot be driven by script; hooks load there per the docs, but that is not measured here.
- No UI: "visible" means available to an API client. Rendering time is out of scope.

## GO / NO-GO

GO when every target is met or the gap has a known, cheap fix. Otherwise the architecture is revised before SPEC.md.

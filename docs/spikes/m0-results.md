# M0 spike — results (2026-10-18)

Protocol: `m0-protocol.md`. Machine: Windows 11, Python 3.13.7, Claude Code 2.1.302, Team subscription login. Repos: fastapi-template (217 indexed modules) and opentelemetry-demo (482 modules, 12+ languages). Spike code lived on branch `spike/m0` (throwaway).

**Verdict: GO.** Every target is met, most by an order of magnitude. Targets remain experimental objectives.

## Measures

| Measure | Target p95 | fastapi p95 | otel p95 | Real Claude (S6) p95 |
|---|---|---|---|---|
| T-detect-watch | < 3 s | 2–8 ms | 2–5 ms | 27 ms |
| T-detect-hook | < 1 s | 219–312 ms | 179–240 ms | 414 ms |
| T-visible | < 5 s | 223–520 ms | 233–440 ms | 56 ms (server side) |
| T-reparse | < 1 s | warm 1.3 ms; in daemon 77 ms (842 runs, max 344 ms) | warm 1.9 ms (max 44 ms) | — |
| T-hook-cost | < 50 ms / tool call | — | — | +62 ms per run of 5 edits ≈ +12 ms per edit (n = 5 per arm, noisy) |
| C-child | pass | — | — | **pass**: enrichment call works on Team login with `--safe-mode`; our plugin hook fired in normal `-p` (1) and not under `--safe-mode` (0), even with `--plugin-dir` |

Scenario samples: S1 50, S2 20, S3 100 (10 bursts), S4 20, S5 20 per repo; S6 25 hooked edits + 61 writes seen by the watcher. Hook process wall time: p50 161 ms, p95 224 ms.

Initial full index: fastapi 7.1 s, otel 20.2 s (includes first-time grammar download).

## Findings

1. **The watcher is the fast detection path; the hook is the attribution path.** The hook costs a Python start-up (~160 ms) and only sees Claude's own tool calls. Its value is the context (session, tool, later prompt and explanation), not speed.
2. **Hook → daemon over HTTP takes 2.2 s when the daemon is down** (Windows retries refused localhost connections). Claude does not wait (async hook), but events are lost. A local append-only spool file read by the daemon would remove both problems.
3. **Windows 8.3 short paths** (`<USER>~1`) make Claude Code refuse edits ("blocked, waiting for approval"). Umbra must always hand long, resolved paths to Claude and compare resolved paths internally.
4. **Coverage Gaps are large on real repos**: 30 % (fastapi) and 41 % (otel) of indexed files have no tags query — YAML, JSON, Markdown, Dockerfile, TOML, SQL. Expected: these are artifact analyzers planned for M1.
5. C# tags query yields definitions but no calls; Terraform/HCL has no tags query at all.
6. Client-side T-visible includes a new HTTP connection per check, so it is an upper bound; server-side visibility after a real Claude edit is p95 56 ms.
7. One watcher event arrived with a 715 s old mtime after a no-op `git checkout`; it is not an edit and was excluded from the reading of p95 (it only affects max).

## Not measured

- VS Code extension (cannot be scripted). Hooks load there per the docs; to confirm during M4 on a live Watchdog session.
- UI rendering time (no UI in the spike).

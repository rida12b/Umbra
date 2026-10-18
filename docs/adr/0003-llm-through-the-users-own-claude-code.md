# LLM calls go through the user's own Claude Code, never an API key

Status: accepted (2026-10-18)

Umbra must add no API key and no extra billing, and must stay usable by other engineers as an open-source tool. So every AI call goes through the user's own, unmodified `claude` CLI on their own subscription: in an interactive Claude Code session, or in the background with `claude -p`. Anthropic's legal page (read 2026-10-18) forbids third-party tools to offer Claude login, to route other users' requests through a subscription, or to handle its credentials, but states that this "does not prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription". Umbra stays inside that case. The engine, the map and the sync must work with zero LLM calls; if background `claude -p` ever becomes disallowed, enrichment moves to interactive sessions only.

## Conditions every background call respects

1. Spawn only the user's installed `claude`; never bundle or modify it.
2. Never read, store or forward credentials; run only when `claude auth status` reports `authMethod: claude.ai`.
3. Remove `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` and `CLAUDE_CODE_USE_*` from the child environment (an API key silently wins in `-p` mode).
4. No hosted or shared mode: each user runs Umbra with their own login.
5. No Anthropic or Claude Code name or logo in the product name.
6. Bounded volume: one call at a time, a budget per Project, `--max-turns 1`.
7. Never `--bare` (it disables subscription login); use `--safe-mode --no-session-persistence --tools ""`, content on stdin, an empty temporary working directory, and an `UMBRA_CHILD=1` guard in Umbra's own hooks.
8. Re-check the usage policy when a new version takes effect (one is announced for 2026-11-12).

## Consequences

- Background calls share the user's 5-hour and weekly limits with their own work, hence the budget.
- Umbra can only list what it sends itself; it cannot see what Claude Code reads during the user's sessions.

## Considered Options

- **API key**: simplest to automate, but adds billing, which is excluded.
- **Local model**: nothing leaves the machine, but explanation quality is much lower.

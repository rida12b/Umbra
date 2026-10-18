# Hybrid analysis, every Claim carries a knowledge status

Status: accepted (2026-10-18)

Umbra builds its picture of a system from two kinds of sources: deterministic analysis of the code and artifacts, and AI inference. When they are mixed silently, a reader cannot tell what is proven: in the versions we read on 2026-10-18, Understand Anything lets the LLM emit final edges, and Graphify files resolver output and LLM output under the same `INFERRED` tag. We decided that every Claim Umbra shows carries exactly one status — **Fact**, **Hypothesis** or **Observation** — and the evidence behind it: a source span (file + line range) for a Fact, the producer (analyzer or model + version) and its inputs for a Hypothesis, and the execution artifact (trace, test run, log) for an Observation. A name-matched call that no resolver has confirmed is a Hypothesis, not a Fact.

## Considered Options

- **All-LLM** (Umbra v0.7): covers business-level meaning, but is non-deterministic, costly and cannot be traced to code.
- **All-deterministic**: fully trustworthy, but cannot describe the Application level (business purpose, users).
- **Hybrid with confidence scores only** (GitNexus, codebase-memory-mcp): scores are uncalibrated and do not tell a guess from a resolution without reading a side field.

## Human Overrides are not a fourth status

Manual corrections (e.g. moving a Module to another Component, renaming a Component) are recorded as **Human Overrides**, a separate mechanism, not as evidence. An Override wins for display, is versioned and reversible, but never hides a contradicting Fact: when one exists, both are shown and the conflict is flagged.

## Consequences

- The UI must always show the status and give one-click access to the evidence.
- Statuses can be upgraded (Hypothesis → Fact when a resolver confirms; → Observation when a trace confirms) but never inferred upward without new evidence.
- Fewer Facts in dynamic languages until precision resolvers exist; we accept this to stay honest.

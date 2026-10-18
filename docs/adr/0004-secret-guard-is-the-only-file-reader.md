# The Secret Guard is the only reader of Project files, enforced by construction and in CI

Status: accepted (2026-10-18)

Umbra reads whole codebases and later sends parts of them to an LLM, so one forgotten `open()` in a future Analyzer would leak a secret into the store or to Claude. A convention is not enough. Only the Secret Guard may read Project files or list their names; Analyzers never receive a path they could open, only guarded content (secrets already redacted) or the reason a file was skipped. This is enforced three ways: the guard hands out content it alone can construct; listing and reading helpers are private to the guard package; and a CI test parses every engine module and fails on any file-reading or directory-walking call outside an explicit allowlist, with a deliberately bad fixture proving the test catches violations.

## Consequences

- Adding a file read anywhere in the engine requires changing the allowlist, which is visible in review.
- Content excluded by the guard is a Coverage Gap, never silently ignored.
- Python cannot sandbox in-process code: a deliberately malicious change could still bypass the rules. The enforcement targets mistakes, and review targets intent.

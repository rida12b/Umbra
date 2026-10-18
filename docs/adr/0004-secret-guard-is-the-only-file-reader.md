# The Secret Guard is the only reader of Project files, enforced by construction and in CI

Status: accepted (2026-10-18)

Umbra reads whole codebases and later sends parts of them to an LLM, so one forgotten `open()` in a future Analyzer would leak a secret into the store or to Claude. A convention is not enough. Only the Secret Guard may read Project files or list their names; Analyzers never receive a path they could open, only guarded content (secrets already redacted) or the reason a file was skipped.

Enforced in three ways (implemented in S1, ticket T2):

1. **Capability**: file listing is private to the guard package, the guard's root and rules are private, and its public API takes no rule override.
2. **Sealed content**: a `GuardedFile` can only be constructed by the guard.
3. **CI architecture test** (`engine/tests/test_guard_boundary.py`): parses every engine module outside the guard and fails on a fixed list of names and modules that read files, list directories, run programs, use introspection or dynamic code (`getattr`, `vars`, `exec`…), reach guard internals or copy a dataclass. A deliberately bad Analyzer fixture proves each rule still fires. Exceptions live in one reviewed allowlist (Umbra's own token file and stores).

## Consequences

- Adding a file read anywhere in the engine requires changing the allowlist, which is visible in review.
- Content excluded by the guard is a Coverage Gap, never silently ignored.
- The test matches names, it does not prove what code does: Python cannot sandbox in-process code, so deliberately obfuscated code can still get around it. The enforcement targets mistakes (a hurried developer or an LLM), and review targets intent.

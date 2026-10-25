# Umbra — rules for agents

- Before opening a UI PR, put the validated mockup (`docs/design/…`) and a real screenshot side by side, list every visual difference, and fix it or get Rida's OK for it: on 2026-10-25 #75/#76 shipped with the right rules but a look unlike mockup B.
- Before pushing, run what CI runs (`cd engine && python -m pytest -q && ruff check . && pyright src tests`, `cd ui && npm test && npm run build`): PR #83 failed CI on ruff that was never run locally.
- Never format or lint `engine/tests/fixtures`: they are verbatim copies of a real project and tests cite their line numbers.

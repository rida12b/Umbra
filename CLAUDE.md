# Umbra — rules for agents

- Before opening a UI PR, put the validated mockup (`docs/design/…`) and a real screenshot side by side, list every visual difference, and fix it or get Rida's OK for it: on 2026-10-25 #75/#76 shipped with the right rules but a look unlike mockup B.
- Before pushing, run what CI runs (`cd engine && python -m pytest -q && ruff check . && pyright src tests`, `cd ui && npm test && npm run build`): PR #83 failed CI on ruff that was never run locally.
- Never format or lint `engine/tests/fixtures`: they are verbatim copies of a real project and tests cite their line numbers.
- Never call a screen readable on an agent dry run alone: agents read everything and always find the answer; on 2026-10-26 Rida, cold on a new project, found the floor not intuitive at all after #81's agent runs passed. A 2-minute cold look by a human (or a first-glance screenshot review: where does the eye land, what is said twice) comes first.

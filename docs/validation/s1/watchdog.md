# watchdog

local Project — local folder @ `local`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 16 files = 12 covered + 0 partial + 4 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 27/27 (every Fact: fewer than the sample size exist) |
| Initial index < 120 s for ≤ 80,000 lines | yes: 0.4 s for 732 lines |
| Claims | fact 27, hypothesis 28; secrets redacted: 0 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for markdown: 2
- no analyzer for *.example: 1
- no analyzer for *.gitignore: 1

Partly analysed:
- none

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `defines` | `watchdog_ai/api/middleware/tenant_auth.py::TenantAuthMiddleware` | `watchdog_ai/api/middleware/tenant_auth.py:25-40` | (private Project: not reproduced) |
| ok | `imports` | `fastapi` | `watchdog_ai/main.py:9-9` | (private Project: not reproduced) |
| ok | `requires` | `package:pypi/uvicorn` | `pyproject.toml:15-15` | (private Project: not reproduced) |
| ok | `imports` | `watchdog_ai.ingestion.schemas` | `watchdog_ai/api/routes/events.py:10-10` | (private Project: not reproduced) |
| ok | `imports` | `uuid` | `watchdog_ai/ingestion/schemas.py:5-5` | (private Project: not reproduced) |
| ok | `imports` | `starlette.responses` | `watchdog_ai/api/middleware/tenant_auth.py:22-22` | (private Project: not reproduced) |
| ok | `imports` | `pydantic` | `watchdog_ai/ingestion/schemas.py:7-7` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/api/routes/events.py::create_event` | `watchdog_ai/api/routes/events.py:21-23` | (private Project: not reproduced) |
| ok | `imports` | `typing` | `watchdog_ai/ingestion/schemas.py:4-4` | (private Project: not reproduced) |
| ok | `imports` | `watchdog_ai.api.routes.events` | `watchdog_ai/main.py:12-12` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/ingestion/schemas.py::EventIn` | `watchdog_ai/ingestion/schemas.py:10-36` | (private Project: not reproduced) |
| ok | `imports` | `datetime` | `watchdog_ai/ingestion/schemas.py:3-3` | (private Project: not reproduced) |
| ok | `requires` | `package:pypi/ruff` | `pyproject.toml:20-20` | (private Project: not reproduced) |
| ok | `requires` | `package:pypi/pyright` | `pyproject.toml:19-19` | (private Project: not reproduced) |
| ok | `imports` | `watchdog_ai.api.middleware.tenant_auth` | `watchdog_ai/main.py:11-11` | (private Project: not reproduced) |
| ok | `imports` | `fastapi` | `watchdog_ai/api/routes/events.py:8-8` | (private Project: not reproduced) |
| ok | `imports` | `watchdog_ai.ingestion.schemas` | `watchdog_ai/storage/events.py:7-7` | (private Project: not reproduced) |
| ok | `requires` | `package:pypi/pydantic` | `pyproject.toml:14-14` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/api/middleware/tenant_auth.py::TenantAuthMiddleware.dispat` | `watchdog_ai/api/middleware/tenant_auth.py:28-40` | (private Project: not reproduced) |
| ok | `imports` | `datetime` | `watchdog_ai/storage/events.py:5-5` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/storage/events.py::list_events` | `watchdog_ai/storage/events.py:23-25` | (private Project: not reproduced) |
| ok | `imports` | `starlette.middleware.base` | `watchdog_ai/api/middleware/tenant_auth.py:20-20` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/storage/events.py::append_event` | `watchdog_ai/storage/events.py:12-20` | (private Project: not reproduced) |
| ok | `imports` | `starlette.requests` | `watchdog_ai/api/middleware/tenant_auth.py:21-21` | (private Project: not reproduced) |
| ok | `defines` | `watchdog_ai/ingestion/schemas.py::EventOut` | `watchdog_ai/ingestion/schemas.py:39-41` | (private Project: not reproduced) |
| ok | `imports` | `watchdog_ai.storage.events` | `watchdog_ai/api/routes/events.py:11-11` | (private Project: not reproduced) |
| ok | `requires` | `package:pypi/fastapi` | `pyproject.toml:13-13` | (private Project: not reproduced) |

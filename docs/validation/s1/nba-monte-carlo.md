# nba-monte-carlo

data pipeline (dbt, DuckDB) — https://github.com/matsonj/nba-monte-carlo @ `e8bf34f252923a640ad224d24e49f007684016ba`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 273 files = 14 covered + 1 partial + 258 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 2.3 s for 25,075 lines |
| Claims | fact 75, hypothesis 972; secrets redacted: 0 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for sql: 176
- no analyzer for markdown: 20
- no analyzer for yaml: 16
- no analyzer for json: 8
- no analyzer for *.gitkeep: 8
- no analyzer for csv: 7
- no analyzer for *.gitignore: 4
- no analyzer for svelte: 3
- too large: 2
- binary: 2
- no analyzer for *.gitattributes: 1
- no analyzer for *.python-version: 1
- no analyzer for LICENSE: 1
- no analyzer for Makefile: 1
- no analyzer for *.sources: 1
- no analyzer for toml: 1
- no analyzer for html: 1
- excluded: sensitive (sensitive path): 1
- no analyzer for css: 1
- no analyzer for *.malloynb: 1
- no analyzer for *.malloy: 1
- no analyzer for *.lock: 1

Partly analysed:
- definitions unverified for bash (Hypotheses): 1
- imports not extracted for bash: 1
- calls not extracted for bash: 1

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::model.get_` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:643-652` | `def get_playoff_eligible(standings_df: pl.DataFrame, conf: str) -> List[str]:` |
| ok | `defines` | `transform/models/nba/prep/nba_elo_rollforward.py::model` | `transform/models/nba/prep/nba_elo_rollforward.py:14-36` | `def model(dbt, sess):` |
| ok | `requires` | `package:pypi/duckdb` | `pyproject.toml:11-11` | `"duckdb~=1.3.0",` |
| ok | `defines` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py::model` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:265-470` | `def model(dbt, sess):` |
| ok | `imports` | `numpy` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:3-3` | `import numpy as np` |
| ok | `defines` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py::_determine` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:166-252` | `def _determine_actual_tiebreaker(df: pl.DataFrame, group_keys: List[str], criteria: List[p` |
| ok | `defines` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py::_build_lon` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:6-21` | `def _build_long_games(simulator: pl.DataFrame) -> pl.DataFrame:` |
| ok | `imports` | `dlt.sources.helpers` | `dlt/nfl_pipeline.py:4-4` | `from dlt.sources.helpers import requests` |
| ok | `requires` | `package:pypi/shandy-sqlfmt` | `pyproject.toml:15-15` | `"shandy-sqlfmt[jinjafmt]",` |
| ok | `requires` | `package:pypi/dbt-core` | `pyproject.toml:8-8` | `"dbt-core==1.9.4",` |
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::_get_h2h_p` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:243-246` | `def _get_h2h_pct_among_tied(team: str, tied_group: List[str], all_h2h_records: Dict[Tuple[` |
| ok | `defines` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py::_team_reco` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:24-30` | `def _team_records(long_games: pl.DataFrame) -> pl.DataFrame:` |
| ok | `requires` | `package:pypi/dbt-duckdb` | `pyproject.toml:9-9` | `"dbt-duckdb",` |
| ok | `imports` | `polars` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:2-2` | `import polars as pl` |
| ok | `imports` | `dlt` | `dlt/nba_pipeline.py:1-1` | `import dlt` |
| ok | `imports` | `sqlmesh` | `sqlmesh/models/prep/nba_elo_rollforward.py:3-3` | `from sqlmesh import ExecutionContext, model` |
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::_get_div_p` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:248-251` | `def _get_div_pct(team: str, all_div_records: Dict[str, Tuple[int, int]]) -> float:` |
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::calculate_` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:35-50` | `def calculate_head_to_head(team1: str, team2: str, results: pl.DataFrame, team_map: Dict[s` |
| ok | `imports` | `os` | `utils/load_season_summary.py:1-1` | `import os` |
| ok | `requires` | `package:pypi/polars` | `pyproject.toml:17-17` | `"polars"` |
| ok | `imports` | `dlt.sources.helpers` | `dlt/nba_pipeline.py:2-2` | `from dlt.sources.helpers import requests` |
| ok | `defines` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py::_sov_metri` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:128-144` | `def _sov_metrics(candidates: pl.DataFrame, long_games: pl.DataFrame, team_records: pl.Data` |
| ok | `requires` | `package:npm/@evidence-dev/core-components` | `evidence/package.json:17-17` | `"@evidence-dev/core-components": "^5.4.0",` |
| ok | `imports` | `pandas` | `transform/models/nba/prep/nba_elo_rollforward.py:1-1` | `import pandas as pd` |
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::break_mult` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:297-435` | `def break_multi_way_tie(tied_teams: List[str],` |
| ok | `imports` | `pandas` | `transform/models/nfl/analysis/nfl_tiebreakers_optimized.py:1-1` | `import pandas as pd` |
| ok | `defines` | `sqlmesh/models/prep/nba_elo_rollforward.py::execute` | `sqlmesh/models/prep/nba_elo_rollforward.py:19-70` | `def execute(` |
| ok | `defines` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py::model` | `transform/models/nba/analysis/nba_tiebreakers_optimized.py:437-746` | `def model(dbt, sess):` |
| ok | `imports` | `typing` | `sqlmesh/models/prep/nba_elo_rollforward.py:1-1` | `import typing as t` |
| ok | `based_on` | `image:mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}` | `.devcontainer/Dockerfile.dev-container:2-2` | `FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}` |

# gpt-researcher

AI agent (Python) — https://github.com/assafelovic/gpt-researcher @ `3582a6841fe7dc801e2a34e34ee408641aea9bce`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 841 files = 494 covered + 0 partial + 347 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 5.5 s for 102,200 lines |
| Claims | fact 5149, hypothesis 13647; secrets redacted: 9 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for markdown: 140
- no analyzer for json: 56
- binary: 48
- no analyzer for *.svg: 39
- no analyzer for css: 12
- no analyzer for yaml: 9
- no analyzer for *.txt: 5
- too large: 4
- no analyzer for *.gitignore: 3
- no analyzer for *.jsonl: 3
- no analyzer for *.dockerignore: 2
- no analyzer for *.python-version: 2
- no analyzer for Procfile: 2
- no analyzer for CNAME: 2
- no analyzer for *.ipynb: 2
- no analyzer for *.cursorignore: 1
- no analyzer for *.cursorrules: 1
- no analyzer for *.example: 1
- no analyzer for LICENSE: 1
- no analyzer for *.cff: 1
- no analyzer for diff: 1
- no analyzer for *.mdx: 1
- no analyzer for *.nojekyll: 1
- no analyzer for *.gitkeep: 1
- no analyzer for html: 1
- excluded: sensitive (sensitive path): 1
- no analyzer for *.prettierrc: 1
- no analyzer for nginx: 1
- no analyzer for *.bootstrap: 1
- no analyzer for *.dompurify: 1
- no analyzer for *.fontawesome: 1
- no analyzer for *.showdown: 1
- no analyzer for toml: 1

Partly analysed:
- none

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `imports` | `os` | `gpt_researcher/retrievers/exa/exa.py:1-1` | `import os` |
| ok | `imports` | `langchain_openai` | `gpt_researcher/llm_provider/generic/base.py:282-282` | `from langchain_openai import ChatOpenAI` |
| ok | `imports` | `langchain_groq` | `gpt_researcher/llm_provider/generic/base.py:229-229` | `from langchain_groq import ChatGroq` |
| ok | `defines` | `evals/quality_eval/benchmark.py::_print_summary` | `evals/quality_eval/benchmark.py:367-407` | `def _print_summary(logs: list[dict]):` |
| ok | `imports` | `traceback` | `gpt_researcher/scraper/browser/nodriver_scraper.py:5-5` | `import traceback` |
| ok | `defines` | `frontend/nextjs/public/workbox-f1770938.js::A` | `frontend/nextjs/public/workbox-f1770938.js:1-1` | `define(["exports"],function(t){"use strict";try{self["workbox:core:7.0.0"]&&_()}catch(t){}` |
| ok | `imports` | `logging` | `tests/backend/test_websocket_disconnect_cleanup.py:3-3` | `import logging` |
| ok | `imports` | `@/types/data` | `frontend/nextjs/components/mobile/MobileChatPanel.tsx:3-3` | `import { Data, ChatData } from '@/types/data';` |
| ok | `requires` | `package:pypi/langchain-google-genai` | `pyproject.toml:194-194` | `"langchain-google-genai",` |
| ok | `defines` | `evals/context_filter/replay.py::replay_one` | `evals/context_filter/replay.py:115-153` | `async def replay_one(run: dict, strategy: str, out: Path) -> None:` |
| ok | `defines` | `frontend/nextjs/public/workbox-f1770938.js::A.getTimestamp` | `frontend/nextjs/public/workbox-f1770938.js:1-1` | `define(["exports"],function(t){"use strict";try{self["workbox:core:7.0.0"]&&_()}catch(t){}` |
| ok | `defines` | `multi_agents/agents/reviewer.py::ReviewerAgent.review_draft` | `multi_agents/agents/reviewer.py:15-66` | `async def review_draft(self, draft_state: dict):` |
| ok | `imports` | `react` | `frontend/nextjs/components/Settings/LayoutSelector.tsx:1-1` | `import React, { ChangeEvent } from 'react';` |
| ok | `imports` | `langchain_community.document_loaders` | `gpt_researcher/scraper/browser/processing/scrape_skills.py:1-1` | `from langchain_community.document_loaders import PyMuPDFLoader` |
| ok | `defines` | `evals/context_filter/collect.py::_recording` | `evals/context_filter/collect.py:29-36` | `async def _recording(self, query, pages):` |
| ok | `defines` | `gpt_researcher/utils/enum.py::ReportSource` | `gpt_researcher/utils/enum.py:30-51` | `class ReportSource(Enum):` |
| ok | `defines` | `tests/test_config_default_isolation.py::restore_defaults` | `tests/test_config_default_isolation.py:20-24` | `def restore_defaults():` |
| ok | `imports` | `gpt_researcher.llm_provider.generic.base` | `tests/test_nebius_provider.py:9-12` | `from gpt_researcher.llm_provider.generic.base import (     GenericLLMProvider,     _SUPPOR` |
| ok | `imports` | `backend.server.server_utils` | `tests/gptr-logs-handler.py:5-5` | `from backend.server.server_utils import CustomLogsHandler  # Update import` |
| ok | `imports` | `evals.quality_eval.metrics` | `tests/test_quality_metrics.py:17-25` | `from evals.quality_eval.metrics import (     citation_faithfulness,     source_diversity, ` |
| ok | `imports` | `langchain_openai` | `gpt_researcher/memory/embeddings.py:90-90` | `from langchain_openai import OpenAIEmbeddings` |
| ok | `defines` | `tests/test_quality_metrics.py::TestSourceDiversity` | `tests/test_quality_metrics.py:145-181` | `class TestSourceDiversity(unittest.TestCase):` |
| ok | `imports` | `@/components/research/ResearchContent` | `frontend/nextjs/app/research/[id]/page.tsx:13-13` | `import ResearchContent from "@/components/research/ResearchContent";` |
| ok | `requires` | `package:npm/react` | `frontend/nextjs/package.json:38-38` | `"react": "^18.0.0",` |
| ok | `imports` | `unittest.mock` | `tests/chat/test_chat_search_sources.py:5-5` | `from unittest.mock import AsyncMock, MagicMock` |
| ok | `defines` | `gpt_researcher/retrievers/bing/bing.py::BingSearch.get_api_key` | `gpt_researcher/retrievers/bing/bing.py:26-37` | `def get_api_key(self):` |
| ok | `imports` | `langchain_core.messages` | `gpt_researcher/utils/tools.py:113-113` | `from langchain_core.messages import ToolMessage` |
| ok | `defines` | `tests/skills/test_tavily_mcp_dedupe.py::MCPRetriever` | `tests/skills/test_tavily_mcp_dedupe.py:15-16` | `class MCPRetriever:  # name contains mcpretriever` |
| ok | `imports` | `langchain_community.chat_models.litellm` | `gpt_researcher/llm_provider/generic/base.py:271-271` | `from langchain_community.chat_models.litellm import ChatLiteLLM` |
| ok | `defines` | `tests/test_multi_agents_draft_revisions.py::test_disable_limit` | `tests/test_multi_agents_draft_revisions.py:31-35` | `def test_disable_limit():` |

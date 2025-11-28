"""
Analyst Node - Semantic change detection.

This node determines if a code change is "structural" (affects architecture)
or "cosmetic" (can be ignored).
"""

import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console

from umbra.agents.state import AnalysisResult, GraphState

console = Console()

ANALYST_SYSTEM_PROMPT = """You analyze code to determine if it should appear in an architecture diagram.

## YOUR GOAL:
Decide if this file is an IMPORTANT part of the system architecture.
We want to show the REAL structure - files that do meaningful work.

## ✅ IS STRUCTURAL (show in diagram):
- Main entry points (main.py, app.py, index.ts, server.js)
- Service files (auth_service.py, payment.py, user_service.js)
- API routes/controllers (routes.py, api.py, controllers/)
- Database operations (db.py, repository.py, models with queries)
- External API integrations (stripe.py, openai_client.py)
- Core business logic files
- Orchestration/workflow files
- Agent/AI files

## ❌ NOT STRUCTURAL (skip):
- __init__.py files
- Type definitions only (types.py, interfaces.ts)
- Pure config files (config.py, settings.py)
- Test files (*_test.py, *.spec.ts)
- Utility helpers (utils.py, helpers.js)
- Constants files
- CSS/styling files

## DECISION RULE:
"Does this file DO something important, or is it just supporting?"
If it DOES something → structural
If it just supports → cosmetic

## Response (JSON only, no markdown):
{
    "is_structural": true,
    "change_type": "service",
    "affected_components": ["auth.py", "UserService"],
    "reasoning": "Core authentication service"
}

change_type options:
- "new_service" - Main service/module file
- "api_call" - External API integration  
- "db_connection" - Database operations
- "api_route" - API endpoint definitions
- "orchestration" - Workflow/pipeline files
- "cosmetic" - Supporting files (DEFAULT if unsure)
"""


def analyst_node(state: GraphState) -> GraphState:
    """
    Analyze the code change and determine if it's structural.

    Input: file_path, file_content, diff
    Output: analysis_result
    """
    model = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    llm = ChatGoogleGenerativeAI(model=model, temperature=0)

    # Truncate content to save tokens
    content = state.get("file_content", "")
    if len(content) > 3000:
        content = content[:3000] + "\n... (truncated)"

    diff = state.get("diff") or "New file or full content"

    prompt = f"""## File: {state.get("file_path", "unknown")}

## Change:
{diff}

## Full File Content:
```python
{content}
```

Analyze this change and determine if it affects the system architecture.
"""

    try:
        response = llm.invoke(
            [
                SystemMessage(content=ANALYST_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        # Parse JSON response
        result = parse_json_response(response.content)

        analysis = AnalysisResult(
            is_structural_change=result.get("is_structural", False),
            change_type=result.get("change_type", "cosmetic"),
            affected_components=result.get("affected_components", []),
            reasoning=result.get("reasoning", ""),
        )

        console.print(
            f"[dim]   -> Analysis: {analysis.change_type} "
            f"({'structural' if analysis.is_structural_change else 'cosmetic'})[/dim]"
        )

        return {**state, "analysis_result": analysis}

    except Exception as e:
        console.print(f"[red]   -> Analyst error: {e}[/red]")
        # Return non-structural on error to be safe
        return {
            **state,
            "analysis_result": AnalysisResult(
                is_structural_change=False,
                change_type="cosmetic",
                affected_components=[],
                reasoning=f"Analysis failed: {e}",
            ),
        }


def parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, handling potential markdown fences."""
    # Remove markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.startswith("```")]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        import re

        match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from response: {content[:200]}")


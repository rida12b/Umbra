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

ANALYST_SYSTEM_PROMPT = """You analyze code to detect MAJOR architectural changes.

## YOUR GOAL:
Determine if a code change should appear on a HIGH-LEVEL architecture diagram.
Be VERY conservative - only TRUE architectural changes matter.

## ✅ IS STRUCTURAL (update diagram):
- Main entry point (main.py, app.py, index.ts, server.js)
- API server setup (FastAPI, Express, Flask, Django)
- Database connection (PostgreSQL, MongoDB, Redis, Prisma)
- External API client (Stripe, AWS, Firebase, OpenAI, Twilio)
- Message queue (Kafka, RabbitMQ, Celery)
- Authentication system (OAuth, JWT, Supabase Auth)

## ❌ NOT STRUCTURAL (skip):
- Helper functions, utilities, hooks
- Individual React/Vue components  
- Models, schemas, types, interfaces
- Configuration files
- Tests
- Styling, assets
- Individual routes (only the router setup matters)
- Internal refactoring

## DECISION RULE:
Ask yourself: "Would this appear on a whiteboard diagram explaining the system to a new dev?"
If NO → cosmetic
If YES → structural

## Response (JSON only, no markdown):
{
    "is_structural": true,
    "change_type": "db_connection",
    "affected_components": ["API", "PostgreSQL"],
    "reasoning": "Added database connection"
}

change_type options:
- "new_service" - Main app/server entry point
- "api_call" - External API integration  
- "db_connection" - Database setup
- "auth" - Authentication system
- "cosmetic" - Everything else (DEFAULT to this if unsure)
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


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

ANALYST_SYSTEM_PROMPT = """You are a Senior Software Architect analyzing code changes.

Your job is to determine if a code change affects the HIGH-LEVEL ARCHITECTURE of a system.

IMPORTANT: Be VERY selective. Only flag changes that represent MAJOR architectural components.

## Supported Languages: Python, JavaScript, TypeScript

## What IS structural (requires diagram update):
- Main service classes/modules (e.g., PaymentService, OrderService, authController)
- External API integrations (Stripe, AWS, Azure, Firebase, Supabase)
- Database connections (PostgreSQL, MongoDB, Redis, Prisma, TypeORM)
- Message queues (Kafka, RabbitMQ, Celery, BullMQ)
- API routes/endpoints (Express, FastAPI, Next.js API routes)

## What is NOT structural (SKIP these):
- Utility functions, helpers, hooks
- React components (unless main pages/layouts)
- Configuration files
- Test files (*.test.*, *.spec.*)
- Types, interfaces, models, schemas
- CSS, styles, assets
- Package.json, requirements.txt changes

## Keep it SIMPLE:
- Maximum 5-6 main services in a diagram
- Only show the MAIN components
- If in doubt, mark as "cosmetic"

## Response Format
Respond ONLY with valid JSON, no markdown code fences:
{
    "is_structural": true,
    "change_type": "api_call",
    "affected_components": ["PaymentService", "StripeAPI"],
    "reasoning": "Added Stripe integration"
}

Valid change_type values:
- "new_service" - Main service/controller/route handler
- "new_dependency" - External cloud service/API
- "api_call" - External API call
- "db_connection" - Database connection
- "inter_service" - Communication between services
- "refactor" - Internal refactoring (not structural)
- "cosmetic" - Everything else
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


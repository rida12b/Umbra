"""
Surgeon Node - Mermaid diagram updates.

This node surgically modifies the existing Mermaid diagram
based on the analysis results.
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console

from umbra.agents.state import GraphState

console = Console()

SURGEON_SYSTEM_PROMPT = """You create CLEAR, LAYERED architecture diagrams.

## GOAL: Show all files in a LEFT-TO-RIGHT flow with clear layers

## FORMAT - Use this EXACT structure:
```
graph LR
    subgraph Entry["🚀 Entry"]
        main[main.py]
    end
    
    subgraph Core["⚙️ Core"]
        orchestrator[orchestrator.py]
        analyst[analyst.py]
        surgeon[surgeon.py]
    end
    
    subgraph Services["📦 Services"]
        watcher[file_watcher.py]
        export[export.py]
    end
    
    subgraph External["🌐 External"]
        Gemini[Gemini]
        DB[(Database)]
    end
    
    Entry --> Core
    Core --> Services
    Services --> External
```

## LAYOUT RULES:

### 1. USE LAYERS (Left to Right)
- Layer 1 (LEFT): Entry points (main.py, app.py, index.ts)
- Layer 2: Core logic (orchestrators, services, controllers)
- Layer 3: Utilities (validators, helpers, exporters)
- Layer 4 (RIGHT): External services (APIs, databases)

### 2. SUBGRAPH NAMING
- Use emoji + name: `["🚀 Entry"]`, `["⚙️ Core"]`, `["📦 Services"]`
- Emojis: 🚀 Entry, ⚙️ Core/Logic, 📦 Services, 🔧 Utils, 🌐 External, 💾 Data

### 3. CONNECTIONS
- Connect LAYERS, not individual files when possible
- Entry --> Core --> Services --> External
- Only add specific file connections for important flows
- Avoid spaghetti: max 2 connections per file

### 4. FILES TO SHOW
- ALL .py/.js/.ts files (except __init__.py, tests)
- Group by folder: agents/, services/, utils/, etc.
- Use short names: `analyst[analyst.py]`

### 5. EXTERNAL SERVICES
- Databases: `DB[(PostgreSQL)]`
- APIs: `Gemini[Gemini]`, `Stripe[Stripe]`
- Always on the RIGHT side

### 6. FORBIDDEN
- NO comments (% or %%)
- NO crossing connections
- NO test files or __init__.py
- NO vertical spaghetti

## OUTPUT:
Return ONLY valid Mermaid starting with "graph LR"
No markdown, no explanation.
"""


def surgeon_node(state: GraphState) -> GraphState:
    """
    Update the Mermaid diagram based on the analysis.

    Input: current_mermaid, analysis_result, file_content
    Output: updated_mermaid
    """
    analysis = state.get("analysis_result")
    if not analysis or not analysis.is_structural_change:
        return state

    model = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    # Use slightly higher temperature for creativity
    llm = ChatGoogleGenerativeAI(model=model, temperature=0.2)

    # Truncate content to save tokens
    content = state.get("file_content", "")
    if len(content) > 2000:
        content = content[:2000] + "\n... (truncated)"

    prompt = f"""## Current Architecture Diagram:
{state.get("current_mermaid", "")}

## Change Detected:
- Type: {analysis.change_type}
- Affected Components: {', '.join(analysis.affected_components)}
- Reasoning: {analysis.reasoning}

## File: {state.get("file_path", "")}
```python
{content}
```

Update the diagram to reflect this change. Remember:
- Keep existing nodes and connections
- Add new nodes to appropriate subgraphs
- Add connections between related components
- Output ONLY the Mermaid diagram, starting with "graph TD"
"""

    try:
        response = llm.invoke(
            [
                SystemMessage(content=SURGEON_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        mermaid = clean_mermaid_output(response.content)

        console.print("[dim]   -> Diagram updated[/dim]")

        return {**state, "updated_mermaid": mermaid}

    except Exception as e:
        console.print(f"[red]   -> Surgeon error: {e}[/red]")
        return {**state, "updated_mermaid": None}


def clean_mermaid_output(raw: str) -> str:
    """Remove markdown code fences, comments, and clean up the output."""
    lines = raw.strip().split("\n")

    # Remove markdown fences and invalid comments
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip markdown fences
        if stripped.startswith("```"):
            continue
        # Skip single % comments (invalid in Mermaid, should be %%)
        if stripped.startswith("%") and not stripped.startswith("%%"):
            continue
        # Skip %% comments too for cleaner output
        if stripped.startswith("%%"):
            continue
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()

    # Ensure it starts with graph directive
    if not result.startswith(("graph ", "flowchart ")):
        # Try to find where the graph starts
        for i, line in enumerate(result.split("\n")):
            if line.strip().startswith(("graph ", "flowchart ")):
                result = "\n".join(result.split("\n")[i:])
                break

    return result


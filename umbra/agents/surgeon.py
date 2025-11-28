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

SURGEON_SYSTEM_PROMPT = """You are an expert at creating BEAUTIFUL, CLEAR architecture diagrams.

## YOUR GOAL:
Create a diagram that a developer can understand in 5 SECONDS.

## STRICT RULES:

### 1. SIMPLICITY
- Maximum 4-5 nodes total
- Only show THE MOST IMPORTANT components
- If you're unsure, DON'T add it

### 2. CLEAR STRUCTURE
Use this EXACT format:
```
graph TB
    subgraph Client["🖥️ Client"]
        UI[Web App]
    end
    
    subgraph Backend["⚙️ Backend"]
        API[API Server]
        Auth[Auth]
    end
    
    subgraph External["🌐 External"]
        DB[(Database)]
        Cloud[Cloud API]
    end
    
    UI --> API
    API --> Auth
    API --> DB
    API --> Cloud
```

### 3. NODE TYPES
- Services: `Name[Label]`
- Databases: `Name[(Label)]`
- Use EMOJIS in subgraph titles for visual clarity

### 4. NAMING
- Short labels: "API", "Auth", "DB", "AI"
- NO long names like "UserAuthenticationService"
- Use common abbreviations

### 5. CONNECTIONS
- Only show MAIN data flows
- Avoid crossing lines
- Max 5-6 connections total

### 6. FORBIDDEN
- NO comments (% or %%)
- NO helper classes
- NO utilities
- NO more than 5 nodes
- NO complex layouts

## OUTPUT:
Return ONLY the Mermaid diagram starting with "graph TB"
Nothing else.
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


"""
Summarizer - Generate a natural language summary of the project.
"""

import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rich.console import Console

console = Console()

SUMMARIZER_PROMPT = """You are explaining a codebase to a developer who just joined the team.

Be CONCISE and ACTIONABLE. They need to understand in 30 seconds.

## Output Format (Markdown):

### 🎯 What is this?
[ONE sentence: "This is a [type] that [does what]"]

### 🏗️ Architecture
| Layer | Technology |
|-------|------------|
| Frontend | React/Vue/None |
| Backend | FastAPI/Express/Django |
| Database | PostgreSQL/MongoDB/None |
| External | Stripe/AWS/None |

### 🚀 Quick Start
```bash
# How to run this project (be specific)
python main.py  # or npm start, etc.
```

### 📁 Key Files
| File | What it does |
|------|--------------|
| `main.py` | Entry point |
| `api/` | API routes |

### ⚠️ Important to Know
- [One critical thing a new dev MUST know]

## Rules:
- Be SPECIFIC, not generic
- Use tables for clarity
- Include actual commands
- Max 3 key files
- One "important to know" item only
"""


def generate_summary(
    project_path: str,
    mermaid_diagram: str,
    file_list: list[Path],
) -> str:
    """
    Generate a natural language summary of the project.
    
    Args:
        project_path: Path to the project root
        mermaid_diagram: Current architecture diagram
        file_list: List of Python files analyzed
        
    Returns:
        Markdown summary string
    """
    model = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    llm = ChatGoogleGenerativeAI(model=model, temperature=0.3)
    
    # Get project name from path
    project_name = Path(project_path).name
    
    # Create file list summary (only show important files)
    important_files = []
    for f in file_list[:20]:  # Limit to 20 files
        rel_path = f.relative_to(project_path) if project_path in str(f) else f
        important_files.append(str(rel_path))
    
    prompt = f"""## Project: {project_name}

## Architecture Diagram:
```mermaid
{mermaid_diagram}
```

## Files ({len(file_list)} total):
{chr(10).join(f'- {f}' for f in important_files)}
{"..." if len(file_list) > 20 else ""}

Based on this information, generate a project summary.
"""

    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARIZER_PROMPT),
            HumanMessage(content=prompt),
        ])
        
        return response.content.strip()
        
    except Exception as e:
        console.print(f"[red]Summary generation failed: {e}[/red]")
        return f"""**Type:** Unknown
**Stack:** Python
**Size:** {len(file_list)} files

### What it does
Unable to generate summary. Please check your API key.
"""


def generate_quick_summary(mermaid_diagram: str) -> str:
    """Generate a one-line summary from the diagram."""
    model = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    llm = ChatGoogleGenerativeAI(model=model, temperature=0)
    
    prompt = f"""Based on this architecture diagram, write a ONE sentence summary (max 100 chars):

{mermaid_diagram}

Example: "FastAPI backend with PostgreSQL and Stripe integration"
Just the sentence, nothing else."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip().strip('"')
    except Exception:
        return "Architecture diagram"


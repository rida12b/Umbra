"""
Ask Umbra - Chat with your codebase in natural language.
"""
import os
from pathlib import Path
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


CHAT_SYSTEM_PROMPT = """You are Umbra, an AI assistant that knows EVERYTHING about this codebase.

You have access to:
1. The project's architecture diagram
2. A summary of the project
3. The actual code files

## YOUR PERSONALITY:
- You are helpful, concise, and technical
- You speak like a senior developer colleague
- You give SPECIFIC answers with file paths and line references
- You don't waste words

## RESPONSE FORMAT:
- Be concise (max 3-4 paragraphs)
- Always reference specific files when relevant
- Use code blocks for code snippets
- If you don't know, say "I don't see that in the codebase"

## CONTEXT PROVIDED:
{context}

## CODEBASE FILES:
{files_content}
"""


def get_code_files(project_path: str, extensions: tuple = ('.py', '.js', '.ts', '.jsx', '.tsx')) -> dict:
    """Get all code files content from the project."""
    files_content = {}
    project = Path(project_path)
    
    # Directories to ignore
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 
                   '.env', 'dist', 'build', '.next', '.nuxt', 'coverage', '.pytest_cache'}
    
    for ext in extensions:
        for file_path in project.rglob(f'*{ext}'):
            # Skip ignored directories
            if any(ignored in file_path.parts for ignored in ignore_dirs):
                continue
            
            try:
                relative_path = file_path.relative_to(project)
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Limit file size to avoid token overflow
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... [truncated]"
                
                files_content[str(relative_path)] = content
            except Exception:
                continue
    
    return files_content


def format_files_for_context(files_content: dict, max_files: int = 20) -> str:
    """Format files content for LLM context."""
    if not files_content:
        return "No code files found."
    
    # Prioritize important files
    priority_patterns = ['main', 'app', 'index', 'server', 'api', 'route', 'config']
    
    def file_priority(filename: str) -> int:
        for i, pattern in enumerate(priority_patterns):
            if pattern in filename.lower():
                return i
        return len(priority_patterns)
    
    sorted_files = sorted(files_content.keys(), key=file_priority)[:max_files]
    
    formatted = []
    for filepath in sorted_files:
        content = files_content[filepath]
        formatted.append(f"### {filepath}\n```\n{content}\n```\n")
    
    return "\n".join(formatted)


def load_architecture_context(project_path: str) -> str:
    """Load existing architecture diagram and summary."""
    output_dir = Path(project_path) / "output"
    context_parts = []
    
    # Load architecture diagram
    arch_file = output_dir / "LIVE_ARCHITECTURE.md"
    if arch_file.exists():
        try:
            content = arch_file.read_text(encoding='utf-8')
            context_parts.append(f"## Architecture Diagram\n{content}")
        except Exception:
            pass
    
    return "\n\n".join(context_parts) if context_parts else "No architecture context available yet."


def ask_umbra(question: str, project_path: str = ".") -> str:
    """
    Ask a question about the codebase.
    
    Args:
        question: The question to ask
        project_path: Path to the project root
        
    Returns:
        AI-generated answer about the codebase
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "ERROR: GOOGLE_API_KEY not set."
    
    # Load context
    architecture_context = load_architecture_context(project_path)
    files_content = get_code_files(project_path)
    files_formatted = format_files_for_context(files_content)
    
    # Build the prompt
    system_prompt = CHAT_SYSTEM_PROMPT.format(
        context=architecture_context,
        files_content=files_formatted
    )
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-flash-latest",
        google_api_key=api_key,
        temperature=0.3
    )
    
    # Get response
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"Error: {str(e)}"


def interactive_chat(project_path: str = "."):
    """Start an interactive chat session."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    
    console = Console(force_terminal=True)
    
    console.print(Panel.fit(
        "[bold cyan]Ask Umbra[/bold cyan]\n"
        "Chat with your codebase. Type 'exit' to quit.",
        border_style="cyan"
    ))
    
    while True:
        try:
            question = console.input("\n[bold green]You:[/bold green] ")
            
            if question.lower() in ('exit', 'quit', 'q'):
                console.print("[dim]Goodbye![/dim]")
                break
            
            if not question.strip():
                continue
            
            console.print("\n[bold cyan]Umbra:[/bold cyan]")
            with console.status("[dim]Thinking...[/dim]"):
                answer = ask_umbra(question, project_path)
            
            console.print(Markdown(answer))
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break


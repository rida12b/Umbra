"""
Umbra - The Shadow Architect

Main entry point and CLI interface.
"""

import os
import signal
import sys
import time
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from umbra.agents.orchestrator import build_graph
from umbra.agents.state import INITIAL_DIAGRAM
from umbra.agents.writer import load_current_mermaid
from umbra.agents.tracker import get_tracker, ChangeType, TrackedChange
from umbra.watcher import FileChangeEvent, start_watching

# Load environment variables
load_dotenv()

console = Console(force_terminal=True)

# Global state for recent changes
recent_changes = []
MAX_RECENT_CHANGES = 50  # Increased for better timeline

# Store previous file contents for diff
file_cache = {}

# Global tracker instance
change_tracker = None


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Umbra - The Shadow Architect

    A living architecture diagram that updates in real-time.
    """
    pass


def do_initial_scan(path: str, output_file: str, graph, enable_docs: bool = True, enable_security: bool = True) -> str:
    """Scan all Python files and return the generated mermaid diagram.
    
    Args:
        path: Project root path
        output_file: Output file for LIVE_ARCHITECTURE.md
        graph: LangGraph workflow
        enable_docs: Generate module documentation
        enable_security: Run security scans
    """
    from datetime import datetime
    from umbra.agents.summarizer import generate_summary
    from umbra.agents.documentor import generate_module_doc, scan_security, generate_api_reference, generate_quick_context
    from umbra.agents.knowledge import generate_knowledge_file
    
    console.print(f"\n[cyan]Initial scan of project...[/cyan]")
    
    # Find all code files (Python + JS/TS)
    extensions = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]
    code_files = []
    for ext in extensions:
        code_files.extend(Path(path).rglob(ext))
    
    # Filter out venv, __pycache__, node_modules, etc.
    ignore_patterns = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".pytest_cache", "test", "tests", "dist", "build", ".next"}
    code_files = [
        f for f in code_files 
        if not any(p in f.parts for p in ignore_patterns)
    ]
    
    console.print(f"[dim]Found {len(code_files)} code files to analyze[/dim]")
    
    if not code_files:
        return INITIAL_DIAGRAM
    
    # Initialize diagram
    current_mermaid = INITIAL_DIAGRAM
    
    # Storage for documentation and security data
    module_docs = []
    security_data = []
    all_modules = {}  # file_path -> content for API ref generation
    total_lines = 0
    
    # Process each file
    global file_cache
    
    for i, file_path in enumerate(code_files, 1):
        console.print(f"[dim]({i}/{len(code_files)}) {file_path.name}[/dim]", end=" ")
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Cache file content for future diff comparisons (use absolute path)
            file_cache[str(file_path.resolve())] = content
            all_modules[str(file_path)] = content
            total_lines += len(content.splitlines())
            
            result = graph.invoke({
                "file_path": str(file_path),
                "file_content": content,
                "diff": f"Initial scan: {file_path.name}",
                "current_mermaid": current_mermaid,
                "retry_count": 0,
            })
            
            # Update current diagram if changed
            if result.get("updated_mermaid"):
                current_mermaid = result["updated_mermaid"]
                console.print("[green]OK[/green]")
            else:
                console.print("[dim]skip[/dim]")
                
        except Exception as e:
            console.print(f"[red]error[/red]")
    
    # Generate module documentation (if enabled)
    if enable_docs and len(code_files) <= 50:  # Limit for API cost
        console.print("\n[cyan]Generating module documentation...[/cyan]")
        for i, (fp, content) in enumerate(list(all_modules.items())[:20], 1):  # Max 20 modules
            console.print(f"[dim]({i}) {Path(fp).name}[/dim]", end=" ")
            doc = generate_module_doc(str(fp), content)
            if doc:
                module_docs.append(doc)
                console.print("[green]OK[/green]")
            else:
                console.print("[dim]skip[/dim]")
    
    # Security scan (if enabled)
    if enable_security:
        console.print("\n[cyan]Running security scan...[/cyan]")
        for i, (fp, content) in enumerate(list(all_modules.items())[:30], 1):  # Max 30 files
            console.print(f"[dim]({i}) {Path(fp).name}[/dim]", end=" ")
            result = scan_security(str(fp), content)
            if result:
                security_data.append(result)
                risk = result.get("risk_level", "none")
                if risk in ("high", "critical"):
                    console.print(f"[red]{risk.upper()}[/red]")
                elif risk == "medium":
                    console.print(f"[yellow]{risk}[/yellow]")
                else:
                    console.print("[green]clean[/green]")
            else:
                console.print("[dim]skip[/dim]")
    
    # Generate summary
    console.print("\n[cyan]Generating project summary...[/cyan]")
    summary = generate_summary(path, current_mermaid, code_files)
    
    # Generate quick context for LLMs
    console.print("[cyan]Generating quick context...[/cyan]")
    quick_context = generate_quick_context(summary, [str(f) for f in code_files])
    
    # Generate API reference
    console.print("[cyan]Generating API reference...[/cyan]")
    api_reference = generate_api_reference(all_modules)
    
    # Write initial diagram with summary
    final_content = f"""# Live Architecture

> **Auto-generated by Umbra** - Do not edit manually
> Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> Scanned: {len(code_files)} files

## Project Summary

{summary}

## System Overview

```mermaid
{current_mermaid}
```

## Recent Changes

| Time | File | Change |
|------|------|--------|
| {datetime.now().strftime("%H:%M")} | initial | Full project scan |
"""
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(final_content, encoding="utf-8")
    
    # Generate UMBRA_KNOWLEDGE.md (comprehensive knowledge base)
    knowledge_path = str(Path(output_file).parent / "UMBRA_KNOWLEDGE.md")
    console.print("\n[cyan]Generating knowledge base...[/cyan]")
    
    # Get metrics from insights
    try:
        from umbra.agents.insights import run_full_analysis
        analysis = run_full_analysis(path)
        metrics = {
            "total_files": len(code_files),
            "total_lines": total_lines,
            "entry_points": len(analysis.get("entry_points", [])),
            "external_apis": len(analysis.get("external_apis", [])),
        }
    except Exception:
        metrics = {
            "total_files": len(code_files),
            "total_lines": total_lines,
            "entry_points": 0,
            "external_apis": 0,
        }
    
    generate_knowledge_file(
        output_path=knowledge_path,
        mermaid=current_mermaid,
        quick_context=quick_context,
        module_docs="\n\n".join(module_docs) if module_docs else "",
        api_reference=api_reference,
        security_data=security_data,
        metrics=metrics,
        recent_changes=[{
            "timestamp": datetime.now(),
            "file_path": "initial",
            "change_type": "scan",
            "description": f"Full project scan - {len(code_files)} files analyzed",
        }],
        file_list=[str(f) for f in code_files],
        root_path=path,
    )
    
    console.print(f"[green]Initial scan complete![/green]")
    console.print(f"[dim]  -> Architecture: {output_file}[/dim]")
    console.print(f"[dim]  -> Knowledge base: {knowledge_path}[/dim]\n")
    
    return current_mermaid


def start_chat_server_background(project_path: str, port: int = 8765):
    """Start the chat server in a background thread."""
    from umbra.server import UmbraRequestHandler
    from http.server import HTTPServer
    
    UmbraRequestHandler.project_path = project_path
    UmbraRequestHandler.project_data = None
    
    server = HTTPServer(('localhost', port), UmbraRequestHandler)
    
    def serve():
        try:
            server.serve_forever()
        except Exception:
            pass
    
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return server


def regenerate_dashboard(path: str, output_file: str, dashboard_file: str):
    """Regenerate the HTML dashboard and update knowledge base."""
    global recent_changes
    
    from umbra.export import export_html
    from umbra.agents.insights import run_full_analysis
    from umbra.agents.knowledge import load_existing_knowledge, generate_knowledge_file
    from umbra.agents.writer import load_current_mermaid
    from umbra.agents.health import run_health_check
    
    try:
        # Get analysis data
        analysis = run_full_analysis(path)
        
        # Run health check
        try:
            health_report = run_health_check(path)
            analysis['health'] = health_report.to_dict()
        except Exception:
            analysis['health'] = None
        
        # Add recent changes to analysis
        analysis['recent_changes'] = recent_changes
        
        # Export dashboard
        project_name = Path(path).absolute().name
        export_html(output_file, dashboard_file, project_name, analysis)
        
        # Update knowledge base with recent changes
        knowledge_path = str(Path(output_file).parent / "UMBRA_KNOWLEDGE.md")
        existing = load_existing_knowledge(knowledge_path)
        
        # Get current mermaid diagram
        current_mermaid = load_current_mermaid(output_file)
        
        # Get file list
        extensions = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]
        code_files = []
        for ext in extensions:
            code_files.extend(Path(path).rglob(ext))
        ignore_patterns = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".pytest_cache", "test", "tests", "dist", "build", ".next"}
        code_files = [f for f in code_files if not any(p in f.parts for p in ignore_patterns)]
        
        # Update knowledge file
        generate_knowledge_file(
            output_path=knowledge_path,
            mermaid=current_mermaid,
            quick_context=existing.get("quick_context", ""),
            module_docs=existing.get("module_docs", ""),
            api_reference=existing.get("api_reference", ""),
            security_data=[],  # Don't re-run security on incremental update
            metrics={
                "total_files": len(code_files),
                "total_lines": analysis.get("total_lines", 0),
                "entry_points": len(analysis.get("entry_points", [])),
                "external_apis": len(analysis.get("external_apis", [])),
            },
            recent_changes=[{
                "timestamp": c.get("time", ""),
                "file_path": c.get("file", ""),
                "change_type": c.get("type", "modified"),
                "description": c.get("description", ""),
            } for c in recent_changes],
            file_list=[str(f) for f in code_files],
            root_path=path,
        )
        
    except Exception as e:
        console.print(f"[dim]Dashboard update failed: {e}[/dim]")


def add_recent_change(
    file_path: str, 
    change_type: str = "modified", 
    description: str = "",
    diff_lines: list = None,
    stats: dict = None,
    impact: list = None,
    warnings: list = None,
    intent: str = None,
):
    """Track a recent change with AI-generated description, diff details, and impact analysis."""
    global recent_changes
    
    recent_changes.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "file": Path(file_path).name if "/" in file_path or "\\" in file_path else file_path,
        "type": change_type,
        "description": description,
        "diff_lines": diff_lines or [],  # List of {"line": str, "type": "add"|"remove"|"context"}
        "stats": stats or {"added": 0, "removed": 0},  # Line counts
        "impact": impact or [],  # List of {"file": str, "type": str, "desc": str}
        "warnings": warnings or [],  # List of warning strings
        "intent": intent,  # "feature" | "bugfix" | "refactor" | etc.
    })
    
    # Keep only last N changes
    recent_changes = recent_changes[:MAX_RECENT_CHANGES]


def compute_diff(old_content: str, new_content: str) -> dict:
    """Compute a detailed diff between old and new content.
    
    Returns:
        dict with:
            - text: str - Human readable diff summary
            - lines: list - List of {"line": str, "type": "add"|"remove"|"context"}
            - stats: dict - {"added": int, "removed": int}
    """
    import difflib
    
    old_lines = old_content.splitlines() if old_content else []
    new_lines = new_content.splitlines() if new_content else []
    
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=2))
    
    diff_lines = []
    added_count = 0
    removed_count = 0
    
    for line in diff[2:]:  # Skip the header lines
        if line.startswith('+') and not line.startswith('+++'):
            diff_lines.append({"line": line[1:], "type": "add"})
            added_count += 1
        elif line.startswith('-') and not line.startswith('---'):
            diff_lines.append({"line": line[1:], "type": "remove"})
            removed_count += 1
        elif line.startswith(' '):
            diff_lines.append({"line": line[1:], "type": "context"})
        elif line.startswith('@@'):
            diff_lines.append({"line": line, "type": "header"})
    
    # Keep only most important lines (max 20)
    diff_lines = diff_lines[:20]
    
    # Build text summary for LLM
    text_parts = []
    added_text = [d["line"] for d in diff_lines if d["type"] == "add"][:10]
    removed_text = [d["line"] for d in diff_lines if d["type"] == "remove"][:10]
    
    if added_text:
        text_parts.append(f"ADDED:\n" + "\n".join(added_text))
    if removed_text:
        text_parts.append(f"REMOVED:\n" + "\n".join(removed_text))
    
    return {
        "text": "\n\n".join(text_parts) if text_parts else "Minor changes",
        "lines": diff_lines,
        "stats": {"added": added_count, "removed": removed_count}
    }


def generate_change_description(file_name: str, content: str, change_type: str, diff_text: str = "") -> str:
    """Generate a short AI description of what ACTUALLY changed."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    import os
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return f"File {change_type}"
        
        # If we have a diff, use it - otherwise use content preview
        if diff_text and diff_text != "Minor changes":
            context = diff_text[:1000]
            prompt_type = "DIFF"
        else:
            context = content[:600] if content else ""
            prompt_type = "FULL"
        
        if not context.strip():
            return f"New empty file created"
        
        llm = ChatGoogleGenerativeAI(
            model="models/gemini-flash-latest",
            google_api_key=api_key,
            temperature=0.1,
            max_tokens=100
        )
        
        if prompt_type == "DIFF":
            prompt = f"""Describe EXACTLY what changed in this code diff. Be specific about the actual change.

File: {file_name}
Change type: {change_type}

{context}

Describe the change in 8-15 words. Focus on WHAT was added/removed/modified.
Examples:
- "Added print('test') debug statement"
- "Removed unused import statement" 
- "Changed timeout from 5s to 10s"
- "Added new validate_user() function"
- "Fixed typo in error message"

Your description:"""
        else:
            prompt = f"""This is a NEW file. Describe what it does in 8-15 words.

File: {file_name}

```
{context}
```

Describe what this file does:"""

        response = llm.invoke([HumanMessage(content=prompt)])
        
        desc = response.content.strip().strip('"').strip("'").strip()
        
        # Clean up
        desc = desc.replace('\n', ' ').replace('  ', ' ')
        
        if len(desc) > 80:
            desc = desc[:77] + "..."
        
        return desc if desc else f"Updated {file_name}"
        print("test ")
    except Exception as e:
        # Fallback: show what was added/removed
        if diff_text and "ADDED:" in diff_text:
            lines = diff_text.split("ADDED:")[1].split("\n")[:2]
            preview = lines[0][:50] if lines else ""
            if preview:
                return f"Added: {preview}..."
        return f"Modified {file_name}"


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file path (default: ./output/LIVE_ARCHITECTURE.md)",
)
@click.option(
    "--debounce",
    "-d",
    default=2.0,
    type=float,
    help="Debounce delay in seconds (default: 2.0)",
)
@click.option(
    "--no-scan",
    is_flag=True,
    help="Skip initial project scan",
)
@click.option(
    "--dashboard/--no-dashboard",
    default=True,
    help="Auto-generate dashboard (default: enabled)",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Open dashboard in browser",
)
@click.option(
    "--port",
    "-p",
    default=8765,
    type=int,
    help="Chat server port (default: 8765)",
)
@click.option(
    "--docs/--no-docs",
    default=True,
    help="Generate module documentation (default: enabled)",
)
@click.option(
    "--security/--no-security",
    default=True,
    help="Run security scan (default: enabled)",
)
def watch(path: str, verbose: bool, output: str | None, debounce: float, no_scan: bool, dashboard: bool, open_browser: bool, port: int, docs: bool, security: bool):
    """Watch a directory for Python file changes.
    
    This command does everything:
    - Scans your project (with docs + security)
    - Generates architecture diagram
    - Creates UMBRA_KNOWLEDGE.md (full project brain)
    - Starts the chat server
    - Auto-updates dashboard on changes
    - Tracks ALL changes with impact analysis
    """
    global recent_changes, change_tracker
    recent_changes = []
    
    # Initialize the change tracker
    change_tracker = get_tracker(path)
    
    # Set output path in environment if provided
    if output:
        os.environ["OUTPUT_FILE"] = output

    output_file = os.getenv("OUTPUT_FILE", "./output/LIVE_ARCHITECTURE.md")
    dashboard_file = str(Path(output_file).parent / "dashboard.html")

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print(
            "[red]ERROR: GOOGLE_API_KEY not set. Please set it in .env or environment.[/red]"
        )
        sys.exit(1)

    # Start chat server in background
    chat_server = None
    if dashboard:
        try:
            chat_server = start_chat_server_background(path, port)
            console.print(f"[green]OK[/green] Chat server started on port {port}")
        except Exception as e:
            console.print(f"[yellow]WARN: Could not start chat server: {e}[/yellow]")

    # Display startup banner
    knowledge_file = str(Path(output_file).parent / "UMBRA_KNOWLEDGE.md")
    console.print(
        Panel.fit(
            "[bold cyan]UMBRA[/bold cyan] - The Shadow Architect\n\n"
            f"[>] Project: [green]{Path(path).absolute()}[/green]\n"
            f"[>] Output: [yellow]{output_file}[/yellow]\n"
            f"[>] Knowledge: [magenta]{knowledge_file}[/magenta]\n"
            f"[>] Dashboard: [blue]{dashboard_file}[/blue]\n"
            f"[>] Chat: [magenta]http://localhost:{port}[/magenta]\n"
            f"[>] Docs: {'[green]ON[/green]' if docs else '[dim]OFF[/dim]'} | Security: {'[green]ON[/green]' if security else '[dim]OFF[/dim]'}\n"
            f"[>] Model: [dim]{os.getenv('GEMINI_MODEL', 'models/gemini-flash-latest')}[/dim]",
            border_style="cyan",
        )
    )

    # Build the graph
    graph = build_graph()
    
    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Pre-fill file cache for diff tracking
    def prefill_cache():
        """Load all code files into cache for diff comparison and tracker."""
        global file_cache, change_tracker
        extensions = ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]
        ignore_patterns = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".pytest_cache", "test", "tests", "dist", "build", ".next", "output"}
        
        for ext in extensions:
            for file_path in Path(path).rglob(ext):
                if not any(p in file_path.parts for p in ignore_patterns):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        # Use absolute path as key for consistency
                        abs_path = str(file_path.resolve())
                        file_cache[abs_path] = content
                    except Exception:
                        pass
        
        # Initialize change tracker with existing files
        if change_tracker:
            change_tracker.initialize(file_cache)
        
        console.print(f"[dim]Cached {len(file_cache)} files for diff tracking[/dim]")
    
    # Initial scan (unless --no-scan)
    if not no_scan:
        do_initial_scan(path, output_file, graph, enable_docs=docs, enable_security=security)
        add_recent_change("initial", "Full project scan", "Analyzed full project structure")
    else:
        # Even with --no-scan, we need to cache files for diff tracking
        prefill_cache()
    
    if not Path(output_file).exists():
        # Create empty diagram if file doesn't exist
        console.print("[dim]Creating initial architecture file...[/dim]")
        Path(output_file).write_text(
            f"""# Live Architecture

> **Auto-generated by Umbra** - Do not edit manually
> Last updated: Starting...

## System Overview

```mermaid
{INITIAL_DIAGRAM}
```

## Recent Changes

| Time | File | Change |
|------|------|--------|
""",
            encoding="utf-8",
        )

    # Generate initial dashboard
    if dashboard:
        console.print("[dim]Generating dashboard...[/dim]")
        regenerate_dashboard(path, output_file, dashboard_file)
        console.print(f"[green]OK[/green] Dashboard ready: {dashboard_file}")
        
        if open_browser:
            webbrowser.open(f"file://{Path(dashboard_file).absolute()}")

    def remove_file_from_diagram(file_name: str, output_path: str):
        """Remove a deleted file from the Mermaid diagram."""
        try:
            content = Path(output_path).read_text(encoding="utf-8")
            
            # Extract mermaid diagram
            if "```mermaid" not in content:
                return
            
            start = content.index("```mermaid") + len("```mermaid")
            end = content.index("```", start)
            mermaid = content[start:end]
            
            # Remove lines containing the file name
            lines = mermaid.split('\n')
            new_lines = []
            for line in lines:
                # Skip lines that reference this file
                if file_name.lower() in line.lower():
                    continue
                new_lines.append(line)
            
            new_mermaid = '\n'.join(new_lines)
            
            # Rebuild content
            new_content = content[:start] + new_mermaid + content[end:]
            Path(output_path).write_text(new_content, encoding="utf-8")
            
        except Exception as e:
            console.print(f"[dim]   Could not update diagram: {e}[/dim]")

    def process_change(event: FileChangeEvent):
        """Process a file change event through the graph (sync wrapper)."""
        file_name = event.file_path.name
        event_type = event.event_type  # "created", "modified", or "deleted"
        
        # Display change with appropriate emoji
        symbol = {"created": "[green]+[/green]", "modified": "[yellow]*[/yellow]", "deleted": "[red]-[/red]"}.get(event_type, "[dim]?[/dim]")
        console.print(f"\n[bold]>> {symbol} {event_type.upper()}:[/bold] {file_name}")

        try:
            # Handle file deletion
            if event_type == "deleted" or not event.file_path.exists():
                console.print(f"[yellow]   Removing from architecture...[/yellow]")
                
                file_key = str(event.file_path.resolve())
                old_content = file_cache.get(file_key, "")
                
                # Track deletion with impact analysis
                if change_tracker:
                    tracked = change_tracker.track_change(
                        file_path=file_key,
                        change_type=ChangeType.DELETED,
                        old_content=old_content,
                        new_content=None,
                        diff_lines=[],
                        stats={"added": 0, "removed": len(old_content.splitlines()) if old_content else 0},
                    )
                    
                    # Show impact (CRITICAL for deletions)
                    if tracked.impacted_files:
                        console.print(f"[red]   BREAKING: {len(tracked.impacted_files)} file(s) import this![/red]")
                        for impact in tracked.impacted_files:
                            console.print(f"[red]     - {Path(impact.file_path).name}: {impact.description}[/red]")
                    
                    for warning in tracked.warnings:
                        console.print(f"[red]   WARNING: {warning}[/red]")
                
                # Remove from diagram
                remove_file_from_diagram(file_name, output_file)
                console.print(f"[dim]   -> Removed from diagram[/dim]")
                
                # Remove from cache
                if file_key in file_cache:
                    del file_cache[file_key]
                
                # Track the deletion
                add_recent_change(file_name, "deleted", f"Removed {file_name} from project")
                
                # Regenerate dashboard
                if dashboard:
                    regenerate_dashboard(path, output_file, dashboard_file)
                    console.print(f"[dim]   Dashboard updated[/dim]")
                return

            # Read file content (try multiple encodings)
            try:
                content = event.file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = event.file_path.read_text(encoding="utf-16")
                except UnicodeDecodeError:
                    content = event.file_path.read_text(encoding="latin-1")
            
            # Get previous content from cache for diff (use absolute path)
            file_key = str(event.file_path.resolve())
            old_content = file_cache.get(file_key, "")
            
            # Compute detailed diff
            if old_content:
                diff_data = compute_diff(old_content, content)
                diff_text = diff_data["text"]
                diff_lines = diff_data["lines"]
                diff_stats = diff_data["stats"]
                console.print(f"[dim]   Diff: +{diff_stats['added']} -{diff_stats['removed']} lines[/dim]")
            else:
                diff_text = ""
                diff_lines = []
                diff_stats = {"added": 0, "removed": 0}
                console.print(f"[yellow]   WARN: No cache for this file[/yellow]")
            
            # Update cache with new content
            file_cache[file_key] = content

            # Load current architecture
            current_mermaid = load_current_mermaid(output_file)

            # Invoke the graph synchronously
            result = graph.invoke(
                {
                    "file_path": str(event.file_path),
                    "file_content": content,
                    "diff": event.diff,
                    "current_mermaid": current_mermaid,
                    "retry_count": 0,
                }
            )

            # Generate AI description based on actual diff
            if diff_text and diff_text != "Minor changes":
                console.print(f"[dim]   Diff preview: {diff_text[:100]}...[/dim]")
            description = generate_change_description(file_name, content, event_type, diff_text)
            console.print(f"[cyan]   => {description}[/cyan]")
            
            # Track the change with the new tracker (includes impact analysis)
            if change_tracker:
                ct = {"created": ChangeType.CREATED, "modified": ChangeType.MODIFIED, "deleted": ChangeType.DELETED}
                tracked = change_tracker.track_change(
                    file_path=file_key,
                    change_type=ct.get(event_type, ChangeType.MODIFIED),
                    old_content=old_content,
                    new_content=content,
                    diff_lines=diff_lines,
                    stats=diff_stats,
                )
                
                # Show impact analysis
                if tracked.impacted_files:
                    console.print(f"[yellow]   Impact: {len(tracked.impacted_files)} file(s) affected[/yellow]")
                    for impact in tracked.impacted_files[:3]:
                        console.print(f"[dim]     - {Path(impact.file_path).name}: {impact.description}[/dim]")
                
                # Show warnings
                for warning in tracked.warnings:
                    console.print(f"[red]   WARNING: {warning}[/red]")
                
                # Use tracker's description if better
                description = tracked.description
                
                # Prepare impact data for dashboard
                impact_data = [
                    {"file": Path(i.file_path).name, "type": i.impact_type, "desc": i.description}
                    for i in tracked.impacted_files
                ]
            else:
                impact_data = []
                tracked = None
            
            # Track the change with description, diff lines, AND impact (for dashboard)
            add_recent_change(
                file_name, 
                event_type, 
                description,
                diff_lines=diff_lines,
                stats=diff_stats,
                impact=impact_data,
                warnings=tracked.warnings if tracked else [],
                intent=tracked.intent.value if tracked else None,
            )

            if verbose:
                if result.get("analysis_result"):
                    ar = result["analysis_result"]
                    console.print(f"[dim]   Analysis: {ar.reasoning}[/dim]")

            # Regenerate dashboard
            if dashboard:
                regenerate_dashboard(path, output_file, dashboard_file)
                console.print(f"[dim]   Dashboard updated[/dim]")

        except Exception as e:
            console.print(f"[red]   ERROR: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()

    def on_file_change(event: FileChangeEvent):
        """Callback for file changes."""
        process_change(event)

    # Setup graceful shutdown
    watcher = None

    def signal_handler(sig, frame):
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
        if watcher:
            watcher.stop()
        if chat_server:
            chat_server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start watching
    console.print("\n[dim]Watching for changes... (CTRL+C to stop)[/dim]")
    console.print(f"[dim]Open dashboard: [blue]file://{Path(dashboard_file).absolute()}[/blue][/dim]\n")

    watcher = start_watching(
        path=path,
        callback=on_file_change,
        debounce_seconds=debounce,
    )

    # Keep alive
    try:
        while watcher.is_running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if watcher:
            watcher.stop()
        if chat_server:
            chat_server.shutdown()


@cli.command()
@click.option(
    "--output",
    "-o",
    default="./output/LIVE_ARCHITECTURE.md",
    help="Output file path",
)
def init(output: str):
    """Initialize a new architecture diagram."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            console.print("[yellow]Aborted.[/yellow]")
            return

    output_path.write_text(
        f"""# Live Architecture

> **Auto-generated by Umbra** - Do not edit manually
> Last updated: Initialized

## System Overview

```mermaid
{INITIAL_DIAGRAM}
```

## Recent Changes

| Time | File | Change |
|------|------|--------|
""",
        encoding="utf-8",
    )

    console.print(f"[green]OK: Created {output}[/green]")
    console.print("\nNext steps:")
    console.print(f"  1. Open {output} in VS Code with Mermaid preview")
    console.print("  2. Run: [cyan]umbra watch .[/cyan]")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default="./output/LIVE_ARCHITECTURE.md",
    help="Output file path",
)
@click.option(
    "--docs/--no-docs",
    default=True,
    help="Generate module documentation (default: enabled)",
)
@click.option(
    "--security/--no-security",
    default=True,
    help="Run security scan (default: enabled)",
)
def scan(path: str, output: str, docs: bool, security: bool):
    """Scan an existing project and generate architecture diagram.
    
    This generates:
    - LIVE_ARCHITECTURE.md (diagram + summary)
    - UMBRA_KNOWLEDGE.md (full project brain for LLMs)
    """
    from umbra.agents.orchestrator import build_graph
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print(
            "[red]ERROR: GOOGLE_API_KEY not set. Please set it in .env or environment.[/red]"
        )
        sys.exit(1)
    
    console.print(
        Panel.fit(
            "[bold cyan]UMBRA[/bold cyan] - Project Scanner\n\n"
            f"[>] Project: [green]{Path(path).absolute()}[/green]\n"
            f"[>] Output: [yellow]{output}[/yellow]\n"
            f"[>] Docs: {'[green]ON[/green]' if docs else '[dim]OFF[/dim]'} | Security: {'[green]ON[/green]' if security else '[dim]OFF[/dim]'}",
            border_style="cyan",
        )
    )
    
    # Build graph and run initial scan (which generates everything)
    graph = build_graph()
    do_initial_scan(path, output, graph, enable_docs=docs, enable_security=security)
    
    console.print(f"\n[green]Scan complete![/green]")


@cli.command()
@click.argument("output_file", type=click.Path())
@click.option(
    "--input", "-i",
    default="./output/LIVE_ARCHITECTURE.md",
    help="Input markdown file",
)
@click.option(
    "--name", "-n",
    default=None,
    help="Project name",
)
def export(output_file: str, input: str, name: str | None):
    """Export architecture to HTML file."""
    from umbra.export import export_html
    
    # Determine project name
    if name is None:
        name = Path.cwd().name
    
    try:
        export_html(input, output_file, name)
        console.print(f"[green]OK: Exported to {output_file}[/green]")
        console.print(f"[dim]Open in browser to view interactive diagram[/dim]")
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        console.print("[dim]Run 'umbra scan' or 'umbra watch' first to generate architecture[/dim]")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file: str):
    """Validate a Mermaid diagram file."""
    from umbra.validators.mermaid import validate_mermaid

    content = Path(file).read_text(encoding="utf-8")

    # Extract mermaid if in markdown
    if "```mermaid" in content:
        start = content.index("```mermaid") + len("```mermaid")
        end = content.index("```", start)
        mermaid = content[start:end].strip()
    else:
        mermaid = content

    result = validate_mermaid(mermaid)

    if result.is_valid:
        console.print("[green]OK: Diagram is valid[/green]")
    else:
        console.print("[red]ERROR: Diagram has errors:[/red]")
        for error in result.errors:
            console.print(f"   - {error}")

    if result.warnings:
        console.print("[yellow]WARNINGS:[/yellow]")
        for warning in result.warnings:
            console.print(f"   - {warning}")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--question", "-q", default=None, help="Ask a single question (non-interactive)")
def ask(path: str, question: str | None):
    """Chat with your codebase using AI.
    
    Ask questions about your code in natural language.
    
    Examples:
        umbra ask                    # Start interactive chat
        umbra ask -q "How does auth work?"  # Single question
    """
    from umbra.agents.chat import ask_umbra, interactive_chat
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print(
            "[red]ERROR: GOOGLE_API_KEY not set. Please set it in .env or environment.[/red]"
        )
        sys.exit(1)
    
    if question:
        # Single question mode
        console.print(f"[dim]Analyzing codebase...[/dim]")
        answer = ask_umbra(question, path)
        from rich.markdown import Markdown
        console.print("\n")
        console.print(Markdown(answer))
    else:
        # Interactive mode
        interactive_chat(path)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def insights(path: str, output_json: bool):
    """Analyze codebase and show architecture insights.
    
    Detects potential issues like:
    - God files (too large)
    - High coupling
    - Missing __init__.py
    - Deep nesting
    """
    from umbra.agents.insights import run_full_analysis, InsightSeverity
    
    console.print(f"[cyan]Analyzing {Path(path).absolute()}...[/cyan]\n")
    
    analysis = run_full_analysis(path)
    
    if output_json:
        import json
        # Convert insights to dicts
        data = {
            'health': analysis['health'],
            'metrics': analysis['metrics'],
            'insights': [
                {
                    'title': i.title,
                    'description': i.description,
                    'severity': i.severity.value,
                    'affected_files': i.affected_files,
                    'recommendation': i.recommendation
                }
                for i in analysis['insights']
            ]
        }
        console.print(json.dumps(data, indent=2))
        return
    
    # Health Score
    health = analysis['health']
    metrics = analysis['metrics']
    
    score_color = {
        'A': 'green', 'B': 'green', 'C': 'yellow', 'D': 'red', 'F': 'red'
    }.get(health['grade'], 'white')
    
    console.print(Panel.fit(
        f"[bold {score_color}]{health['grade']}[/bold {score_color}] "
        f"[{score_color}]{health['score']}/100[/{score_color}]\n"
        f"[dim]{health['status']}[/dim]",
        title="Health Score",
        border_style=score_color
    ))
    
    # Metrics
    console.print("\n[bold]Metrics[/bold]")
    console.print(f"  Files: {metrics['total_files']}")
    console.print(f"  Lines: {metrics['total_lines']:,}")
    console.print(f"  Avg lines/file: {metrics['total_lines'] // max(metrics['total_files'], 1)}")
    
    # Insights
    console.print("\n[bold]Insights[/bold]")
    
    if not analysis['insights']:
        console.print("  [green]No issues detected![/green]")
    else:
        for insight in analysis['insights']:
            severity_icon = {
                InsightSeverity.CRITICAL: "[red]",
                InsightSeverity.WARNING: "[yellow]",
                InsightSeverity.INFO: "[blue]"
            }.get(insight.severity, "[white]")
            
            severity_close = severity_icon.replace("[", "[/")
            console.print(f"  {severity_icon}{insight.title}{severity_close}")
            console.print(f"    [dim]{insight.recommendation}[/dim]")
    
    # Largest files
    if metrics['largest_files']:
        console.print("\n[bold]Largest Files[/bold]")
        for filepath, lines in metrics['largest_files'][:5]:
            console.print(f"  {filepath}: {lines} lines")


@cli.command()
@click.argument("output_file", type=click.Path())
@click.option(
    "--input", "-i",
    default="./output/LIVE_ARCHITECTURE.md",
    help="Input markdown file",
)
@click.option(
    "--name", "-n",
    default=None,
    help="Project name",
)
@click.option(
    "--path", "-p",
    default=".",
    help="Project path for insights analysis",
)
def dashboard(output_file: str, input: str, name: str | None, path: str):
    """Export beautiful interactive HTML dashboard.
    
    Includes:
    - Architecture diagram
    - Health score
    - Code metrics
    - Insights and recommendations
    """
    from umbra.export import export_html
    from umbra.agents.insights import run_full_analysis
    
    # Determine project name
    if name is None:
        name = Path.cwd().name
    
    console.print(f"[cyan]Generating dashboard for {name}...[/cyan]")
    
    # Run insights analysis
    console.print("[dim]Analyzing codebase...[/dim]")
    analysis = run_full_analysis(path)
    
    try:
        export_html(input, output_file, name, analysis)
        console.print(f"\n[green]Dashboard exported to {output_file}[/green]")
        console.print(f"[dim]Open in browser: file://{Path(output_file).absolute()}[/dim]")
    except FileNotFoundError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        console.print("[dim]Run 'umbra scan' first to generate architecture[/dim]")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8765, help="Server port (default: 8765)")
def serve(path: str, port: int):
    """Start the Umbra API server for dashboard chat.
    
    This enables the chat functionality in the HTML dashboard.
    Run this command, then open the dashboard in your browser.
    """
    from umbra.server import start_server
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print(
            "[red]ERROR: GOOGLE_API_KEY not set. Please set it in .env or environment.[/red]"
        )
        sys.exit(1)
    
    console.print(Panel.fit(
        "[bold cyan]UMBRA[/bold cyan] - Chat Server\n"
        f"Project: [green]{Path(path).absolute()}[/green]\n"
        f"API: [yellow]http://localhost:{port}[/yellow]\n\n"
        "[dim]Open the dashboard HTML to chat with your codebase![/dim]",
        border_style="cyan"
    ))
    
    start_server(path, port)


if __name__ == "__main__":
    cli()

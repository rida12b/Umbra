"""
Umbra Server - Local API for dashboard chat functionality.
"""
import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

load_dotenv()


class UmbraRequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests for the Umbra chat API."""
    
    project_path = "."
    project_data = None
    
    def send_cors_headers(self):
        """Send CORS headers for cross-origin requests."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            
        elif parsed.path == '/project':
            # Return project data
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            
            data = self.get_project_data()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        
        if parsed.path == '/chat':
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode())
                question = data.get('question', '')
                
                # Get answer from LLM
                answer = self.ask_question(question)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"answer": answer}).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_project_data(self):
        """Load project data from analysis."""
        if UmbraRequestHandler.project_data:
            return UmbraRequestHandler.project_data
        
        project_path = Path(UmbraRequestHandler.project_path)
        output_file = project_path / "output" / "LIVE_ARCHITECTURE.md"
        
        data = {
            "name": project_path.name,
            "path": str(project_path.absolute()),
            "diagram": "",
            "summary": "",
            "files": []
        }
        
        # Load architecture file
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8')
            
            # Extract diagram
            if "```mermaid" in content:
                start = content.index("```mermaid") + len("```mermaid")
                end = content.index("```", start)
                data["diagram"] = content[start:end].strip()
            
            # Extract summary
            if "## Project Summary" in content:
                start = content.index("## Project Summary") + len("## Project Summary")
                end = content.index("## System Overview") if "## System Overview" in content else len(content)
                data["summary"] = content[start:end].strip()
        
        # Get file list
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'output'}
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}
        
        for file_path in project_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                if not any(ignored in file_path.parts for ignored in ignore_dirs):
                    try:
                        relative = file_path.relative_to(project_path)
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        data["files"].append({
                            "path": str(relative),
                            "lines": len(content.splitlines()),
                            "preview": content[:500]
                        })
                    except Exception:
                        pass
        
        UmbraRequestHandler.project_data = data
        return data
    
    def ask_question(self, question: str) -> str:
        """Ask a question about the project using LLM."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, SystemMessage
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Error: GOOGLE_API_KEY not configured"
        
        # Get project context
        project_data = self.get_project_data()
        
        # Build context from project data
        context = f"""
## Project: {project_data['name']}

## Architecture Diagram:
```mermaid
{project_data['diagram']}
```

## Project Summary:
{project_data['summary']}

## Files in project:
"""
        for f in project_data['files'][:15]:  # Limit to 15 files
            context += f"\n### {f['path']} ({f['lines']} lines)\n```\n{f['preview']}\n```\n"
        
        system_prompt = f"""You are Umbra, an AI assistant that knows this codebase intimately.

You have analyzed this project and have access to:
- The architecture diagram
- Project summary
- Key files and their contents

{context}

## Your personality:
- Be concise and helpful
- Reference specific files when relevant
- Use code examples when appropriate
- If you don't know, say so

Answer the user's question about this codebase:"""
        
        llm = ChatGoogleGenerativeAI(
            model="models/gemini-flash-latest",
            google_api_key=api_key,
            temperature=0.3
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def start_server(project_path: str = ".", port: int = 8765):
    """Start the Umbra API server."""
    UmbraRequestHandler.project_path = project_path
    UmbraRequestHandler.project_data = None  # Reset cache
    
    server = HTTPServer(('localhost', port), UmbraRequestHandler)
    print(f"🌑 Umbra server running at http://localhost:{port}")
    print(f"   Project: {Path(project_path).absolute()}")
    print(f"   Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.shutdown()


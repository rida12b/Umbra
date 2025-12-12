"""
Auto-Documentation Generator.

Automatically generates and updates documentation for modules
based on code analysis.
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai
from rich.console import Console

console = Console()

# Configure API
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

DOC_PROMPT = """You are a documentation expert. Analyze this Python module and generate clear, concise documentation.

**File**: {file_path}
**Code**:
```python
{code}
```

Generate documentation in this EXACT format:

### {module_name}

**Purpose**: [One sentence explaining what this module does]

**Key Components**:
- `ComponentName`: Brief description
- `function_name()`: Brief description

**Dependencies**: [List external imports]

**Example Usage** (if applicable):
```python
# Brief example
```

Keep it SHORT and USEFUL. Focus on WHAT it does, not HOW.
"""

SECURITY_PROMPT = """You are a security expert. Analyze this code for potential vulnerabilities.

**File**: {file_path}
**Code**:
```python
{code}
```

Check for these vulnerabilities:
1. Hardcoded secrets/API keys
2. SQL injection risks
3. Command injection (os.system, subprocess without validation)
4. Path traversal vulnerabilities
5. Insecure deserialization
6. Missing input validation
7. Insecure file operations
8. Debug code left in production

Respond in this EXACT format (JSON):
{{
  "file": "{file_path}",
  "risk_level": "none|low|medium|high|critical",
  "issues": [
    {{
      "type": "vulnerability type",
      "line": line_number_or_null,
      "description": "brief description",
      "recommendation": "how to fix"
    }}
  ]
}}

If no issues found, return:
{{
  "file": "{file_path}",
  "risk_level": "none",
  "issues": []
}}

Return ONLY valid JSON, no markdown.
"""


def extract_module_info(code: str) -> Dict:
    """Extract structural information from Python code using AST."""
    info = {
        "classes": [],
        "functions": [],
        "imports": [],
        "constants": [],
    }
    
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                info["classes"].append({
                    "name": node.name,
                    "methods": methods,
                    "docstring": ast.get_docstring(node),
                })
            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                # Top-level function only
                info["functions"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node),
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info["imports"].append(node.module)
            elif isinstance(node, ast.Assign):
                # Look for constants (UPPER_CASE at module level)
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        info["constants"].append(target.id)
    except SyntaxError:
        pass
    
    return info


def generate_module_doc(file_path: str, code: str) -> Optional[str]:
    """Generate documentation for a single module."""
    if not api_key:
        return None
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        module_name = Path(file_path).stem
        
        response = model.generate_content(
            DOC_PROMPT.format(
                file_path=file_path,
                code=code[:8000],  # Limit code size
                module_name=module_name,
            ),
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1000,
            ),
        )
        
        return response.text.strip()
    except Exception as e:
        console.print(f"[yellow]   Doc generation failed: {e}[/yellow]")
        return None


def scan_security(file_path: str, code: str) -> Optional[Dict]:
    """Scan a file for security vulnerabilities."""
    if not api_key:
        return None
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        response = model.generate_content(
            SECURITY_PROMPT.format(
                file_path=file_path,
                code=code[:8000],
            ),
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1000,
            ),
        )
        
        # Parse JSON response
        import json
        text = response.text.strip()
        
        # Clean up if wrapped in markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text)
    except Exception as e:
        console.print(f"[yellow]   Security scan failed: {e}[/yellow]")
        return None


def generate_api_reference(modules: Dict[str, str]) -> str:
    """Generate API reference from all modules."""
    api_ref = []
    
    for file_path, code in modules.items():
        info = extract_module_info(code)
        module_name = Path(file_path).stem
        
        if info["functions"] or info["classes"]:
            api_ref.append(f"\n#### `{module_name}`\n")
            
            for func in info["functions"]:
                args = ", ".join(func["args"])
                doc = func["docstring"]
                if doc:
                    doc = doc.split("\n")[0]  # First line only
                    api_ref.append(f"- `{func['name']}({args})` - {doc}")
                else:
                    api_ref.append(f"- `{func['name']}({args})`")
            
            for cls in info["classes"]:
                methods = ", ".join(cls["methods"][:5])
                if len(cls["methods"]) > 5:
                    methods += ", ..."
                api_ref.append(f"- `class {cls['name']}` - Methods: {methods}")
    
    return "\n".join(api_ref) if api_ref else "No public API detected."


def generate_quick_context(project_summary: str, file_list: List[str]) -> str:
    """Generate a quick context paragraph for LLMs."""
    if not api_key:
        return "Quick context not available (no API key)."
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        prompt = f"""Based on this project information, write a SINGLE paragraph (3-5 sentences) that gives an LLM everything it needs to understand this project quickly.

**Project Summary**:
{project_summary}

**Files**:
{chr(10).join(file_list[:30])}

Write a dense, information-rich paragraph. Include: what the project does, main technologies, key entry points, and architecture pattern. NO bullet points, NO headers, just one paragraph."""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=300,
            ),
        )
        
        return response.text.strip()
    except Exception:
        return "Quick context generation failed."


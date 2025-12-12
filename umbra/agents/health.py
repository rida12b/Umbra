"""
Health Monitor Agent.

Continuously monitors project health, detecting:
- Broken imports (missing files)
- Syntax errors
- Circular dependencies
- Orphan files (never imported)
- Code quality issues
"""

import ast
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console

console = Console()


class IssueSeverity(Enum):
    """Severity level of health issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueType(Enum):
    """Type of health issue."""
    BROKEN_IMPORT = "broken_import"
    SYNTAX_ERROR = "syntax_error"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    ORPHAN_FILE = "orphan_file"
    GOD_FILE = "god_file"
    MISSING_INIT = "missing_init"
    HARDCODED_SECRET = "hardcoded_secret"
    DEPRECATED_USAGE = "deprecated_usage"


@dataclass
class HealthIssue:
    """A detected health issue."""
    issue_type: IssueType
    severity: IssueSeverity
    file_path: str
    line_number: Optional[int]
    message: str
    suggestion: str
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "file": self.file_path,
            "line": self.line_number,
            "message": self.message,
            "suggestion": self.suggestion,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class HealthReport:
    """Overall health report for the project."""
    score: int  # 0-100
    grade: str  # A, B, C, D, F
    issues: List[HealthIssue]
    metrics: Dict[str, int]
    scanned_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "issues": [i.to_dict() for i in self.issues],
            "metrics": self.metrics,
            "scanned_at": self.scanned_at.isoformat(),
        }


class HealthMonitor:
    """Monitors project health in real-time."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.issues: List[HealthIssue] = []
        self.file_contents: Dict[str, str] = {}
        self.import_graph: Dict[str, Set[str]] = {}
        
    def scan_project(self) -> HealthReport:
        """Perform a full health scan of the project."""
        self.issues = []
        self.file_contents = {}
        self.import_graph = {}
        
        # Find all Python files
        python_files = self._find_python_files()
        
        # Load and analyze each file
        for file_path in python_files:
            self._analyze_file(file_path)
        
        # Run cross-file checks
        self._check_broken_imports()
        self._check_circular_dependencies()
        self._check_orphan_files()
        self._check_missing_init()
        
        # Calculate score
        score, grade = self._calculate_score()
        
        # Build metrics
        metrics = {
            "total_files": len(python_files),
            "total_issues": len(self.issues),
            "critical_issues": len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL]),
            "error_issues": len([i for i in self.issues if i.severity == IssueSeverity.ERROR]),
            "warning_issues": len([i for i in self.issues if i.severity == IssueSeverity.WARNING]),
        }
        
        return HealthReport(
            score=score,
            grade=grade,
            issues=self.issues,
            metrics=metrics,
        )
    
    def check_file(self, file_path: str, content: str) -> List[HealthIssue]:
        """Check a single file for issues (for real-time monitoring)."""
        issues = []
        
        # Syntax check
        syntax_issue = self._check_syntax(file_path, content)
        if syntax_issue:
            issues.append(syntax_issue)
        
        # Secret check
        secret_issues = self._check_secrets(file_path, content)
        issues.extend(secret_issues)
        
        # God file check
        god_issue = self._check_god_file(file_path, content)
        if god_issue:
            issues.append(god_issue)
        
        return issues
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        ignore_patterns = {
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", "dist", "build", ".next", "output"
        }
        
        files = []
        for file_path in self.project_path.rglob("*.py"):
            if not any(p in file_path.parts for p in ignore_patterns):
                files.append(file_path)
        
        return files
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            self.file_contents[str(file_path)] = content
            
            # Extract imports
            imports = self._extract_imports(content)
            self.import_graph[str(file_path)] = imports
            
            # Check syntax
            syntax_issue = self._check_syntax(str(file_path), content)
            if syntax_issue:
                self.issues.append(syntax_issue)
            
            # Check secrets
            secret_issues = self._check_secrets(str(file_path), content)
            self.issues.extend(secret_issues)
            
            # Check god file
            god_issue = self._check_god_file(str(file_path), content)
            if god_issue:
                self.issues.append(god_issue)
                
        except Exception as e:
            self.issues.append(HealthIssue(
                issue_type=IssueType.SYNTAX_ERROR,
                severity=IssueSeverity.ERROR,
                file_path=str(file_path),
                line_number=None,
                message=f"Could not read file: {e}",
                suggestion="Check file encoding and permissions",
            ))
    
    def _extract_imports(self, content: str) -> Set[str]:
        """Extract import statements from Python code."""
        imports = set()
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except SyntaxError:
            # Try regex fallback
            import_pattern = r'^(?:from\s+([\w.]+)|import\s+([\w.]+))'
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                module = match.group(1) or match.group(2)
                if module:
                    imports.add(module.split('.')[0])
        
        return imports
    
    def _check_syntax(self, file_path: str, content: str) -> Optional[HealthIssue]:
        """Check for syntax errors."""
        try:
            ast.parse(content)
            return None
        except SyntaxError as e:
            return HealthIssue(
                issue_type=IssueType.SYNTAX_ERROR,
                severity=IssueSeverity.CRITICAL,
                file_path=file_path,
                line_number=e.lineno,
                message=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error before committing",
            )
    
    def _check_secrets(self, file_path: str, content: str) -> List[HealthIssue]:
        """Check for hardcoded secrets."""
        issues = []
        
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Password"),
            (r'secret\s*=\s*["\'][^"\']{10,}["\']', "Secret"),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', "Token"),
            (r'aws[_-]?access[_-]?key', "AWS Access Key"),
            (r'private[_-]?key\s*=', "Private Key"),
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
                
            for pattern, secret_type in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's reading from env
                    if 'os.getenv' in line or 'os.environ' in line or '.env' in line:
                        continue
                    
                    issues.append(HealthIssue(
                        issue_type=IssueType.HARDCODED_SECRET,
                        severity=IssueSeverity.CRITICAL,
                        file_path=file_path,
                        line_number=line_num,
                        message=f"Possible hardcoded {secret_type} detected",
                        suggestion=f"Move {secret_type} to environment variables",
                    ))
                    break
        
        return issues
    
    def _check_god_file(self, file_path: str, content: str) -> Optional[HealthIssue]:
        """Check for god files (too large)."""
        lines = len(content.split('\n'))
        
        if lines > 500:
            return HealthIssue(
                issue_type=IssueType.GOD_FILE,
                severity=IssueSeverity.WARNING if lines < 800 else IssueSeverity.ERROR,
                file_path=file_path,
                line_number=None,
                message=f"File has {lines} lines (threshold: 500)",
                suggestion="Consider splitting into smaller modules",
            )
        
        return None
    
    def _check_broken_imports(self):
        """Check for imports that reference non-existent local modules."""
        # Get all local module names
        local_modules = set()
        for file_path in self.file_contents.keys():
            rel_path = Path(file_path).relative_to(self.project_path)
            module_name = rel_path.stem
            if module_name != "__init__":
                local_modules.add(module_name)
            
            # Add parent directories as potential packages
            for parent in rel_path.parents:
                if parent != Path('.'):
                    local_modules.add(parent.name)
        
        # Check each file's imports
        for file_path, imports in self.import_graph.items():
            for imp in imports:
                # Skip standard library and known third-party
                if self._is_stdlib_or_thirdparty(imp):
                    continue
                
                # Check if it's a local module that exists
                if imp in local_modules:
                    continue
                
                # Check if the import could be a local module that's missing
                potential_file = self.project_path / f"{imp}.py"
                potential_package = self.project_path / imp / "__init__.py"
                
                if imp.startswith(self.project_path.name):
                    # It's trying to import from our project
                    parts = imp.split('.')
                    if len(parts) > 1 and parts[1] not in local_modules:
                        self.issues.append(HealthIssue(
                            issue_type=IssueType.BROKEN_IMPORT,
                            severity=IssueSeverity.ERROR,
                            file_path=file_path,
                            line_number=None,
                            message=f"Import '{imp}' may reference missing module",
                            suggestion="Check if the imported module exists",
                        ))
    
    def _check_circular_dependencies(self):
        """Detect circular import dependencies."""
        # Build a more detailed import graph
        module_imports: Dict[str, Set[str]] = {}
        
        for file_path in self.file_contents.keys():
            rel_path = Path(file_path).relative_to(self.project_path)
            module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
            
            imports = self.import_graph.get(file_path, set())
            # Filter to local imports only
            local_imports = {i for i in imports if not self._is_stdlib_or_thirdparty(i)}
            module_imports[module_name] = local_imports
        
        # Find cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []
        
        def find_cycle(module: str, path: List[str]) -> bool:
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for imp in module_imports.get(module, set()):
                if imp not in visited:
                    if find_cycle(imp, path):
                        return True
                elif imp in rec_stack:
                    # Found cycle
                    cycle_start = path.index(imp)
                    cycles.append(path[cycle_start:])
                    return True
            
            path.pop()
            rec_stack.remove(module)
            return False
        
        for module in module_imports:
            if module not in visited:
                find_cycle(module, [])
        
        # Report cycles
        for cycle in cycles[:3]:  # Limit to first 3 cycles
            cycle_str = " -> ".join(cycle + [cycle[0]])
            self.issues.append(HealthIssue(
                issue_type=IssueType.CIRCULAR_DEPENDENCY,
                severity=IssueSeverity.WARNING,
                file_path=cycle[0].replace('.', os.sep) + ".py",
                line_number=None,
                message=f"Circular dependency: {cycle_str}",
                suggestion="Refactor to break the circular dependency",
            ))
    
    def _check_orphan_files(self):
        """Find files that are never imported."""
        # Build set of all imported modules
        all_imports = set()
        for imports in self.import_graph.values():
            all_imports.update(imports)
        
        # Check each file
        entry_points = {"main", "__main__", "cli", "app", "wsgi", "asgi", "manage"}
        
        for file_path in self.file_contents.keys():
            rel_path = Path(file_path).relative_to(self.project_path)
            module_name = rel_path.stem
            
            # Skip entry points and init files
            if module_name in entry_points or module_name == "__init__":
                continue
            
            # Skip test files
            if "test" in str(rel_path).lower():
                continue
            
            # Check if any file imports this module
            is_imported = any(
                module_name in imp or module_name in imp.split('.')
                for imp in all_imports
            )
            
            if not is_imported:
                self.issues.append(HealthIssue(
                    issue_type=IssueType.ORPHAN_FILE,
                    severity=IssueSeverity.INFO,
                    file_path=file_path,
                    line_number=None,
                    message=f"File '{module_name}.py' is never imported",
                    suggestion="Remove if unused, or add to exports",
                ))
    
    def _check_missing_init(self):
        """Check for Python packages missing __init__.py."""
        # Find all directories containing Python files
        dirs_with_python = set()
        for file_path in self.file_contents.keys():
            dirs_with_python.add(Path(file_path).parent)
        
        # Check each directory
        for dir_path in dirs_with_python:
            if dir_path == self.project_path:
                continue
            
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                self.issues.append(HealthIssue(
                    issue_type=IssueType.MISSING_INIT,
                    severity=IssueSeverity.WARNING,
                    file_path=str(dir_path),
                    line_number=None,
                    message=f"Package missing __init__.py",
                    suggestion="Add __init__.py for proper package structure",
                ))
    
    def _is_stdlib_or_thirdparty(self, module: str) -> bool:
        """Check if a module is from stdlib or known third-party."""
        stdlib = {
            "os", "sys", "re", "json", "datetime", "time", "pathlib",
            "typing", "collections", "itertools", "functools", "ast",
            "dataclasses", "enum", "abc", "copy", "io", "logging",
            "threading", "multiprocessing", "subprocess", "socket",
            "http", "urllib", "email", "html", "xml", "sqlite3",
            "hashlib", "hmac", "secrets", "random", "math", "statistics",
            "unittest", "doctest", "pdb", "profile", "timeit",
            "argparse", "configparser", "csv", "pickle", "shelve",
            "contextlib", "traceback", "warnings", "inspect", "dis",
            "builtins", "importlib", "pkgutil", "types", "textwrap",
            "difflib", "tempfile", "shutil", "glob", "fnmatch",
        }
        
        thirdparty = {
            "click", "rich", "dotenv", "requests", "flask", "fastapi",
            "django", "sqlalchemy", "pydantic", "pytest", "numpy",
            "pandas", "scipy", "matplotlib", "google", "langchain",
            "langgraph", "openai", "anthropic", "watchdog", "uvicorn",
            "starlette", "httpx", "aiohttp", "asyncio", "anyio",
        }
        
        root = module.split('.')[0]
        return root in stdlib or root in thirdparty
    
    def _calculate_score(self) -> Tuple[int, str]:
        """Calculate health score and grade."""
        # Start with perfect score
        score = 100
        
        # Deduct points based on issues
        for issue in self.issues:
            if issue.severity == IssueSeverity.CRITICAL:
                score -= 15
            elif issue.severity == IssueSeverity.ERROR:
                score -= 8
            elif issue.severity == IssueSeverity.WARNING:
                score -= 3
            elif issue.severity == IssueSeverity.INFO:
                score -= 1
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        # Determine grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return score, grade


# Convenience function
def run_health_check(project_path: str) -> HealthReport:
    """Run a full health check on a project."""
    monitor = HealthMonitor(project_path)
    return monitor.scan_project()


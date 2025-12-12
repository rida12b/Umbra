"""
Change Tracker Agent.

Tracks all changes with rich context, impact analysis, and session timeline.
This is the core of Umbra's "Guardian" functionality.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import google.generativeai as genai
from rich.console import Console

console = Console()

# Configure API
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


class ChangeType(Enum):
    """Type of change detected."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ChangeIntent(Enum):
    """Detected intent of the change."""
    FEATURE = "feature"      # New functionality
    BUGFIX = "bugfix"        # Fixing a bug
    REFACTOR = "refactor"    # Code restructuring
    CLEANUP = "cleanup"      # Formatting, comments
    CONFIG = "config"        # Configuration changes
    BREAKING = "breaking"    # Breaking changes
    UNKNOWN = "unknown"


class ImpactLevel(Enum):
    """Impact level of the change."""
    NONE = "none"           # No impact on other files
    LOW = "low"             # 1-2 files affected
    MEDIUM = "medium"       # 3-5 files affected
    HIGH = "high"           # 6+ files affected
    CRITICAL = "critical"   # Core file, affects everything


@dataclass
class FileImpact:
    """Impact on a specific file."""
    file_path: str
    impact_type: str  # "imports", "calls", "inherits", "config"
    description: str


@dataclass
class TrackedChange:
    """A tracked change with full context."""
    timestamp: datetime
    file_path: str
    change_type: ChangeType
    intent: ChangeIntent
    description: str
    diff_summary: str
    lines_added: int
    lines_removed: int
    impacted_files: List[FileImpact]
    impact_level: ImpactLevel
    session_id: str
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "intent": self.intent.value,
            "description": self.description,
            "diff_summary": self.diff_summary,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "impacted_files": [
                {"file": f.file_path, "type": f.impact_type, "desc": f.description}
                for f in self.impacted_files
            ],
            "impact_level": self.impact_level.value,
            "session_id": self.session_id,
            "warnings": self.warnings,
        }


class DependencyGraph:
    """Tracks file dependencies for impact analysis."""
    
    def __init__(self):
        self.imports: Dict[str, Set[str]] = {}  # file -> files it imports
        self.imported_by: Dict[str, Set[str]] = {}  # file -> files that import it
        
    def add_file(self, file_path: str, content: str):
        """Analyze a file and add its dependencies to the graph."""
        imports = self._extract_imports(content, file_path)
        
        self.imports[file_path] = imports
        
        # Update reverse mapping
        for imported in imports:
            if imported not in self.imported_by:
                self.imported_by[imported] = set()
            self.imported_by[imported].add(file_path)
    
    def remove_file(self, file_path: str):
        """Remove a file from the dependency graph."""
        # Remove from imports
        if file_path in self.imports:
            del self.imports[file_path]
        
        # Remove from imported_by
        for imports_set in self.imported_by.values():
            imports_set.discard(file_path)
        
        if file_path in self.imported_by:
            del self.imported_by[file_path]
    
    def get_dependents(self, file_path: str) -> Set[str]:
        """Get all files that depend on this file (directly or indirectly)."""
        dependents = set()
        to_check = [file_path]
        
        while to_check:
            current = to_check.pop()
            direct_dependents = self.imported_by.get(current, set())
            
            for dep in direct_dependents:
                if dep not in dependents:
                    dependents.add(dep)
                    to_check.append(dep)
        
        return dependents
    
    def _extract_imports(self, content: str, file_path: str) -> Set[str]:
        """Extract import statements from Python code."""
        imports = set()
        
        try:
            tree = ast.parse(content)
            file_dir = Path(file_path).parent
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Convert module path to potential file path
                        module_parts = node.module.split('.')
                        imports.add(node.module)
        except SyntaxError:
            # If we can't parse, try regex
            import_pattern = r'^(?:from\s+([\w.]+)|import\s+([\w.]+))'
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                module = match.group(1) or match.group(2)
                if module:
                    imports.add(module)
        
        return imports


class ChangeTracker:
    """Main change tracking system."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.changes: List[TrackedChange] = []
        self.dependency_graph = DependencyGraph()
        self._initialized = False
        
    def initialize(self, files: Dict[str, str]):
        """Initialize the dependency graph with existing files."""
        for file_path, content in files.items():
            self.dependency_graph.add_file(file_path, content)
        self._initialized = True
        console.print(f"[dim]Tracker initialized with {len(files)} files[/dim]")
    
    def track_change(
        self,
        file_path: str,
        change_type: ChangeType,
        old_content: Optional[str],
        new_content: Optional[str],
        diff_lines: List[dict],
        stats: dict,
    ) -> TrackedChange:
        """Track a change and analyze its impact."""
        
        # Update dependency graph
        if change_type == ChangeType.DELETED:
            self.dependency_graph.remove_file(file_path)
        elif new_content:
            self.dependency_graph.add_file(file_path, new_content)
        
        # Analyze impact
        impacted_files = self._analyze_impact(file_path, change_type)
        impact_level = self._calculate_impact_level(impacted_files)
        
        # Detect intent
        intent = self._detect_intent(file_path, diff_lines, stats)
        
        # Generate description
        description = self._generate_description(
            file_path, change_type, diff_lines, stats
        )
        
        # Check for warnings
        warnings = self._detect_warnings(
            file_path, change_type, old_content, new_content
        )
        
        # Create diff summary
        diff_summary = self._create_diff_summary(diff_lines, stats)
        
        # Create tracked change
        change = TrackedChange(
            timestamp=datetime.now(),
            file_path=file_path,
            change_type=change_type,
            intent=intent,
            description=description,
            diff_summary=diff_summary,
            lines_added=stats.get("added", 0),
            lines_removed=stats.get("removed", 0),
            impacted_files=impacted_files,
            impact_level=impact_level,
            session_id=self.session_id,
            warnings=warnings,
        )
        
        self.changes.append(change)
        return change
    
    def _analyze_impact(
        self, file_path: str, change_type: ChangeType
    ) -> List[FileImpact]:
        """Analyze which files are impacted by this change."""
        impacts = []
        
        # Get files that import/depend on this file
        dependents = self.dependency_graph.get_dependents(file_path)
        
        for dep in dependents:
            # Determine impact type
            if change_type == ChangeType.DELETED:
                impact_type = "broken_import"
                description = f"Imports deleted file {Path(file_path).name}"
            else:
                impact_type = "imports"
                description = f"Imports {Path(file_path).name}"
            
            impacts.append(FileImpact(
                file_path=dep,
                impact_type=impact_type,
                description=description,
            ))
        
        return impacts
    
    def _calculate_impact_level(self, impacts: List[FileImpact]) -> ImpactLevel:
        """Calculate the overall impact level."""
        # Check for broken imports (critical)
        if any(i.impact_type == "broken_import" for i in impacts):
            return ImpactLevel.CRITICAL
        
        count = len(impacts)
        if count == 0:
            return ImpactLevel.NONE
        elif count <= 2:
            return ImpactLevel.LOW
        elif count <= 5:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.HIGH
    
    def _detect_intent(
        self,
        file_path: str,
        diff_lines: List[dict],
        stats: dict,
    ) -> ChangeIntent:
        """Detect the intent of the change using heuristics."""
        file_name = Path(file_path).name.lower()
        
        # Check file name patterns
        if "test" in file_name:
            return ChangeIntent.FEATURE  # Likely adding tests for feature
        if "config" in file_name or file_name in (".env", "settings.py"):
            return ChangeIntent.CONFIG
        
        # Analyze diff content
        added_lines = [d["line"] for d in diff_lines if d.get("type") == "add"]
        removed_lines = [d["line"] for d in diff_lines if d.get("type") == "remove"]
        
        added_text = " ".join(added_lines).lower()
        removed_text = " ".join(removed_lines).lower()
        
        # Check for bug fix patterns
        bugfix_patterns = ["fix", "bug", "issue", "error", "exception", "handle"]
        if any(p in added_text for p in bugfix_patterns):
            return ChangeIntent.BUGFIX
        
        # Check for refactor patterns
        if stats.get("added", 0) > 0 and stats.get("removed", 0) > 0:
            ratio = stats["added"] / max(stats["removed"], 1)
            if 0.8 <= ratio <= 1.2:  # Similar amount added/removed
                return ChangeIntent.REFACTOR
        
        # Check for cleanup
        if stats.get("removed", 0) > stats.get("added", 0) * 2:
            return ChangeIntent.CLEANUP
        
        # Default to feature for new code
        if stats.get("added", 0) > stats.get("removed", 0):
            return ChangeIntent.FEATURE
        
        return ChangeIntent.UNKNOWN
    
    def _generate_description(
        self,
        file_path: str,
        change_type: ChangeType,
        diff_lines: List[dict],
        stats: dict,
    ) -> str:
        """Generate a human-readable description of the change."""
        file_name = Path(file_path).name
        
        if change_type == ChangeType.CREATED:
            return f"New file created: {file_name}"
        elif change_type == ChangeType.DELETED:
            return f"File deleted: {file_name}"
        
        # For modifications, use LLM if available
        if api_key and diff_lines:
            return self._llm_description(file_name, diff_lines, stats)
        
        # Fallback to simple description
        added = stats.get("added", 0)
        removed = stats.get("removed", 0)
        return f"Modified {file_name}: +{added} -{removed} lines"
    
    def _llm_description(
        self,
        file_name: str,
        diff_lines: List[dict],
        stats: dict,
    ) -> str:
        """Generate description using LLM."""
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            # Build diff text
            diff_text = []
            for d in diff_lines[:15]:  # Limit
                prefix = "+" if d.get("type") == "add" else "-" if d.get("type") == "remove" else " "
                diff_text.append(f"{prefix} {d.get('line', '')}")
            
            prompt = f"""Describe this code change in ONE short sentence (max 10 words).

File: {file_name}
Changes: +{stats.get('added', 0)} -{stats.get('removed', 0)} lines

Diff:
{chr(10).join(diff_text)}

Be specific about WHAT changed, not generic. Example: "Added user authentication validation" not "Modified code"."""

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=50,
                ),
            )
            
            return response.text.strip().strip('"').strip("'")
        except Exception:
            return f"Modified {file_name}: +{stats.get('added', 0)} -{stats.get('removed', 0)} lines"
    
    def _detect_warnings(
        self,
        file_path: str,
        change_type: ChangeType,
        old_content: Optional[str],
        new_content: Optional[str],
    ) -> List[str]:
        """Detect potential issues with the change."""
        warnings = []
        
        # Warning: File deleted that others import
        if change_type == ChangeType.DELETED:
            dependents = self.dependency_graph.imported_by.get(file_path, set())
            if dependents:
                warnings.append(
                    f"BREAKING: {len(dependents)} file(s) import this deleted file"
                )
        
        # Warning: Syntax error in new content
        if new_content and file_path.endswith(".py"):
            try:
                ast.parse(new_content)
            except SyntaxError as e:
                warnings.append(f"SYNTAX ERROR: Line {e.lineno}: {e.msg}")
        
        # Warning: Hardcoded secrets
        if new_content:
            secret_patterns = [
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
            ]
            for pattern in secret_patterns:
                if re.search(pattern, new_content, re.IGNORECASE):
                    warnings.append("SECURITY: Possible hardcoded secret detected")
                    break
        
        return warnings
    
    def _create_diff_summary(self, diff_lines: List[dict], stats: dict) -> str:
        """Create a compact diff summary."""
        added = stats.get("added", 0)
        removed = stats.get("removed", 0)
        
        summary_parts = []
        if added:
            summary_parts.append(f"+{added}")
        if removed:
            summary_parts.append(f"-{removed}")
        
        return " ".join(summary_parts) if summary_parts else "no changes"
    
    def get_session_timeline(self) -> List[dict]:
        """Get timeline of changes for current session."""
        return [c.to_dict() for c in self.changes]
    
    def get_session_summary(self) -> dict:
        """Get summary statistics for current session."""
        if not self.changes:
            return {
                "session_id": self.session_id,
                "total_changes": 0,
                "files_modified": 0,
                "lines_added": 0,
                "lines_removed": 0,
                "warnings": 0,
                "breaking_changes": 0,
            }
        
        files_modified = len(set(c.file_path for c in self.changes))
        total_added = sum(c.lines_added for c in self.changes)
        total_removed = sum(c.lines_removed for c in self.changes)
        total_warnings = sum(len(c.warnings) for c in self.changes)
        breaking = sum(1 for c in self.changes if c.impact_level == ImpactLevel.CRITICAL)
        
        return {
            "session_id": self.session_id,
            "total_changes": len(self.changes),
            "files_modified": files_modified,
            "lines_added": total_added,
            "lines_removed": total_removed,
            "warnings": total_warnings,
            "breaking_changes": breaking,
        }


# Global tracker instance
_tracker: Optional[ChangeTracker] = None


def get_tracker(project_path: str) -> ChangeTracker:
    """Get or create the global tracker instance."""
    global _tracker
    if _tracker is None or str(_tracker.project_path) != str(Path(project_path).resolve()):
        _tracker = ChangeTracker(project_path)
    return _tracker


"""
Insights Engine - Automatically detect architectural problems and provide recommendations.
"""
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class InsightSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Insight:
    title: str
    description: str
    severity: InsightSeverity
    affected_files: List[str]
    recommendation: str
    

def analyze_file_metrics(project_path: str) -> Dict[str, Any]:
    """Analyze basic file metrics."""
    project = Path(project_path)
    
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 
                   'env', 'dist', 'build', '.next', 'output'}
    
    extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}
    
    metrics = {
        'total_files': 0,
        'total_lines': 0,
        'files_by_type': {},
        'largest_files': [],
        'files_by_dir': {},
    }
    
    file_sizes = []
    
    for file_path in project.rglob('*'):
        if file_path.is_file() and file_path.suffix in extensions:
            # Skip ignored directories
            if any(ignored in file_path.parts for ignored in ignore_dirs):
                continue
            
            try:
                relative_path = str(file_path.relative_to(project))
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = len(content.splitlines())
                
                metrics['total_files'] += 1
                metrics['total_lines'] += lines
                
                # Count by extension
                ext = file_path.suffix
                metrics['files_by_type'][ext] = metrics['files_by_type'].get(ext, 0) + 1
                
                # Count by directory
                parent = str(file_path.parent.relative_to(project))
                metrics['files_by_dir'][parent] = metrics['files_by_dir'].get(parent, 0) + 1
                
                file_sizes.append((relative_path, lines))
                
            except Exception:
                continue
    
    # Get largest files
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    metrics['largest_files'] = file_sizes[:5]
    
    return metrics


def detect_god_files(project_path: str, threshold: int = 300) -> List[Insight]:
    """Detect files that are too large (God files)."""
    insights = []
    metrics = analyze_file_metrics(project_path)
    
    for filepath, lines in metrics['largest_files']:
        if lines > threshold:
            insights.append(Insight(
                title=f"Large file detected: {filepath}",
                description=f"This file has {lines} lines, which may indicate it has too many responsibilities.",
                severity=InsightSeverity.WARNING if lines < 500 else InsightSeverity.CRITICAL,
                affected_files=[filepath],
                recommendation="Consider splitting this file into smaller, focused modules."
            ))
    
    return insights


def detect_deep_nesting(project_path: str, max_depth: int = 4) -> List[Insight]:
    """Detect deeply nested directory structures."""
    insights = []
    project = Path(project_path)
    
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'dist', 'build'}
    
    for file_path in project.rglob('*.py'):
        if any(ignored in file_path.parts for ignored in ignore_dirs):
            continue
            
        relative = file_path.relative_to(project)
        depth = len(relative.parts) - 1  # -1 for the file itself
        
        if depth > max_depth:
            insights.append(Insight(
                title=f"Deep nesting: {relative}",
                description=f"This file is {depth} directories deep, which can make navigation difficult.",
                severity=InsightSeverity.INFO,
                affected_files=[str(relative)],
                recommendation="Consider flattening your directory structure."
            ))
            break  # Only report once
    
    return insights


def detect_missing_init(project_path: str) -> List[Insight]:
    """Detect Python packages missing __init__.py."""
    insights = []
    project = Path(project_path)
    
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'dist', 'build', 'output'}
    
    for dir_path in project.rglob('*'):
        if not dir_path.is_dir():
            continue
        if any(ignored in dir_path.parts for ignored in ignore_dirs):
            continue
        
        # Check if directory has .py files but no __init__.py
        py_files = list(dir_path.glob('*.py'))
        has_init = (dir_path / '__init__.py').exists()
        
        if py_files and not has_init and dir_path != project:
            relative = dir_path.relative_to(project)
            insights.append(Insight(
                title=f"Missing __init__.py in {relative}",
                description="This directory contains Python files but no __init__.py, so it's not a proper package.",
                severity=InsightSeverity.INFO,
                affected_files=[str(relative)],
                recommendation="Add an __init__.py file to make this a proper Python package."
            ))
    
    return insights


def detect_circular_potential(project_path: str) -> List[Insight]:
    """Detect potential circular import risks based on import patterns."""
    insights = []
    project = Path(project_path)
    
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env'}
    
    # Track imports between files
    imports_map = {}  # file -> list of imported modules
    
    for file_path in project.rglob('*.py'):
        if any(ignored in file_path.parts for ignored in ignore_dirs):
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            relative = str(file_path.relative_to(project))
            
            # Simple import detection
            imports = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('from ') or line.startswith('import '):
                    # Extract module name
                    if line.startswith('from '):
                        parts = line.split()
                        if len(parts) >= 2:
                            imports.append(parts[1])
                    else:
                        parts = line.split()
                        if len(parts) >= 2:
                            imports.append(parts[1].split('.')[0])
            
            imports_map[relative] = imports
            
        except Exception:
            continue
    
    # Check for files with many internal imports (potential coupling issues)
    for filepath, imports in imports_map.items():
        internal_imports = [i for i in imports if not i.startswith(('os', 'sys', 'json', 'typing', 'pathlib', 'dataclass', 'enum'))]
        if len(internal_imports) > 10:
            insights.append(Insight(
                title=f"High coupling: {filepath}",
                description=f"This file imports {len(internal_imports)} modules, indicating high coupling.",
                severity=InsightSeverity.WARNING,
                affected_files=[filepath],
                recommendation="Consider reducing dependencies or using dependency injection."
            ))
    
    return insights


def calculate_health_score(insights: List[Insight], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall architecture health score."""
    
    # Base score
    score = 100
    
    # Deduct for insights
    for insight in insights:
        if insight.severity == InsightSeverity.CRITICAL:
            score -= 15
        elif insight.severity == InsightSeverity.WARNING:
            score -= 8
        else:
            score -= 2
    
    # Bonus for good practices
    if metrics['total_files'] > 0:
        avg_lines = metrics['total_lines'] / metrics['total_files']
        if avg_lines < 200:
            score += 5  # Good file sizes
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Determine grade
    if score >= 90:
        grade = 'A'
        status = 'Excellent'
    elif score >= 75:
        grade = 'B'
        status = 'Good'
    elif score >= 60:
        grade = 'C'
        status = 'Needs Improvement'
    elif score >= 40:
        grade = 'D'
        status = 'Poor'
    else:
        grade = 'F'
        status = 'Critical'
    
    return {
        'score': score,
        'grade': grade,
        'status': status,
        'total_issues': len(insights),
        'critical': sum(1 for i in insights if i.severity == InsightSeverity.CRITICAL),
        'warnings': sum(1 for i in insights if i.severity == InsightSeverity.WARNING),
        'info': sum(1 for i in insights if i.severity == InsightSeverity.INFO),
    }


def run_full_analysis(project_path: str = ".") -> Dict[str, Any]:
    """Run all insight detectors and return full analysis."""
    
    # Collect metrics
    metrics = analyze_file_metrics(project_path)
    
    # Run all detectors
    insights = []
    insights.extend(detect_god_files(project_path))
    insights.extend(detect_deep_nesting(project_path))
    insights.extend(detect_missing_init(project_path))
    insights.extend(detect_circular_potential(project_path))
    
    # Calculate health score
    health = calculate_health_score(insights, metrics)
    
    return {
        'metrics': metrics,
        'insights': insights,
        'health': health,
    }


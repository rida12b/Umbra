"""
Mermaid syntax validator.

Ensures that generated Mermaid diagrams are valid before writing to file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

console = Console()


@dataclass
class ValidationResult:
    """Result of Mermaid validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_mermaid(mermaid: str) -> ValidationResult:
    """
    Validate Mermaid.js syntax.

    Performs basic structural validation to catch common errors.
    """
    errors = []
    warnings = []

    if not mermaid or not mermaid.strip():
        errors.append("Empty diagram")
        return ValidationResult(is_valid=False, errors=errors)

    lines = mermaid.strip().split("\n")

    # Rule 1: Must start with graph/flowchart directive
    first_line = lines[0].strip()
    if not re.match(r"^(graph|flowchart)\s+(TD|TB|LR|RL|BT)", first_line):
        errors.append(
            f"Diagram must start with 'graph TD' or similar directive, got: {first_line[:50]}"
        )

    # Rule 2: Balanced subgraphs
    subgraph_count = sum(1 for line in lines if line.strip().startswith("subgraph"))
    # Count 'end' that closes subgraphs (not part of other words)
    end_count = sum(1 for line in lines if re.match(r"^\s*end\s*$", line))

    if subgraph_count != end_count:
        errors.append(
            f"Unbalanced subgraphs: {subgraph_count} 'subgraph' vs {end_count} 'end'"
        )

    # Rule 3: No dangerous content
    dangerous_patterns = ["<script", "javascript:", "onclick", "onerror"]
    for pattern in dangerous_patterns:
        if pattern.lower() in mermaid.lower():
            errors.append(f"Potentially dangerous content detected: {pattern}")

    # Rule 4: Check for balanced brackets
    if mermaid.count("[") != mermaid.count("]"):
        errors.append(
            f"Unbalanced square brackets: {mermaid.count('[')} '[' vs {mermaid.count(']')} ']'"
        )

    if mermaid.count("(") != mermaid.count(")"):
        errors.append(
            f"Unbalanced parentheses: {mermaid.count('(')} '(' vs {mermaid.count(')')} ')'"
        )

    # Rule 5: Check for common syntax issues (warnings)
    if re.search(r"\w+->\w+", mermaid):
        warnings.append("Found '->' instead of '-->'. Consider using '-->' for arrows.")

    # Rule 6: Check for empty subgraphs (warning, not error)
    subgraph_pattern = re.compile(r"subgraph\s+.*?\n\s*end", re.DOTALL)
    for match in subgraph_pattern.finditer(mermaid):
        content = match.group()
        # Check if there's any content between subgraph and end
        inner = content.split("\n")[1:-1]
        if not any(line.strip() for line in inner):
            warnings.append("Found empty subgraph")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validator_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node to validate the updated Mermaid diagram.

    Input: updated_mermaid, retry_count
    Output: is_valid_mermaid, validation_error
    """
    updated = state.get("updated_mermaid")

    if not updated:
        return {
            **state,
            "is_valid_mermaid": False,
            "validation_error": "No diagram to validate",
        }

    result = validate_mermaid(updated)

    if result.warnings:
        for warning in result.warnings:
            console.print(f"[yellow]   WARNING: {warning}[/yellow]")

    if not result.is_valid:
        error_msg = "; ".join(result.errors)
        console.print(f"[red]   FAILED: Validation failed: {error_msg}[/red]")
        return {
            **state,
            "is_valid_mermaid": False,
            "validation_error": error_msg,
        }

    console.print("[dim]   -> Validation passed[/dim]")
    return {
        **state,
        "is_valid_mermaid": True,
        "validation_error": None,
    }


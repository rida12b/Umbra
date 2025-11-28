"""
LangGraph state definitions for Umbra.

This module defines the GraphState that flows through the analysis pipeline.
"""

from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass
class AnalysisResult:
    """Output of the Analyst node."""

    is_structural_change: bool
    change_type: Literal[
        "new_service",
        "new_dependency",
        "api_call",
        "db_connection",
        "inter_service",
        "refactor",
        "cosmetic",
    ]
    affected_components: list[str]
    reasoning: str


class GraphState(TypedDict, total=False):
    """
    State that flows through the LangGraph pipeline.

    This is the central data structure that all nodes read from and write to.
    """

    # Input from watcher
    file_path: str
    file_content: str
    diff: str | None

    # Current architecture (loaded from file)
    current_mermaid: str

    # Analyst output
    analysis_result: AnalysisResult | None

    # Surgeon output
    updated_mermaid: str | None

    # Validation
    is_valid_mermaid: bool
    validation_error: str | None

    # Meta
    retry_count: int


# Initial diagram template
INITIAL_DIAGRAM = """graph LR
    subgraph Core["Core Services"]
        App[Application]
    end

    subgraph External["External APIs"]
    end

    subgraph Data["Data Stores"]
    end
"""


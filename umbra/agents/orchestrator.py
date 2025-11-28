"""
LangGraph Orchestrator.

This module builds and compiles the LangGraph that orchestrates
the entire analysis pipeline.
"""

from langgraph.graph import END, StateGraph
from rich.console import Console

from umbra.agents.analyst import analyst_node
from umbra.agents.state import GraphState
from umbra.agents.surgeon import surgeon_node
from umbra.agents.writer import writer_node
from umbra.validators.mermaid import validator_node

console = Console()

# Maximum retry attempts for invalid Mermaid
MAX_RETRIES = 3


def should_update(state: GraphState) -> str:
    """
    Router function after analysis.

    Determines if we should update the diagram or skip.
    """
    analysis = state.get("analysis_result")

    if analysis and analysis.is_structural_change:
        return "update"

    console.print("[dim]   -> No structural change, skipping[/dim]")
    return "skip"


def check_validity(state: GraphState) -> str:
    """
    Router function after validation.

    Determines next step based on validation result.
    """
    if state.get("is_valid_mermaid", False):
        return "valid"

    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
        console.print(f"[yellow]   WARNING: Max retries ({MAX_RETRIES}) reached, aborting[/yellow]")
        return "abort"

    console.print(f"[yellow]   RETRY: {retry_count + 1}/{MAX_RETRIES}[/yellow]")
    return "retry"


def increment_retry(state: GraphState) -> GraphState:
    """Increment the retry counter."""
    return {**state, "retry_count": state.get("retry_count", 0) + 1}


def build_graph() -> StateGraph:
    """
    Build the Umbra analysis graph.

    The flow is:
    1. Analyst analyzes the change
    2. If structural -> Surgeon updates diagram
    3. Validator checks Mermaid syntax
    4. If valid -> Writer saves to file
    5. If invalid -> Retry (up to MAX_RETRIES) or abort

    Returns:
        Compiled StateGraph ready to invoke
    """
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyst", analyst_node)
    graph.add_node("surgeon", surgeon_node)
    graph.add_node("validator", validator_node)
    graph.add_node("writer", writer_node)
    graph.add_node("increment_retry", increment_retry)

    # Set entry point
    graph.set_entry_point("analyst")

    # Define edges
    graph.add_conditional_edges(
        "analyst",
        should_update,
        {
            "skip": END,
            "update": "surgeon",
        },
    )

    graph.add_edge("surgeon", "validator")

    graph.add_conditional_edges(
        "validator",
        check_validity,
        {
            "valid": "writer",
            "retry": "increment_retry",
            "abort": END,
        },
    )

    graph.add_edge("increment_retry", "surgeon")
    graph.add_edge("writer", END)

    return graph.compile()


# Pre-built graph instance for convenience
def get_graph():
    """Get a compiled graph instance."""
    return build_graph()


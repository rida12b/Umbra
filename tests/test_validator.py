"""Tests for the Mermaid validator."""

import pytest

from umbra.validators.mermaid import validate_mermaid


class TestMermaidValidator:
    """Test cases for validate_mermaid function."""

    def test_valid_simple_diagram(self):
        """A simple valid diagram should pass."""
        mermaid = """graph TD
    A --> B
    B --> C"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_diagram_with_subgraphs(self):
        """A diagram with balanced subgraphs should pass."""
        mermaid = """graph TD
    subgraph "Core Services"
        ServiceA[Service A]
        ServiceB[Service B]
    end
    
    subgraph "External APIs"
        StripeAPI[Stripe API]
    end
    
    ServiceA --> ServiceB
    ServiceB --> StripeAPI"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is True

    def test_invalid_missing_directive(self):
        """Diagram without graph directive should fail."""
        mermaid = """A --> B
    B --> C"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is False
        assert any("graph" in e.lower() or "directive" in e.lower() for e in result.errors)

    def test_invalid_unbalanced_subgraphs(self):
        """Diagram with unclosed subgraph should fail."""
        mermaid = """graph TD
    subgraph "Test"
        A --> B"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is False
        assert any("subgraph" in e.lower() for e in result.errors)

    def test_invalid_unbalanced_brackets(self):
        """Diagram with unbalanced brackets should fail."""
        mermaid = """graph TD
    A[Unclosed
    B --> C"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is False
        assert any("bracket" in e.lower() for e in result.errors)

    def test_invalid_empty_diagram(self):
        """Empty diagram should fail."""
        result = validate_mermaid("")
        assert result.is_valid is False

    def test_warning_wrong_arrow_syntax(self):
        """Using -> instead of --> should produce a warning."""
        mermaid = """graph TD
    A->B"""
        result = validate_mermaid(mermaid)
        # This is a warning, not an error
        assert len(result.warnings) > 0
        assert any("->" in w for w in result.warnings)

    def test_valid_flowchart_directive(self):
        """Flowchart directive should also be valid."""
        mermaid = """flowchart TD
    A --> B"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is True

    def test_valid_different_directions(self):
        """Different graph directions should be valid."""
        for direction in ["TD", "TB", "LR", "RL", "BT"]:
            mermaid = f"""graph {direction}
    A --> B"""
            result = validate_mermaid(mermaid)
            assert result.is_valid is True, f"Failed for direction {direction}"

    def test_dangerous_content_detected(self):
        """Potentially dangerous content should fail."""
        mermaid = """graph TD
    A[<script>alert('xss')</script>] --> B"""
        result = validate_mermaid(mermaid)
        assert result.is_valid is False
        assert any("dangerous" in e.lower() for e in result.errors)


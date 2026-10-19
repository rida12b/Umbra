"""YAML read as a node tree, so every value keeps the lines it was written on (Evidence)."""

from collections.abc import Iterator
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class Located:
    """A YAML node with its 1-based line range."""

    node: yaml.Node
    start: int
    end: int


class YamlText:
    """The parsed documents of one file, plus its lines to compute exact Evidence ranges."""

    def __init__(self, text: str) -> None:
        self.lines = [line.rstrip("\r") for line in text.split("\n")]
        self.documents = [doc for doc in yaml.compose_all(text, Loader=yaml.SafeLoader) if doc is not None]

    def located(self, node: yaml.Node) -> Located:
        return Located(node, node.start_mark.line + 1, self._end(node.start_mark.line, node.end_mark))

    def span(self, key: yaml.Node, value: yaml.Node) -> tuple[int, int]:
        """Lines from a mapping key to the last line of its value."""
        return key.start_mark.line + 1, self._end(key.start_mark.line, value.end_mark)

    def _end(self, start_row: int, mark: yaml.Mark) -> int:
        """Last 1-based line holding the node: a block ends where the next key starts, so step back
        over that line when nothing of the node is on it, then over trailing blank or comment lines."""
        row = mark.line
        if row >= len(self.lines) or not self.lines[row][: mark.column].strip():
            row -= 1
        while row > start_row and (not self.lines[row].strip() or self.lines[row].lstrip().startswith("#")):
            row -= 1
        return max(row, start_row) + 1


def items(node: yaml.Node | None) -> Iterator[tuple[str, yaml.Node, yaml.Node]]:
    """`(key, key node, value node)` of a mapping; nothing for other node types."""
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode):
                yield str(key.value), key, value


def get(node: yaml.Node | None, *path: str) -> yaml.Node | None:
    for part in path:
        node = next((value for key, _, value in items(node) if key == part), None)
    return node


def scalar(node: yaml.Node | None) -> str | None:
    return str(node.value) if isinstance(node, yaml.ScalarNode) else None


def sequence(node: yaml.Node | None) -> list[yaml.Node]:
    return list(node.value) if isinstance(node, yaml.SequenceNode) else []

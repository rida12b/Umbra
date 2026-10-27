"""« Ce qu'on peut faire » (ADR-0007, #107): the addresses a server answers and the commands a CLI offers,
grouped by file, read in the code (route decorators, `@group.command`), never named by a model. French
words only where the shape of the address says it all (`card_routes.label`); a command keeps its name."""

import ast
import posixpath
from dataclasses import dataclass, field

from umbra_engine.projection import card_routes
from umbra_engine.projection.card_code import parse
from umbra_engine.projection.card_routes import TextOf, action_id
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_units import Unit

ROUTES = "routes"
COMMANDS = "commands"


@dataclass
class Action:
    id: str  # the function's file and line: « backend/app/api/routes/items.py:62 »
    kind: str  # « routes » or « commands »
    verb: str  # « POST »; empty for a command
    label: str  # « Créer un item » for a plain shape; empty otherwise
    address: str  # « /api/v1/items/ », or the command as typed: « insert »
    name: str  # the function: « create_item »
    file: str
    line: int


@dataclass
class ActionGroup:
    file: str  # repo path: « backend/app/api/routes/items.py »
    kind: str
    actions: list[Action] = field(default_factory=list)


@dataclass
class ActionList:
    total: int = 0
    groups: list[ActionGroup] = field(default_factory=list)

    def find(self, action: str) -> Action | None:
        return next((a for g in self.groups for a in g.actions if a.id == action), None)


def list_actions(facts: Facts, units: list[Unit], text_of: TextOf) -> ActionList:
    groups = _routes(facts, units, text_of) + _commands(facts, units, text_of)
    return ActionList(sum(len(g.actions) for g in groups), groups)


def _routes(facts: Facts, units: list[Unit], text_of: TextOf) -> list[ActionGroup]:
    """Files that manage things (every address of a plain shape) first, then by name: items before login."""
    groups: list[ActionGroup] = []
    for unit in (u for u in units if u.role == "server"):
        files = sorted({c.file for c in facts.signal("route", unit.files)})
        by_file: dict[str, ActionGroup] = {}
        for file, route, full, words in card_routes.read_routes(facts, unit.files, files, text_of):
            if not route.name:  # an inline JavaScript handler: no function to trace
                continue
            group = by_file.setdefault(file, ActionGroup(file, ROUTES))
            group.actions.append(
                Action(
                    action_id(file, route.line), ROUTES, route.verb, words, full, route.name, file, route.line
                )
            )
        groups += sorted(
            by_file.values(),
            key=lambda g: (-sum(1 for a in g.actions if a.label), posixpath.basename(g.file), g.file),
        )
    return groups


def _commands(facts: Facts, units: list[Unit], text_of: TextOf) -> list[ActionGroup]:
    """`@cli.command()` above `def add_column` → « add-column », as click names it; `name=` when given."""
    groups: list[ActionGroup] = []
    for unit in (u for u in units if u.role == "cli"):
        lines: dict[str, set[int]] = {}
        for claim in facts.commands(unit.files):
            lines.setdefault(claim.file, set()).add(claim.line_start)
        for file in sorted(lines):
            tree = parse(text_of(file) or "")
            found = [_command(node, lines[file]) for node in ast.walk(tree)] if tree else []
            actions = sorted((a for a in found if a), key=lambda a: a[2])
            if actions:
                group = ActionGroup(file, COMMANDS)
                for name, function, line in actions:
                    group.actions.append(
                        Action(action_id(file, line), COMMANDS, "", "", name, function, file, line)
                    )
                groups.append(group)
    return groups


def _command(node: ast.AST, lines: set[int]) -> tuple[str, str, int] | None:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    for decorator in node.decorator_list:
        if decorator.lineno in lines and isinstance(decorator, ast.Call):
            named = next((k.value for k in decorator.keywords if k.arg == "name"), None)
            first = decorator.args[0] if decorator.args else named
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value, node.name, node.lineno
            return node.name.replace("_", "-"), node.name, node.lineno
    return None

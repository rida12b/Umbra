"""« Ce qu'on peut faire » (ADR-0007, #107): the addresses a server answers and the commands a CLI offers,
grouped by file, read in the code (route decorators, `@group.command`), never named by a model. A route's
French words come from `route_words`, a command's from `command_words` (#108). Each file of routes gets one
role word (« items », « comptes », « connexion », « outils », « en local seulement »)."""

import ast
import posixpath
from dataclasses import dataclass, field

from umbra_engine.projection import card_routes, command_words
from umbra_engine.projection.card_code import Mount, mounts, parse
from umbra_engine.projection.card_routes import ORDER, TextOf, action_id
from umbra_engine.projection.inside_words import PAGE_WORDS, STEM_TITLES, table_words
from umbra_engine.projection.route_words import OTHERS, caller_rank
from umbra_engine.projection.system_facts import Facts
from umbra_engine.projection.system_purpose import ACCOUNT_TABLES
from umbra_engine.projection.system_units import Unit

ROUTES = "routes"
COMMANDS = "commands"


@dataclass
class Action:
    id: str  # the function's file and line: « backend/app/api/routes/items.py:62 »
    kind: str  # « routes » or « commands »
    verb: str  # « POST »; empty for a command
    label: str  # « Créer un item » (`route_words`), « Créer une table » (`command_words`); empty: no rule
    address: str  # « /api/v1/items/ », or the command as typed: « insert »
    name: str  # the function: « create_item »
    file: str
    line: int


@dataclass
class ActionGroup:
    file: str  # repo path: « backend/app/api/routes/items.py »
    kind: str
    actions: list[Action] = field(default_factory=list)
    role: str = ""  # one French word for a file of routes: « comptes »; empty for commands


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
    """The files about what the app keeps first (« items », then « comptes »), then the others in the order
    they are mounted, a file mounted only in local last. Inside a file, what the caller does for himself
    first (sign up, then « me »), then the code's order."""
    words = table_words(facts)
    groups: list[ActionGroup] = []
    for unit in (u for u in units if u.role == "server"):
        files = sorted({c.file for c in facts.signal("route", unit.files)})
        mounted = [
            m
            for f in sorted({c.file for c in facts.signal("mount", unit.files)})
            for m in mounts(text_of(f) or "")
        ]
        by_file: dict[str, ActionGroup] = {}
        for file, route, full, label in card_routes.read_routes(facts, unit.files, files, text_of):
            if not route.name:  # an inline JavaScript handler: no function to trace
                continue
            group = by_file.setdefault(file, ActionGroup(file, ROUTES, role=_role(file, words, mounted)))
            group.actions.append(
                Action(
                    action_id(file, route.line), ROUTES, route.verb, label, full, route.name, file, route.line
                )
            )
        for group in by_file.values():
            group.actions.sort(key=_row_order)
        groups += sorted(by_file.values(), key=lambda g: _group_order(g, words, mounted))
    return groups


def _row_order(action: Action) -> tuple[int, int, int]:
    rank = caller_rank(action.address)
    verb = ORDER.index(action.verb) if rank != OTHERS and action.verb in ORDER else 0
    return rank, verb, action.line


def _group_order(
    group: ActionGroup, words: dict[str, str], mounted: list[Mount]
) -> tuple[bool, int, int, str]:
    stem = _stem(group.file)
    local = any(m.local for m in _mounts_of(stem, mounted))
    thing = stem.rstrip("s")
    kept = 0 if thing in words and thing not in ACCOUNT_TABLES else 1 if thing in words else 2
    at = next((i for i, m in enumerate(mounted) if m.target.split(".")[0] == stem), len(mounted))
    return local, kept, at, group.file


def _role(file: str, words: dict[str, str], mounted: list[Mount]) -> str:
    stem = _stem(file)
    if _mounts_of(stem, mounted) and all(m.local for m in _mounts_of(stem, mounted)):
        return "en local seulement"
    if stem.rstrip("s") in words:
        return words[stem.rstrip("s")]
    return PAGE_WORDS.get(stem) or STEM_TITLES.get(stem, stem).lower()


def _mounts_of(stem: str, mounted: list[Mount]) -> list[Mount]:
    return [m for m in mounted if m.target.split(".")[0] == stem]


def _stem(file: str) -> str:
    return posixpath.splitext(posixpath.basename(file))[0].lower()


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
                    words = command_words.label(name)
                    group.actions.append(
                        Action(action_id(file, line), COMMANDS, "", words, name, function, file, line)
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

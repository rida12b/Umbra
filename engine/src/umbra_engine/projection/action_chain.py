"""The static call chain of one action (#107): from the function that answers it, what it reaches, read
with `ast` in the text the Secret Guard released, joined through the imports Umbra indexed. No model and
no code is run. Reached: FastAPI dependencies (`Depends`, also through an `Annotated` alias), functions
called by name or through an imported module, classes used (`Item.model_validate`), methods of its own
class, and the lines that write (a row, a mail, an SQLite file). A method found by its name alone (the
object's type is not read) is a guess, and so is everything reached through it."""

import ast
from collections import deque
from dataclasses import dataclass

from umbra_engine.projection.action_code import Code, Definition
from umbra_engine.projection.system_facts import Facts

MAX_DEPTH = 4
MAX_FUNCTIONS = 40
WRITES = ("db-write", "smtp", "sqlite")  # the lines that make something leave the project
CONNECTIONS = ("Session", "Connection", "Engine")  # a dependency that only hands over the connection
SELF = ("self", "cls")


@dataclass
class Hit:
    file: str
    line: int  # where the reached thing is defined; for a write, the line that writes
    name: str  # « get_current_user », « Item », « session.commit »
    kind: str  # « handler », « function », « class », « write »
    depth: int  # 0 for the handler and what it writes itself
    guess: bool = False
    signal: str = ""  # a write: « db-write », « smtp », « sqlite »
    reason: str = ""  # a guess: « name » (a method found by its name alone) or « class » (inside a class)
    reads: str = ""  # a table class it fetches a row of: `session.get(User, …)` → « User »


NAME = "name"
CLASS = "class"


def chain(code: Code, facts: Facts, file: str, line: int) -> list[Hit]:
    """Breadth first, so what the handler does itself comes before what its callees do."""
    handler = code.function_at(file, line)
    if handler is None:
        return []
    hits = [Hit(file, handler.lineno, handler.name, "handler", 0)]
    tables = {c.object.split(":", 2)[2] for c in facts.signals_starting("table:")}
    queue = deque([(Definition(file, handler, code.class_of(file, handler)), 0, "")])
    seen = {(file, handler.lineno)}
    while queue and len(seen) <= MAX_FUNCTIONS:
        here, depth, reason = queue.popleft()
        hits += _writes(code, facts, here, depth, reason)
        if depth >= MAX_DEPTH:
            continue
        for target, guessed in _dependencies(code, here) + _calls(code, here):
            node, key = target.node, (target.file, target.node.lineno)
            if key in seen or isinstance(node, ast.Assign | ast.AnnAssign):
                continue
            seen.add(key)
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            name = f"{target.owner}.{node.name}" if target.owner else node.name
            why = reason or (NAME if guessed else "")
            reads = _reads(node, tables) if kind == "function" else ""
            hits.append(
                Hit(target.file, node.lineno, name, kind, depth + 1, bool(why), reason=why, reads=reads)
            )
            if kind == "class":  # its methods are not followed: what it writes is only supposed
                hits += _writes(code, facts, target, depth + 1, why or CLASS)
            else:
                queue.append((target, depth + 1, why))
    return hits


def _writes(code: Code, facts: Facts, here: Definition, depth: int, reason: str) -> list[Hit]:
    """The last line of each kind of write inside the definition (`session.commit`, not `session.add`); a
    write signalled by a module the file imports (`import emails`) where the definition uses it."""
    start, end = here.node.lineno, here.node.end_lineno or here.node.lineno
    found: list[Hit] = []
    for signal in WRITES:
        claims = facts.signal(signal, {here.file})
        lines = [c.line_start for c in claims if start <= c.line_start <= end]
        lines = lines or [u for c in claims if (u := code.use_of_import(here.file, here.node, c.line_start))]
        if lines:
            at = max(lines)
            name = code.call_text(here.file, at) or signal
            found.append(Hit(here.file, at, name, "write", depth, bool(reason), signal, reason))
    return found


def _dependencies(code: Code, here: Definition) -> list[tuple[Definition, bool]]:
    """FastAPI's `Depends(f)`: in a parameter's annotation (or the alias it names), its default, or the
    route decorator's `dependencies=[...]`. One that only hands over a session is left out."""
    node = here.node
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return []
    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    exprs: list[ast.expr] = [a.annotation for a in args if a.annotation is not None]
    exprs += [d for d in node.args.defaults + node.args.kw_defaults if d is not None]
    exprs += [
        k.value
        for d in node.decorator_list
        if isinstance(d, ast.Call)
        for k in d.keywords
        if k.arg == "dependencies"
    ]
    found: list[tuple[Definition, bool]] = []
    for expr in exprs:
        for target in _depends(code, here.file, expr, hops=2):
            returns = (
                target.node.returns
                if isinstance(target.node, ast.FunctionDef | ast.AsyncFunctionDef)
                else None
            )
            if returns is not None and any(w in ast.unparse(returns) for w in CONNECTIONS):
                continue
            found.append((target, False))
    return found


def _depends(code: Code, file: str, expr: ast.expr, hops: int) -> list[Definition]:
    found: list[Definition] = []
    for node in ast.walk(expr):
        if isinstance(node, ast.Call) and _called(node.func) == "Depends" and node.args:
            first = node.args[0]
            target = code.define(file, first.id) if isinstance(first, ast.Name) else None
            if target is not None and isinstance(target.node, ast.FunctionDef | ast.AsyncFunctionDef):
                found.append(target)
        elif (
            isinstance(node, ast.Name) and hops > 0
        ):  # `CurrentUser`: an alias of `Annotated[User, Depends(f)]`
            alias = code.define(file, node.id)
            if alias is not None and isinstance(alias.node, ast.Assign | ast.AnnAssign) and alias.node.value:
                found += _depends(code, alias.file, alias.node.value, hops - 1)
    return found


def _calls(code: Code, here: Definition) -> list[tuple[Definition, bool]]:
    calls = sorted(  # in the order they run: `Database(p)[t].insert_all(r)` calls `Database` first
        (n for n in ast.walk(here.node) if isinstance(n, ast.Call)),
        key=lambda n: (n.end_lineno or n.lineno, n.end_col_offset or 0),
    )
    found: list[tuple[Definition, bool]] = []
    for call in calls:
        target = _target(code, here, call.func)
        if target is not None:
            found.append(target)
    return found


def _target(code: Code, here: Definition, func: ast.expr) -> tuple[Definition, bool] | None:
    if isinstance(func, ast.Name):
        target = code.define(here.file, func.id)
        return (target, False) if target is not None and _runs(target) else None
    if not isinstance(func, ast.Attribute):
        return None
    receiver = func.value
    if isinstance(receiver, ast.Name):
        if receiver.id in SELF and here.owner:
            target = code.method(here.file, here.owner, func.attr)
            return (target, False) if target is not None else None
        module = code.module(here.file, receiver.id)
        if module:
            target = next((t for f in module if (t := code.define(f, func.attr))), None)
            return (target, False) if target is not None and _runs(target) else None
        named = code.define(here.file, receiver.id)
        if named is not None and isinstance(named.node, ast.ClassDef):  # `Item.model_validate(…)`
            return named, False
        if named is not None:
            return None  # a known object of the project that is not a class: its type is not read
    target = code.unique_method(func.attr)
    return (target, True) if target is not None else None


def _runs(target: Definition) -> bool:
    return isinstance(target.node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)


def _called(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def _reads(node: ast.AST, tables: set[str]) -> str:
    """The table class a function fetches one row of: `session.get(User, token)` → « User »."""
    for call in (n for n in ast.walk(node) if isinstance(n, ast.Call) and n.args):
        first = call.args[0]
        if isinstance(first, ast.Name) and first.id in tables:
            return first.id
    return ""

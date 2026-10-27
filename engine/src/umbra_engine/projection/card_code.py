"""What the card reads in the code itself (#106): route decorators, router prefixes, the names a file
takes from another, return annotations. Python is read with `ast`; JavaScript routes with one pattern.
Every function here takes text already released by the Secret Guard and never raises on bad code."""

import ast
import re
from collections import Counter
from dataclasses import dataclass, field

VERBS = ("get", "post", "put", "patch", "delete")
JS_ROUTE = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"`]([^'\"`]+)")
ADMIN = re.compile(r"superuser|admin", re.IGNORECASE)
SIGNED_IN = re.compile(r"current_?user|superuser|admin|auth", re.IGNORECASE)
LOCAL = {"local", "dev", "development"}
NOT_A_MODEL = {"Any", "None", "dict", "list", "str", "int", "bool", "float", "bytes", "object"}


@dataclass
class RouteDef:
    verb: str  # « GET »
    path: str  # as written on the decorator: « /{id} »
    router: str  # the variable it hangs on: « router »
    name: str  # the function: « read_item »; empty for an inline JavaScript handler
    line: int  # the function's own line (or the route line when there is no function)
    answers: list[str] = field(default_factory=list)  # response models: « ItemPublic »
    takes: list[str] = field(default_factory=list)  # annotated parameters: « ItemCreate »
    raises: bool = False
    owned: bool = False  # keeps the caller's rows: `Item.owner_id == current_user.id`
    admin: bool = False  # behind a superuser or admin dependency: `Depends(get_current_active_superuser)`
    signed_in: bool = True  # takes the signed-in caller (`CurrentUser`), or an admin


@dataclass
class Mount:
    holder: str  # « api_router » in `api_router.include_router(items.router)`
    target: str  # « items.router »
    prefix: str  # the prefix as written: « "/x" » or « settings.API_V1_STR »; empty when none
    local: bool = False  # mounted only under `if settings.ENVIRONMENT == "local":`


def parse(text: str) -> ast.Module | None:
    try:
        return ast.parse(text)
    except (SyntaxError, ValueError):
        return None


def routes(text: str, python: bool) -> list[RouteDef]:
    if not python:
        found: list[RouteDef] = []
        for number, line in enumerate(text.split("\n"), 1):
            match = JS_ROUTE.search(line)
            if match:
                found.append(RouteDef(match[1].upper(), match[2], "", "", number))
        return found
    tree = parse(text)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            route = _route_of(decorator, node)
            if route:
                found.append(route)
    return sorted(found, key=lambda r: r.line)


def _route_of(decorator: ast.expr, node: ast.FunctionDef | ast.AsyncFunctionDef) -> RouteDef | None:
    if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)):
        return None
    verb = decorator.func.attr
    if verb not in VERBS or not isinstance(decorator.func.value, ast.Name):
        return None
    first = decorator.args[0] if decorator.args else None
    path = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else ""
    answers = [_name(k.value) for k in decorator.keywords if k.arg == "response_model"]
    if node.returns is not None and not answers:
        answers = [_name(node.returns)]
    takes = [_name(a.annotation) for a in node.args.args + node.args.kwonlyargs if a.annotation is not None]
    raises = any(isinstance(n, ast.Raise) for n in ast.walk(node))
    gates = _gates(decorator, node)
    return RouteDef(
        verb.upper(), path, decorator.func.value.id, node.name, node.lineno,
        [a for a in answers if a], [t for t in takes if t], raises, _owned(node),
        bool(ADMIN.search(gates)), bool(SIGNED_IN.search(gates)),
    )  # fmt: skip


def _gates(decorator: ast.Call, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """What a route asks of its caller, as written: its `dependencies=` and its parameters' types and
    defaults (`current_user: CurrentUser`, `Depends(get_current_active_superuser)`)."""
    written = [ast.unparse(k.value) for k in decorator.keywords if k.arg == "dependencies"]
    params = node.args.args + node.args.kwonlyargs
    written += [ast.unparse(a.annotation) for a in params if a.annotation is not None]
    written += [ast.unparse(d) for d in node.args.defaults + node.args.kw_defaults if d is not None]
    return " ".join(written)


def _owned(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body compares an `owner_id` with the `.id` of one of the function's parameters."""
    params = {a.arg for a in node.args.args + node.args.kwonlyargs}

    def side(e: ast.expr) -> str:
        if not isinstance(e, ast.Attribute):
            return ""
        if e.attr == "owner_id":
            return "owner"
        return "caller" if e.attr == "id" and isinstance(e.value, ast.Name) and e.value.id in params else ""

    return any(
        isinstance(n, ast.Compare) and len(n.comparators) == 1 and isinstance(n.ops[0], ast.Eq)
        and {side(n.left), side(n.comparators[0])} == {"owner", "caller"}
        for n in ast.walk(node)
    )  # fmt: skip


def _name(node: ast.expr) -> str:
    """`ItemPublic` → « ItemPublic »; `list[Item]` → « Item »; anything else → ""."""
    if isinstance(node, ast.Name):
        return "" if node.id in NOT_A_MODEL else node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):  # `-> "Table"`
        return node.value if node.value.isidentifier() and node.value not in NOT_A_MODEL else ""
    if isinstance(node, ast.Subscript):
        return _name(node.slice) if not isinstance(node.slice, ast.Tuple) else ""
    return ""


def router_prefixes(text: str) -> dict[str, str]:
    """`router = APIRouter(prefix="/items")` → {"router": "/items"}."""
    tree = parse(text)
    found: dict[str, str] = {}
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            prefix = _keyword(node.value, "prefix")
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(prefix, ast.Constant):
                    found[target.id] = str(prefix.value)
    return found


def mounts(text: str) -> list[Mount]:
    """`app.include_router(api_router, prefix=settings.API_V1_STR)`, as written."""
    tree = parse(text)
    found: list[Mount] = []
    local = {
        id(inner)
        for node in (ast.walk(tree) if tree else [])
        if isinstance(node, ast.If) and _local_only(node.test)
        for statement in node.body
        for inner in ast.walk(statement)
    }
    for node in ast.walk(tree) if tree else []:
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
            and isinstance(node.func.value, ast.Name)
            and node.args
        ):
            prefix = _keyword(node, "prefix")
            written = "" if prefix is None else ast.unparse(prefix)
            found.append(Mount(node.func.value.id, ast.unparse(node.args[0]), written, id(node) in local))
    return found


def _local_only(test: ast.expr) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.lower() in LOCAL
        for n in ast.walk(test)
    )


def constant(text: str, name: str) -> str | None:
    """The string a settings class gives `name`: `API_V1_STR: str = "/api/v1"` → « /api/v1 »."""
    tree = parse(text)
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == name and isinstance(value, ast.Constant):
            return str(value.value)
    return None


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def imported_names(text: str, start: int, end: int, python: bool) -> list[str]:
    """The names an import statement on lines `start..end` takes: `from app.models import Item, User`."""
    if not python:
        lines = "\n".join(text.split("\n")[start - 1 : end])
        braces = re.search(r"\{([^}]*)\}", lines)
        names = braces[1].split(",") if braces else []
        return [n.split(" as ")[0].strip() for n in names if n.strip()]
    tree = parse(text)
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, ast.ImportFrom) and node.lineno == start:
            return [a.name for a in node.names if a.name != "*"]
    return []


def return_types(text: str) -> Counter[str]:
    """How often each annotated return type comes back from the public functions and methods."""
    tree = parse(text)
    found: Counter[str] = Counter()
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            name = _name(node.returns) if node.returns is not None else ""
            if name:
                found[name] += 1
    return found

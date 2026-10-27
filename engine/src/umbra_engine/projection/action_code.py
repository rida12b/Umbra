"""The code an action's chain is read in (#107): each released Python file parsed once, the names it
imports joined to the files Umbra resolved them to (`imports_module`), its top-level definitions, and the
methods of the whole project by name (a guess only when one method alone has that name)."""

import ast
import posixpath
from collections.abc import Callable
from dataclasses import dataclass

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.card_code import parse
from umbra_engine.projection.system_around import TEST_FILE

TextOf = Callable[[str], str | None]
Node = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Assign | ast.AnnAssign
MAX_HOPS = 3
# Method names any object may have: a call `x.get()` is never taken for the project's one method `get`.
COMMON = (
    {n for t in (dict, list, str, set, bytes, object) for n in dir(t)}
    | {"add", "commit", "refresh", "exec", "execute", "query", "filter", "where", "all", "first", "one",
       "delete", "merge", "flush", "close", "open", "read", "write", "run", "send", "save", "load"}
)  # fmt: skip


@dataclass
class Definition:
    file: str
    node: Node
    owner: str = ""  # the class a method belongs to


@dataclass
class Ref:
    module: bool  # `import x` / `from app import crud`: a module; else one name of the target files
    files: list[str]
    name: str = ""


class Code:
    def __init__(self, text_of: TextOf, module_links: list[StoredClaim], methods: list[StoredClaim]) -> None:
        self._text_of = text_of
        self._trees: dict[str, ast.Module | None] = {}
        self._scopes: dict[str, dict[str, Ref]] = {}
        self._targets: dict[tuple[str, int], list[str]] = {}
        for claim in module_links:
            for line in range(claim.line_start, claim.line_end + 1):
                self._targets.setdefault((claim.subject, line), []).append(claim.object)
        self._methods: dict[str, list[tuple[str, str]]] = {}
        for claim in methods:
            file, _, qualified = claim.object.partition("::")
            owner, _, name = qualified.split("~", 1)[0].rpartition(".")
            if owner and "." not in owner and not TEST_FILE.search(file):
                self._methods.setdefault(name, []).append((file, owner))

    def tree(self, file: str) -> ast.Module | None:
        if file not in self._trees:
            self._trees[file] = parse(self._text_of(file) or "") if file.endswith(".py") else None
        return self._trees[file]

    def function_at(self, file: str, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        tree = self.tree(file)
        nodes = ast.walk(tree) if tree else iter(())
        return next(
            (n for n in nodes if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.lineno == line),
            None,
        )

    def class_of(self, file: str, node: ast.AST) -> str:
        tree = self.tree(file)
        for top in tree.body if tree else []:
            if isinstance(top, ast.ClassDef) and node in top.body:
                return top.name
        return ""

    def call_text(self, file: str, line: int) -> str:
        """« session.commit » for the call on that line."""
        tree = self.tree(file)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.lineno == line] if tree else []
        return ast.unparse(min(calls, key=lambda n: n.col_offset).func) if calls else ""

    def use_of_import(self, file: str, node: ast.AST, line: int) -> int | None:
        """The first line of `node` that uses a name the import on `line` binds (`emails.Message(…)`)."""
        tree = self.tree(file)
        bound = {
            alias.asname or alias.name.split(".")[0]
            for top in (tree.body if tree else [])
            if isinstance(top, ast.Import | ast.ImportFrom) and top.lineno == line
            for alias in top.names
        }
        uses = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Name) and n.id in bound]
        return min(uses) if uses else None

    def scope(self, file: str) -> dict[str, Ref]:
        """What each imported name of the file stands for."""
        if file in self._scopes:
            return self._scopes[file]
        found: dict[str, Ref] = {}
        tree = self.tree(file)
        for node in ast.walk(tree) if tree else []:
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            targets = [t for t in self._targets.get((file, node.lineno), []) if t.endswith(".py")]
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if isinstance(node, ast.Import):
                    found[local] = Ref(True, targets)
                    continue
                modules = [t for t in targets if _stem(t) == alias.name]
                found[local] = Ref(True, modules) if modules else Ref(False, targets, alias.name)
        self._scopes[file] = found
        return found

    def module(self, file: str, name: str) -> list[str]:
        ref = self.scope(file).get(name)
        return ref.files if ref is not None and ref.module else []

    def define(self, file: str, name: str, hops: int = MAX_HOPS) -> Definition | None:
        """The top-level function, class or assignment `name` in `file`, or where the file imports it from."""
        tree = self.tree(file)
        for node in tree.body if tree else []:
            if isinstance(node, Node) and _names(node, name):
                return Definition(file, node)
        ref = self.scope(file).get(name)
        if ref is None or ref.module or hops <= 0:
            return None
        return next((d for f in ref.files if f != file and (d := self.define(f, ref.name, hops - 1))), None)

    def method(self, file: str, owner: str, name: str) -> Definition | None:
        tree = self.tree(file)
        for top in tree.body if tree else []:
            if isinstance(top, ast.ClassDef) and top.name == owner:
                for node in top.body:
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
                        return Definition(file, node, owner)
        return None

    def unique_method(self, name: str) -> Definition | None:
        """The one method of the project with this name; none when it is common or defined twice."""
        found = self._methods.get(name, [])
        if name in COMMON or name.startswith("__") or len(found) != 1:
            return None
        file, owner = found[0]
        return self.method(file, owner, name)


def _names(node: ast.stmt, name: str) -> bool:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.name == name
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name


def _stem(path: str) -> str:
    stem = posixpath.splitext(posixpath.basename(path))[0]
    return posixpath.basename(posixpath.dirname(path)) if stem == "__init__" else stem

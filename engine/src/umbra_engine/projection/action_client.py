"""Who sends a route's request on the client side (#107): the line of the web app that names the exact
address with the same verb (`url: '/api/v1/items/'` beside `method: 'POST'`), the function it sits in,
and the first place that calls that function (the form). Read as text, never run; nothing found, nothing
said."""

import posixpath
import re
from collections.abc import Callable
from dataclasses import dataclass

from umbra_engine.projection.system_around import TEST_FILE

TextOf = Callable[[str], str | None]
SCRIPTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte")
NEAR = 4  # lines around the address where its verb is written
UP = 15  # lines above the address where the function holding it starts
METHOD = re.compile(r"""\bmethod\s*:\s*["'`](\w+)["'`]""", re.IGNORECASE)
FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:public\s+|private\s+)?(?:static\s+)?(?:async\s+)?(?:function\s+)?"
    r"(?:const\s+|let\s+)?(?P<name>[A-Za-z_$][\w$]*)\s*(?:=\s*(?:async\s*)?\(|\(|:\s*\()"
)
FORM = re.compile(r"<form[\s>]|[^\w$]onSubmit[^\w$]")
NOT_NAMES = {"if", "for", "while", "switch", "return", "catch", "function"}


@dataclass
class ClientCall:
    file: str  # « frontend/src/client/sdk.gen.ts »
    line: int  # the function holding the address (« createItem »), or the address itself
    name: str  # « createItem »; empty when the address is not inside a named function
    caller: tuple[str, int] | None  # the first place that calls it: (« …/AddItem.tsx », 57)
    form: bool = False  # that place is a form (`<form`, `onSubmit`): « le formulaire envoie »


def client_call(files: list[str], text_of: TextOf, verb: str, address: str) -> ClientCall | None:
    """`files`: the web app's. The generated client (sdk, client/) is read first."""
    wanted = re.compile(r"""(["'`])""" + re.escape(address) + r"\1")
    scripts = sorted(
        (f for f in files if f.endswith(SCRIPTS) and not TEST_FILE.search(f)),
        key=lambda f: ("sdk" not in f and "/client/" not in f, f),
    )
    for file in scripts:
        lines = (text_of(file) or "").split("\n")
        for at, line in enumerate(lines):
            if not wanted.search(line):
                continue
            near = "\n".join(lines[max(0, at - NEAR) : at + NEAR + 1])
            verbs = {m.upper() for m in METHOD.findall(near)}
            if verbs and verb not in verbs:
                continue
            name, start = _holder(lines, at)
            caller = _caller(scripts, text_of, file, name) if name else None
            form = caller is not None and bool(FORM.search(text_of(caller[0]) or ""))
            return ClientCall(file, start + 1, name, caller, form)
    return None


def _holder(lines: list[str], at: int) -> tuple[str, int]:
    for row in range(at, max(-1, at - UP), -1):
        match = FUNCTION.match(lines[row])
        if match and match["name"] not in NOT_NAMES:
            return match["name"], row
    return "", at


def _caller(scripts: list[str], text_of: TextOf, file: str, name: str) -> tuple[str, int] | None:
    called = re.compile(rf"(?<![\w$]){re.escape(name)}\s*\(")
    for other in (f for f in scripts if f != file and not posixpath.basename(f).startswith("index.")):
        for number, line in enumerate((text_of(other) or "").split("\n"), 1):
            if called.search(line) and not line.lstrip().startswith(("//", "*", "/*")):
                return other, number
    return None

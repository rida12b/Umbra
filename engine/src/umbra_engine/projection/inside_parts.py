"""How one box of the map is cut into parts (Level 1, #105), from hard signals only (no LLM).

Each rule takes the files it recognises among those still free, in a fixed order per kind of box: a
server is cut into its entry, routes, access control, models and data access; a web app into its start,
pages, client, sign-in and screens; anything else into its entry, its data access, its extensions, then
one part per top file or folder. Tests, migrations, settings and a UI kit go « autour »."""

import posixpath
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from umbra_engine.claims import StoredClaim
from umbra_engine.projection.system_around import MIGRATIONS, TEST_FILE
from umbra_engine.projection.system_facts import Facts, under
from umbra_engine.projection.system_units import CODE, Unit

PAGE_DIRS = {"routes", "pages"}
CLIENT_DIRS = {"client", "api", "services"}
SCREEN_DIRS = {"components", "features", "screens", "views", "widgets"}
UI_KIT_DIRS = {"ui"}  # under a screens folder: shared buttons and fields, not screens
SIGNALS_OF = {
    "server": (
        ("entry", ("web-server:",)), ("routes", ("route", "mount")), ("mail", ("smtp",)),
        ("access", ("auth",)), ("models", ("table:", "tablename:")), ("data", ("db-write", "sqlite")),
    ),
    "web": (("entry", ("ui-render",)), ("pages", ("routing",)), ("client", ()), ("session", ("token-store",)),
            ("screens", ())),
    "other": (("entry", ()), ("data", ("db-write", "sqlite")), ("models", ("table:", "tablename:")),
              ("plugins", ("plugins",))),
}  # fmt: skip


@dataclass
class Group:
    kind: str
    files: set[str]
    claims: list[StoredClaim]  # the lines that made it this part, in file then line order
    chips: list[str] = field(default_factory=list)  # files shown as chips (route files)


@dataclass
class Cut:
    root: str  # the folder every part sits in (« backend/app »; "" = the Project root)
    groups: list[Group]
    hidden: set[str]  # files no part holds but whose work is drawn: a mail helper, sent by its callers
    around: dict[str, list[str]]  # « settings », « migrations », « tests », « ui-kit », « more:<title> »


def cut(facts: Facts, unit: Unit, folder: str) -> Cut:
    scope = folder.rstrip("/") if folder.endswith("/") else unit.root
    files = sorted(f for f in unit.files if under(scope, f))
    around: dict[str, list[str]] = {}
    for key, test in (("tests", TEST_FILE.search), ("migrations", MIGRATIONS.search)):
        found = [f for f in files if test(f)]
        if found:
            around[key] = found
    free = {f for f in files if f.endswith(CODE) and not any(f in v for v in around.values())}
    settings = sorted(c.file for c in facts.signal("settings") if c.file in free)
    if settings:
        around["settings"] = settings
        free -= set(settings)
    groups: list[Group] = []
    hidden: set[str] = set()
    kind = unit.role if unit.role in ("server", "web") else "other"
    for part, signals in SIGNALS_OF[kind]:
        group = _rule(facts, unit, part, signals, free)
        if group is None:
            continue
        free -= group.files
        if part == "mail":
            hidden |= group.files
        else:
            groups.append(group)
    kit = [f for f in files if _in_dir(f, SCREEN_DIRS) and _in_dir(f, UI_KIT_DIRS)]
    if kit:
        around["ui-kit"] = kit
    if kind == "other" or len(groups) < 2:
        groups += _by_folder(facts, free, scope)
    return Cut(_common([f for g in groups for f in g.files]), groups, hidden, around)


def _rule(facts: Facts, unit: Unit, part: str, signals: tuple[str, ...], free: set[str]) -> Group | None:
    claims = [c for s in signals for c in facts.signals_starting(s, free)]
    if part == "entry" and not signals:  # a library: what it exports; a command: its own file
        claims = [c for c in unit.proofs if c.file in free and "script:" not in c.object]
        top = min((c.file.count("/") for c in claims), default=0)
        claims = [c for c in claims if c.file.count("/") == top]
    files = {c.file for c in claims}
    picks: dict[str, Callable[[str], bool]] = {
        "pages": lambda f: _in_dir(f, PAGE_DIRS),
        "client": lambda f: _in_dir(f, CLIENT_DIRS),
        "screens": lambda f: _in_dir(f, SCREEN_DIRS) and not _in_dir(f, UI_KIT_DIRS),
    }
    if part in picks:
        files |= {f for f in free if picks[part](f)}
    if part == "routes":  # a file that only hangs routes on the app (`api/main.py`) goes with them
        chips = sorted({c.file for c in claims if c.object == "signal:route"})
        return Group(part, files, _ordered(claims), chips) if chips else None
    return Group(part, files, _ordered(claims)) if files else None


def _by_folder(facts: Facts, free: set[str], root: str) -> list[Group]:
    """One part per top file or folder left, the biggest first (by the last line of what they define)."""
    tops: dict[str, set[str]] = {}
    for f in sorted(free):
        rest = f[len(root) + 1 :] if root else f
        key = rest.split("/", 1)[0]
        if posixpath.basename(f) == "__init__.py" and "/" not in rest:
            continue  # a package's own marker file: nothing to show on its own
        tops.setdefault(key, set()).add(f)
    size = _sizes(facts)
    ranked = sorted(tops.items(), key=lambda kv: (-sum(size.get(f, 0) for f in kv[1]), kv[0]))
    return [Group(f"code:{key}", group, []) for key, group in ranked]


def _sizes(facts: Facts) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for claim in facts.classes + facts.functions:
        sizes[claim.file] = max(sizes.get(claim.file, 0), claim.line_end)
    return sizes


def _ordered(claims: list[StoredClaim]) -> list[StoredClaim]:
    return sorted(claims, key=lambda c: (c.file, c.line_start))


def _in_dir(path: str, names: set[str]) -> bool:
    return any(part.lower() in names for part in path.split("/")[:-1])


def _common(files: list[str]) -> str:
    folders = [posixpath.dirname(f) for f in files]
    if not folders:
        return ""
    return posixpath.commonpath(folders) if all(folders) else ""


def is_generated(path: str) -> bool:
    return bool(re.search(r"\.gen\.|/generated/", path))

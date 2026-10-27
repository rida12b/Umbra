"""The routes of a file on its card (#106): each one's full address (router prefixes and the prefixes it
is mounted under, read in the code), and its plain French words (`route_words`)."""

import ast
import posixpath
import re
from collections.abc import Callable

from umbra_engine.projection import route_words
from umbra_engine.projection.card_code import RouteDef, constant, mounts, router_prefixes, routes
from umbra_engine.projection.system_facts import Facts

TextOf = Callable[[str], str | None]
Route = tuple[str, RouteDef, str, str]  # file, route, full address, plain words
MAX_HOPS = 4
SUFFIXES = ("Public", "Out", "Response", "Read", "Schema")
ORDER = ("GET", "POST", "PUT", "PATCH", "DELETE")
DOES = {
    "Lister": "lister",
    "Voir": "voir",
    "Créer": "créer",
    "Modifier": "modifier",
    "Supprimer": "supprimer",
}


def action_id(file: str, line: int) -> str:
    """An action of « Ce qu'on peut faire » (#107): the file and line of the function that does it."""
    return f"{file}:{line}"


def read_routes(facts: Facts, unit_files: set[str], files: list[str], text_of: TextOf) -> list[Route]:
    """The routes of `files`, each with its full address and plain words (card, « Ce qu'on peut faire »)."""
    mount_files = sorted({c.file for c in facts.signal("mount", unit_files)})
    settings = sorted({c.file for c in facts.signal("settings")})
    found: list[Route] = []
    for file in files:
        python = file.endswith(".py")
        for route in routes(text_of(file) or "", python):
            prefix = full_prefix(file, route.router, text_of, mount_files, settings) if python else ""
            full = address(prefix, route.path)
            found.append(
                (file, route, full, label(route.verb, full, route.owned, route.admin, route.signed_in))
            )
    return found


def full_prefix(file: str, router: str, text_of: TextOf, mount_files: list[str], settings: list[str]) -> str:
    """« /api/v1/items »: the router's own prefix, then each prefix it is mounted under, up to the app."""
    text = text_of(file) or ""
    parts = [router_prefixes(text).get(router, "")]
    wanted = {f"{_stem(file)}.{router}"}
    for _ in range(MAX_HOPS):
        found = next(
            ((m, f) for f in mount_files for m in mounts(text_of(f) or "") if m.target in wanted), None
        )
        if found is None:
            break
        mount, holder_file = found
        parts.append(_resolve(mount.prefix, text_of, settings))
        parts.append(router_prefixes(text_of(holder_file) or "").get(mount.holder, ""))
        wanted = {mount.holder, f"{_stem(holder_file)}.{mount.holder}"}
    return "".join(reversed([p.rstrip("/") for p in parts if p]))


def _resolve(written: str, text_of: TextOf, settings: list[str]) -> str:
    """`"/x"` as it is; `settings.API_V1_STR` from the settings class; anything else is not resolved."""
    if not written:
        return ""
    try:
        value = ast.literal_eval(written)
        return value if isinstance(value, str) else ""
    except (ValueError, SyntaxError):
        pass
    name = written.rsplit(".", 1)[-1]
    return next((v for f in settings if (v := constant(text_of(f) or "", name)) is not None), "")


def address(prefix: str, path: str) -> str:
    joined = f"{prefix}/{path.lstrip('/')}" if path else prefix + "/"
    return re.sub(r"/{2,}", "/", joined if joined.startswith("/") else "/" + joined)


def common_address(addresses: list[str]) -> str:
    """« /api/v1/items/ » for « /api/v1/items/ » and « /api/v1/items/{id} »."""
    if not addresses:
        return ""
    common = posixpath.commonprefix(addresses)
    return common if common.endswith("/") else common.rsplit("/", 1)[0] + "/"


def label(verb: str, full: str, owned: bool = False, admin: bool = False, signed_in: bool = True) -> str:
    """French words for a route (`route_words`); « » when no rule names it (Claude names those, #108)."""
    return route_words.label(verb, full, owned, admin, signed_in)


def sentence(rows: list[tuple[RouteDef, str, str]]) -> str:
    """« Les adresses pour lister, voir, créer, modifier et supprimer ses items. » when every route has
    plain words on the same things (« ses » when the list is the caller's own); else how many addresses
    and under which one."""
    things = {full.strip("/").split("/")[-1] if not full.endswith("}") else full.split("/")[-2]
              for _, full, _ in rows}  # fmt: skip
    words = list(dict.fromkeys(DOES.get(w.split(" ")[0], "") for _, _, w in rows if w))
    if rows and all(w for _, _, w in rows) and len(things) == 1 and all(words):
        listed = ", ".join(words[:-1]) + f" et {words[-1]}" if len(words) > 1 else words[0]
        whose = "ses" if any(w.startswith("Lister ses ") for _, _, w in rows) else "les"
        return f"Les adresses pour {listed} {whose} {things.pop()}."
    count = len(rows)
    under = common_address([full for _, full, _ in rows])
    return f"{count} adresse{'s' if count > 1 else ''} du serveur, sous {under}."


def answer_words(models: list[str], known: set[str], error: bool) -> str:
    """`ItemPublic`, `ItemsPublic`, `Message` + a raise → « un item, une liste d'items, un message, ou une
    erreur ». A name ending in « s » is a list only when the same name without it is a model too."""
    bases = {_base(m).lower() for m in known}
    named = [_base(m).lower() for m in dict.fromkeys(models)]
    lists = {b for b in named if b.endswith("s") and b[:-1] in bases}
    words: list[str] = []
    for base in (b for b in named if b not in lists):
        words.append(_a(base))
        if f"{base}s" in lists:  # the list right after the one: « un item, une liste d'items »
            words.append(f"une liste {_of(base + 's')}")
    words += [f"une liste {_of(b)}" for b in named if b in lists and b[:-1] not in named]
    words = list(dict.fromkeys(words))
    if error:
        words.append("ou une erreur")
    return ", ".join(words)


def _base(model: str) -> str:
    return next((model[: -len(s)] for s in SUFFIXES if model.endswith(s) and len(model) > len(s)), model)


def _a(word: str) -> str:
    return f"un {word}"


def _of(word: str) -> str:
    return f"d'{word}" if word[:1] in "aeioh" else f"de {word}"


def _stem(path: str) -> str:
    return posixpath.splitext(posixpath.basename(path))[0]

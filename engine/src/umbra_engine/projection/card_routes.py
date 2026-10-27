"""The routes of a file on its card (#106): each one's full address (router prefixes and the prefixes it
is mounted under, read in the code), and plain French words only where the shape says it all: a GET on
a collection lists, a GET on `{id}` shows, a POST creates, a PUT or PATCH changes, a DELETE removes."""

import ast
import posixpath
import re
from collections.abc import Callable

from umbra_engine.projection.card_code import RouteDef, constant, mounts, router_prefixes

TextOf = Callable[[str], str | None]
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


def label(verb: str, full: str) -> str:
    """French words for a plain shape only; « » for anything else (Claude names those, #108)."""
    segments = [s for s in full.split("/") if s]
    one = bool(segments) and segments[-1].startswith("{")
    statics = [s for s in segments if not s.startswith("{")]
    if not statics or (one and len(segments) < 2) or (one and segments[-2].startswith("{")):
        return ""
    many = statics[-1]
    if one and segments[-2] != many or not re.fullmatch(r"[a-z]+s", many):
        return ""
    single = many[:-1]
    shapes = {
        ("GET", False): f"Lister les {many}", ("GET", True): f"Voir {_a(single)}",
        ("POST", False): f"Créer {_a(single)}", ("PUT", True): f"Modifier {_a(single)}",
        ("PATCH", True): f"Modifier {_a(single)}", ("DELETE", True): f"Supprimer {_a(single)}",
    }  # fmt: skip
    return shapes.get((verb, one), "")


def sentence(rows: list[tuple[RouteDef, str, str]]) -> str:
    """« Les adresses pour lister, voir, créer, modifier et supprimer les items. » when every route has
    plain words on the same things; else how many addresses and under which one."""
    things = {full.strip("/").split("/")[-1] if not full.endswith("}") else full.split("/")[-2]
              for _, full, _ in rows}  # fmt: skip
    words = list(dict.fromkeys(DOES[w.split(" ")[0]] for _, _, w in rows if w))
    if rows and all(w for _, _, w in rows) and len(things) == 1:
        listed = ", ".join(words[:-1]) + f" et {words[-1]}" if len(words) > 1 else words[0]
        return f"Les adresses pour {listed} les {things.pop()}."
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

"""The settings a study names, checked word for word against the code it cites (#78).

Claude says « the header name is X-Tenant-ID, tenant_auth.py line 33 ». Umbra checks it in the text the
Secret Guard released (never the Project folder): the cited lines exist, are few, and hold that exact
code. A wide citation, a one-character code or a masked secret proves nothing, so it never passes.
"""

import re

MAX_SPAN = 15  # cited lines: more than this holds almost any code
_PUNCTUATION = re.compile(r"[\W_]+")
_SECRET_NAME = re.compile(r"key|secret|token|passw|credential|dsn|auth", re.IGNORECASE)
_MASK = re.compile(r"\*{4,}")
_URL_WITH_USER = re.compile(r"://[^/\s:@]+:[^/\s@]+@")


def collapse(text: str) -> str:
    return " ".join(text.split())


def cited_lines(row: dict, texts: dict[str, str]) -> tuple[str | None, list[int] | None, str | None]:
    """The row's file and lines when they fit the released text, and that text (spaces collapsed)."""
    file = row.get("fichier") if isinstance(row.get("fichier"), str) else None
    file = file.strip().removeprefix("./") if file else None
    lines = row.get("lignes")
    if not (isinstance(lines, list) and len(lines) == 2 and all(isinstance(n, int) for n in lines)):
        return file, None, None
    start, end = lines
    text = texts.get(file) if file else None
    if text is None or not 1 <= start <= end or end - start + 1 > MAX_SPAN:
        return file, lines, None
    numbered = text.splitlines()
    if end > len(numbered):
        return file, lines, None
    return file, lines, collapse(" ".join(numbered[start - 1 : end]))


def literal(code: object, cited: str | None) -> bool:
    if not isinstance(code, str) or cited is None:
        return False
    wanted = collapse(code)
    if len(wanted) < 2 or not _PUNCTUATION.sub("", wanted):
        return False
    return wanted in cited


def checked_setting(row: dict, texts: dict[str, str]) -> dict:
    """The citation and the two verdicts, always computed again: a `verifie` in the answer is ignored.
    The value is kept only when the cited lines show it and it is not a secret: Umbra stores the
    model, so a key or a password must never reach it, even one the guard missed or Claude guessed."""
    file, lines, cited = cited_lines(row, texts)
    value: str = row["valeur"] if isinstance(row.get("valeur"), str) else ""
    seen = bool(value) and literal(value, cited)
    names = " ".join(str(row.get(k, "")) for k in ("nom", "code"))
    secret = bool(_SECRET_NAME.search(names) or _URL_WITH_USER.search(value) or _MASK.search(cited or ""))
    return {
        "fichier": file,
        "lignes": lines,
        "verifie": literal(row.get("code"), cited),
        "valeur": value if seen and not secret else "",
        "valeur_vue": seen,
    }


def read_by_code(code: str, file: str | None, line: str | None, texts: dict[str, str]) -> bool:
    """A project setting (« APP_PORT=8000 » in .env.example) counts as read only when its line is not
    commented out and its name appears in some other released file."""
    if line is not None and line.lstrip().startswith("#"):
        return False
    name = re.split(r"[=:\s]", code.strip(), maxsplit=1)[0].lower()
    if len(name) < 2:
        return False
    return any(name in text.lower() for path, text in texts.items() if path != file)


def cut(text: object, limit: int) -> str:
    """At most `limit` characters, cut after a whole word, « … » when something was cut."""
    text = text if isinstance(text, str) else ""
    if len(text) <= limit:
        return text
    head = text[: limit - 1]
    if " " in head and not text[limit - 1].isspace():
        head = head[: head.rindex(" ")]
    return head.rstrip() + "…"

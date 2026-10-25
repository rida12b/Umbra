"""The settings a study names, checked word for word against the code it cites (#78).

Claude says « the header name is X-Tenant-ID, tenant_auth.py line 33 ». Umbra checks it in the text the
Secret Guard released (never the Project folder): the cited lines exist, are few, and hold that exact
code. A wide citation, a one-character code or a masked secret proves nothing, so it never passes.
"""

import re

MAX_SPAN = 15  # cited lines: more than this holds almost any code
_PUNCTUATION = re.compile(r"[\W_]+")
# A setting is a secret when one WORD of its name says so (« DB_PASS », « apiKey », « Mot de passe »),
# not when a word merely contains one (« MAX_TOKENS », « AUTHOR_NAME », « KEYBOARD_LAYOUT »).
_SECRET_WORDS = {
    "pass", "passe", "passwd", "password", "pwd", "secret", "secrets", "key", "keys", "apikey", "token",
    "tokens", "credential", "credentials", "creds", "dsn", "auth", "jwt", "private", "salt", "cookie",
}  # fmt: skip
_COUNTED = {"max", "num", "limit", "total", "prompt", "completion", "input", "output"}  # « MAX_TOKENS »: a number
_WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")
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
    code: str = row["code"] if isinstance(row.get("code"), str) else ""
    secret = is_secret(f"{row.get('nom', '')} {code}") or bool(_URL_WITH_USER.search(value) or _MASK.search(cited or ""))
    return {
        "fichier": file,
        "lignes": lines,
        "verifie": literal(code, cited),  # on the line as written, before the value is cut out
        "code": name_only(code) if secret else code,
        "valeur": value if seen and not secret else "",
        "valeur_vue": seen,
    }


def is_secret(names: str) -> bool:
    words = [w.lower() for w in _WORD.findall(names)]
    return any(w in _SECRET_WORDS and not (w.startswith("token") and i and words[i - 1] in _COUNTED) for i, w in enumerate(words))


def name_only(code: str) -> str:
    """« APP_KEY=base64… » → « APP_KEY »; a URL keeps no user:password part."""
    name = re.split(r"\s*[=:]\s*", code.strip(), maxsplit=1)[0]
    return _URL_WITH_USER.sub("://", name)


def safe_code(code: str) -> str:
    return name_only(code) if is_secret(code) else code


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

"""What an import statement names, per language family.

Only languages with an explicit rule produce import Facts; a statement that no rule understands
produces nothing (the file's analyzer coverage says so) rather than a guessed target.
"""

import re

_QUOTED = re.compile(r"""["'`]([^"'`\s]+)["'`]""")
_JS = re.compile(
    r"""\bfrom\s*["']([^"']+)["']"""  # import ... from "m" / export ... from "m"
    r"""|^\s*import\s*["']([^"']+)["']"""  # import "m"
    r"""|\b(?:require|import)\s*\(\s*["']([^"']+)["']\s*\)""",  # require("m") / import("m")
    re.MULTILINE,
)
_PY_FROM = re.compile(r"^\s*from\s+(\.*[\w.]*)\s+import\b")
_PY_FROM_NAMES = re.compile(r"^\s*from\s+(\.*[\w.]*)\s+import\s+(.+)$", re.DOTALL)
_MODULE_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
_PY_IMPORT = re.compile(r"^\s*import\s+(.+)$", re.DOTALL)
_JAVA = re.compile(r"^\s*import\s+(?:static\s+)?(\w+(?:\.\w+)*(?:\.\*)?)\s*;?")
_CSHARP = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;")
_RUST = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?use\s+((?:::)?[\w]+(?:::[\w]+)*)")
_ELIXIR = re.compile(r"^\s*(?:alias|import|use|require)\s+([A-Z][\w.]*?)(?:\.\{([^}]*)\})?(?:\s|,|$)")
_PHP = re.compile(r"^\s*use\s+(?:function\s+|const\s+)?\\?([\w\\]+)")
_C_INCLUDE = re.compile(r"""^\s*#\s*include\s*[<"]([^>"]+)[>"]""")
_RUBY = re.compile(r"""^\s*(?:require|require_relative|load)\s*\(?\s*["']([^"']+)["']""")

JS_LIKE = {"javascript", "typescript", "tsx", "jsx"}
RULE_LANGUAGES = JS_LIKE | {
    "python", "go", "java", "kotlin", "scala", "csharp", "rust", "elixir", "php", "c", "cpp", "ruby",
}  # fmt: skip


def has_import_rule(language: str) -> bool:
    return language in RULE_LANGUAGES


def import_targets(language: str, statement: str) -> list[str]:
    """Targets named by one import statement, in order, without duplicates."""
    return list(dict.fromkeys(target for target in _targets(language, statement) if target))


def _targets(language: str, statement: str) -> list[str]:
    if language in JS_LIKE:
        return [next(group for group in match.groups() if group) for match in _JS.finditer(statement)]
    if language == "python":
        return _python(statement)
    if language == "go":
        return _QUOTED.findall(statement)
    if language in {"java", "kotlin", "scala"}:
        return _first(_JAVA, re.sub(r"\s*\.\s*", ".", statement))
    if language == "csharp":
        return _first(_CSHARP, statement)
    if language == "rust":
        return _first(_RUST, statement)
    if language == "elixir":
        return _elixir(statement)
    if language == "php":
        return _first(_PHP, statement)
    if language in {"c", "cpp"}:
        return _first(_C_INCLUDE, statement)
    if language == "ruby":
        return _first(_RUBY, statement)
    return []


def imported_names(language: str, statement: str) -> list[str]:
    """`from app import crud, User` → `app.crud`: a lower-case name taken from a package may be one of
    its modules. Only a guess (a function is lower-case too): the linker keeps the ones that are files."""
    if language != "python":
        return []
    from_import = _PY_FROM_NAMES.match(statement)
    if from_import is None:
        return []
    module, names = from_import.group(1), from_import.group(2)
    names = names.replace("(", " ").replace(")", " ").replace("\\", " ")
    found = [part.split(" as ")[0].strip() for part in names.split(",")]
    joined = module if module.endswith(".") else f"{module}."
    return [f"{joined}{name}" for name in found if _MODULE_NAME.match(name)]


def _python(statement: str) -> list[str]:
    from_import = _PY_FROM.match(statement)
    if from_import:
        return [from_import.group(1)]
    plain = _PY_IMPORT.match(statement)
    if plain is None:
        return []
    names = plain.group(1).replace("(", " ").replace(")", " ").replace("\\", " ")
    return [part.split(" as ")[0].strip() for part in names.split(",") if part.strip()]


def _elixir(statement: str) -> list[str]:
    """`alias Shop.{Order, User}` names Shop.Order and Shop.User."""
    match = _ELIXIR.match(statement)
    if match is None:
        return []
    base, group = match.group(1), match.group(2)
    if group is None:
        return [base]
    return [f"{base}.{name.strip()}" for name in group.split(",") if name.strip()]


def _first(pattern: re.Pattern[str], statement: str) -> list[str]:
    match = pattern.match(statement)
    return [match.group(1)] if match else []

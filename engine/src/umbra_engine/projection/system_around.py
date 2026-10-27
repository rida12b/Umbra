"""What sits around the running parts and does not make the app run: tests, CI, docs, admin tools,
start-up jobs, a project generator. Folded into one « + N autour » item on the Level 0 map."""

import posixpath
import re

from umbra_engine.projection.system_facts import ComposeService, Facts
from umbra_engine.projection.system_model import AroundItem, Proof, proof_of
from umbra_engine.projection.system_units import test_service

DB_ADMIN = ("adminer", "phpmyadmin", "pgadmin")
PROXIES = ("traefik", "nginx-proxy", "caddy", "haproxy", "envoy")  # routing only: neither a box nor a tool
CI = re.compile(
    r"^(?:\.github/workflows/.+\.ya?ml|\.gitlab-ci\.yml|\.circleci/.+|azure-pipelines\.yml|Jenkinsfile)$"
)
TEST_FILE = re.compile(
    r"(?:^|/)(?:tests?|__tests__|e2e|spec)/|(?:^|/)test_[^/]+\.py$|\.(?:test|spec)\.[jt]sx?$"
    r"|(?:^|/)(?:playwright|cypress|vitest|jest)\.config\.[cm]?[jt]s$"
)
DOCS = re.compile(r"^(?:docs?/.+|[^/]+\.(?:md|rst))$", re.IGNORECASE)
GENERATORS = ("copier.yml", "copier.yaml", "cookiecutter.json")
NOT_DOCS = {"license.md", "security.md", "code_of_conduct.md"}
DOC_SITE = {"conf.py", "index.rst", "index.md"}
GUIDES = (  # root guides, by what they teach, in reading order
    ("installer", r"^(?:readme|install)"),
    ("développer", r"^(?:development|develop|contributing|hacking)"),
    ("mettre en ligne", r"^(?:deployment|deploy)"),
)
CI_KINDS = (("tests", r"test|lint|check"), ("mise en ligne", r"deploy"), ("publication", r"publish|release"))
MIGRATIONS = re.compile(r"(?:^|/)(?:alembic(?:\.ini|/)|migrations/)")
MAX_PROOFS = 5


def image_name(service: ComposeService) -> str:
    """`schickling/mailcatcher:latest` → `mailcatcher`."""
    return service.image.split("@", 1)[0].rsplit("/", 1)[-1].split(":", 1)[0].lower()


def around_items(
    facts: Facts,
    prestart: list[str],
    extra: list[tuple[str, str, list[Proof]]],
    roles: set[str],
    commands: int,
) -> list[AroundItem]:
    """In a fixed order, each with what it is for in plain words. `prestart`: compose services that
    prepare the app before it starts. `extra`: services that fit no box, as (title, detail, proofs).
    `roles`: the running parts found (« server », « web », « cli »…); `commands`: what a CLI offers."""
    items: list[AroundItem] = []
    sentry = facts.signal("sentry")
    if sentry:
        guarded = facts.signal("sentry-if-key")
        detail = "Sentry, seulement si une clé est réglée" if guarded else "Sentry"
        proofs = [proof_of(c) for c in guarded + sentry]
        items.append(_item("sentry", "Suivi des erreurs", "", detail, proofs))
    services = list(facts.services.values())
    starting = [facts.services[name] for name in prestart]
    if starting:
        proofs = [proof_of(c) for s in starting for c in s.declared[:1]]
        items.append(_item("prestart", "Préparation au démarrage", "", _prestart(facts), proofs))
    sizes: dict[str, int] = {}  # the items named in the chip, by their number of files
    tests = _tests(facts, services, roles, commands)
    if tests:
        items.append(tests[0])
        sizes["tests"] = tests[1]
    ci = [f for f in facts.files if CI.match(f)]
    if ci:
        items.append(_item("ci", "Vérifications automatiques", "CI", _ci(ci), _files(ci)))
        sizes["ci"] = len(ci)
    admin = [s for s in services if image_name(s).startswith(DB_ADMIN)]
    if admin:
        proofs = [proof_of(c) for s in admin for c in s.declared[:1]]
        title = f"Voir la base ({image_name(admin[0]).capitalize()})"
        items.append(_item("db-admin", title, "", "la base dans le navigateur, en local", proofs))
    generators = [f for f in facts.files if f.lower() in GENERATORS]
    if generators:
        detail = "questions posées à la création"
        items.append(_item("generator", "Créer un projet depuis ce modèle", "", detail, _files(generators)))
    docs = [f for f in facts.files if DOCS.match(f) and posixpath.basename(f).lower() not in NOT_DOCS]
    if docs:
        detail, shown = _docs(docs)
        items.append(_item("docs", "Documentation", "docs", detail, _files(shown)))
        sizes["docs"] = len(docs)
    plugins = facts.signal("plugins")
    if plugins:
        detail = "d'autres paquets ajoutent des commandes"
        items.append(_item("plugins", "Extensions", "", detail, [proof_of(c) for c in plugins[:MAX_PROOFS]]))
    for index, (title, detail, proofs) in enumerate(extra):
        items.append(_item(f"service-{index}", title, "", detail, proofs))
    # The chip names the first two of these: the biggest first, each kept in one of their own places.
    places = [i for i, item in enumerate(items) if item.id in sizes]
    biggest = sorted((items[i] for i in places), key=lambda item: -sizes[item.id])
    for place, item in zip(places, biggest, strict=True):
        items[place] = item
    return items


def _prestart(facts: Facts) -> str:
    """What a start-up job prepares: the tables (migrations), the first account (a seeded admin)."""
    does = []
    if any(MIGRATIONS.search(f) for f in facts.files):
        does.append("crée les tables")
    if facts.signal("first-account"):
        does.append("le premier compte" if does else "crée le premier compte")
    return " et ".join(does) or "prépare tout avant que le serveur démarre"


def _ci(files: list[str]) -> str:
    names = " ".join(posixpath.basename(f).lower() for f in files)
    kinds = [word for word, pattern in CI_KINDS if re.search(pattern, names)]
    return f"{len(files)} fichiers" + (f" : {', '.join(kinds)}" if kinds else "")


def _docs(files: list[str]) -> tuple[str, list[str]]:
    """A documentation site (`docs/` with its builder), or the guides at the root, by what they teach."""
    site = [f for f in files if f.lower().startswith(("doc/", "docs/"))]
    if any(posixpath.basename(f).lower() in DOC_SITE for f in site) or any(
        f.lower() in ("mkdocs.yml", "mkdocs.yaml") for f in files
    ):
        return "site de documentation", ["docs/"]
    found: list[tuple[int, str, str]] = []
    for f in files:
        if "/" in f:
            continue
        for rank, (word, pattern) in enumerate(GUIDES):
            if re.search(pattern, f.lower()):
                found.append((rank, word, f))
                break
    if not found:
        return f"{len(files)} fichiers", files
    found.sort()
    words = list(dict.fromkeys(word for _, word, _ in found))
    return ", ".join(words), list(dict.fromkeys(f for _, w, f in found if w in words))


def _tests(
    facts: Facts, services: list[ComposeService], roles: set[str], commands: int
) -> tuple[AroundItem, int] | None:
    files = [f for f in facts.files if TEST_FILE.search(f)]
    runners = [s for s in services if test_service(s.name)]
    if not files and not runners:
        return None
    python = [f for f in files if f.endswith(".py")]
    pytest = any(posixpath.basename(f) == "conftest.py" for f in files) or any(
        "pytest" in facts.deps(d) for d in facts.requires
    )
    tools: list[tuple[str, str]] = []  # (the part tested, the tool)
    if python:
        tools.append(("serveur", "pytest" if pytest else "Python"))
    if runners or any("playwright" in f for f in facts.files):
        tools.append(("écrans", "Playwright"))
    if len(tools) > 1 and {"server", "web"} <= roles:
        detail = " et ".join(f"{part} ({tool})" for part, tool in tools)
    elif tools:
        test_files = [f for f in python if posixpath.basename(f).startswith("test_")]
        per_command = commands > 0 and 0.8 <= len(test_files) / commands <= 1.25
        count = "un fichier par commande ou presque" if per_command else f"{len(files)} fichiers"
        detail = f"{tools[0][1]}, {count}"
    else:
        detail = f"{len(files)} fichiers"
    proofs = _files(files) + [proof_of(c) for s in runners for c in s.declared[:1]]
    return _item("tests", "Tests", "tests", detail, proofs), len(files)


def _item(key: str, title: str, short: str, detail: str, proofs: list[Proof]) -> AroundItem:
    return AroundItem(key, title, short, detail, proofs[:MAX_PROOFS])


def _files(paths: list[str]) -> list[Proof]:
    return [Proof(p, 0, 0) for p in sorted(paths)[:MAX_PROOFS]]  # the whole file

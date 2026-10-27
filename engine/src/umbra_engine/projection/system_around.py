"""What sits around the running parts and does not make the app run: tests, CI, docs, admin tools,
start-up jobs, a project generator, a proxy. Folded into one « + N autour » item on the Level 0 map."""

import posixpath
import re

from umbra_engine.projection.system_facts import ComposeService, Facts
from umbra_engine.projection.system_model import AroundItem, Proof, proof_of
from umbra_engine.projection.system_units import test_service

DB_ADMIN = ("adminer", "phpmyadmin", "pgadmin")
PROXIES = ("traefik", "nginx-proxy", "caddy", "haproxy", "envoy")
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
MAX_PROOFS = 5


def image_name(service: ComposeService) -> str:
    """`schickling/mailcatcher:latest` → `mailcatcher`."""
    return service.image.split("@", 1)[0].rsplit("/", 1)[-1].split(":", 1)[0].lower()


def around_items(
    facts: Facts, prestart: list[str], extra: list[tuple[str, str, list[Proof]]]
) -> list[AroundItem]:
    """In a fixed order. `prestart`: compose services that prepare the app before it starts.
    `extra`: services that fit no box, as (title, detail, proofs)."""
    items: list[AroundItem] = []
    sentry = facts.signal("sentry")
    if sentry:
        items.append(_item("sentry", "Suivi des erreurs", "", "Sentry", [proof_of(c) for c in sentry]))
    services = list(facts.services.values())
    starting = [facts.services[name] for name in prestart]
    if starting:
        proofs = [proof_of(c) for s in starting for c in s.declared[:1]]
        items.append(_item("prestart", "Préparation au démarrage", "", ", ".join(prestart), proofs))
    items += _tests(facts, services)
    ci = [f for f in facts.files if CI.match(f)]
    if ci:
        items.append(_item("ci", "Vérifications automatiques", "CI", f"{len(ci)} fichiers", _files(ci)))
    admin = [s for s in services if image_name(s).startswith(DB_ADMIN)]
    if admin:
        proofs = [proof_of(c) for s in admin for c in s.declared[:1]]
        title = f"Voir la base ({image_name(admin[0]).capitalize()})"
        items.append(_item("db-admin", title, "", "la base dans le navigateur", proofs))
    proxies = [s for s in services if image_name(s).startswith(PROXIES) or s.name.lower() == "proxy"]
    if proxies:
        proofs = [proof_of(c) for s in proxies for c in s.declared[:1]]
        title = f"Proxy ({image_name(proxies[0]).capitalize() or proxies[0].name})"
        items.append(_item("proxy", title, "", ", ".join(s.name for s in proxies), proofs))
    generators = [f for f in facts.files if f.lower() in GENERATORS]
    if generators:
        items.append(
            _item("generator", "Créer un projet depuis ce modèle", "", generators[0], _files(generators))
        )
    plugins = facts.signal("plugins")
    if plugins:
        detail = "d'autres paquets ajoutent des commandes"
        items.append(_item("plugins", "Extensions", "", detail, [proof_of(c) for c in plugins[:MAX_PROOFS]]))
    for index, (title, detail, proofs) in enumerate(extra):
        items.append(_item(f"service-{index}", title, "", detail, proofs))
    docs = [f for f in facts.files if DOCS.match(f) and posixpath.basename(f).lower() not in NOT_DOCS]
    if docs:
        items.append(_item("docs", "Documentation", "docs", f"{len(docs)} fichiers", _files(docs)))
    return items


def _tests(facts: Facts, services: list[ComposeService]) -> list[AroundItem]:
    files = [f for f in facts.files if TEST_FILE.search(f)]
    runners = [s for s in services if test_service(s.name)]
    tools = []
    if any(f.endswith(".py") for f in files):
        pytest = any(posixpath.basename(f) == "conftest.py" for f in files)
        tools.append(
            "pytest" if pytest or any("pytest" in facts.deps(d) for d in facts.requires) else "Python"
        )
    if runners or any("playwright" in f for f in facts.files):
        tools.append("Playwright")
    if not files and not runners:
        return []
    proofs = _files(files) + [proof_of(c) for s in runners for c in s.declared[:1]]
    return [_item("tests", "Tests", "tests", " et ".join(tools) or f"{len(files)} fichiers", proofs)]


def _item(key: str, title: str, short: str, detail: str, proofs: list[Proof]) -> AroundItem:
    return AroundItem(key, title, short, detail, proofs[:MAX_PROOFS])


def _files(paths: list[str]) -> list[Proof]:
    return [Proof(p, 0, 0) for p in sorted(paths)[:MAX_PROOFS]]  # the whole file

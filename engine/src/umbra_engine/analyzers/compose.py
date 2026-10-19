"""Docker Compose files: the services they declare, with images, builds, dependencies and ports.

Every Claim is a Declaration (a Fact about what the file says), never proof that anything runs.
Values are kept as written, `${VAR}` interpolation included. A service built from a Dockerfile is
linked to that Dockerfile's `build:` key, so the two Analyzers meet without guessing.
"""

import posixpath
import re
from collections.abc import Iterable

import yaml

from umbra_engine.analyzers.dockerfile import build_key
from umbra_engine.analyzers.yaml_nodes import YamlText, get, items, scalar, sequence
from umbra_engine.claims import BUILT_FROM, DECLARES, DEPENDS_ON, EXPOSES, USES_IMAGE, Claim, Kind
from umbra_engine.guard import GuardedFile

COMPOSE_NAME = re.compile(r"(?:^|/)(?:docker-)?compose(?:[.\-][\w.\-]+)?\.ya?ml$", re.IGNORECASE)


def service_key(name: str) -> str:
    return f"service:{name}"


class ComposeAnalyzer:
    producer = "compose@1.1"

    def accepts(self, file: GuardedFile) -> bool:
        return COMPOSE_NAME.search(file.rel_path) is not None

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        parsed = YamlText(file.text)
        return [
            claim
            for document in parsed.documents
            for name, key, service in items(get(document, "services"))
            for claim in _service(parsed, file.rel_path, name, key, service)
        ]

    def limits(self, file: GuardedFile) -> list[str]:
        try:
            YamlText(file.text)
        except yaml.YAMLError:
            return ["unparsable YAML"]
        return []


def _service(parsed: YamlText, path: str, name: str, key: yaml.Node, service: yaml.Node) -> list[Claim]:
    subject = service_key(name)
    start, end = parsed.span(key, service)
    claims = [Claim(path, "module", DECLARES, subject, "service", "fact", start, end)]

    keys = {field: field_key for field, field_key, _ in items(service)}

    def at(relation: str, obj: str, kind: Kind, node: yaml.Node, field: str | None = None) -> None:
        """Evidence is the value's lines, or the whole `field:` entry when the value is a block."""
        if field is None:
            span = parsed.located(node)
            first, last = span.start, span.end
        else:
            first, last = parsed.span(keys[field], node)
        claims.append(Claim(subject, "service", relation, obj, kind, "fact", first, last))

    image = get(service, "image")
    if image is not None and scalar(image):
        at(USES_IMAGE, f"image:{scalar(image)}", "image", image)
    build = get(service, "build")
    context = scalar(build) or scalar(get(build, "context"))
    if build is not None and context:
        directory = posixpath.normpath(posixpath.join(posixpath.dirname(path), context))
        dockerfile = scalar(get(build, "dockerfile")) or "Dockerfile"
        target = build_key(posixpath.normpath(posixpath.join(directory, dockerfile)))
        at(BUILT_FROM, target, "resource", build, field="build")
    depends = get(service, "depends_on")
    for dependency in sequence(depends):
        if scalar(dependency):
            at(DEPENDS_ON, service_key(str(scalar(dependency))), "service", dependency)
    for dependency_name, dependency_key, _ in items(depends):
        at(DEPENDS_ON, service_key(dependency_name), "service", dependency_key)
    for port in sequence(get(service, "ports")):
        published = scalar(port) or scalar(get(port, "published"))
        if published:
            at(EXPOSES, f"port:{published}", "port", port)
    return claims

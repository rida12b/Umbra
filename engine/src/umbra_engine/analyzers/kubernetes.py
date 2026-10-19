"""Kubernetes manifests: workloads, images, ports, labels, Services, what they select, Ingress routes.

Declarations only. Labels are one Claim per `key=value`: a Service `selects` each pair of its
selector and a workload `has_labels` each of its pod labels, so "selector is a subset of the labels"
is checked from Facts when the map is built, never guessed here. Templated manifests (Helm) are not
analyzed: their names are not known until rendering.
"""

from collections.abc import Iterable, Iterator

import yaml

from umbra_engine.analyzers.yaml_nodes import YamlText, get, items, scalar, sequence
from umbra_engine.claims import DECLARES, EXPOSES, HAS_LABELS, ROUTES_TO, SELECTS, USES_IMAGE, Claim, Kind
from umbra_engine.guard import GuardedFile

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob", "Pod"}
RESOURCE_KINDS: dict[str, Kind] = {"Service": "k8s-service", "Ingress": "ingress"}
NOT_RESOURCES = {"Kustomization", "Component"}
YAML_SUFFIXES = (".yaml", ".yml")
TEMPLATE_MARKERS = ("{{", "{%")


class TemplatedManifestError(ValueError):
    """The manifest is a template (Helm, Jinja): names and values are only known after rendering."""


def resource_key(kind: str, name: str, namespace: str | None = None) -> str:
    return f"k8s:{namespace}/{kind}/{name}" if namespace else f"k8s:{kind}/{name}"


def label_key(key: str, value: str) -> str:
    return f"label:{key}={value}"


class KubernetesAnalyzer:
    producer = "kubernetes@1.1"

    def __init__(self) -> None:
        self._notes: dict[str, list[str]] = {}

    def accepts(self, file: GuardedFile) -> bool:
        if not file.rel_path.lower().endswith(YAML_SUFFIXES):
            return False
        return "apiVersion:" in file.text and "kind:" in file.text

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        if any(marker in file.text for marker in TEMPLATE_MARKERS):
            raise TemplatedManifestError(file.rel_path)
        parsed = YamlText(file.text)
        claims: list[Claim] = []
        notes: list[str] = []
        for document in _resources(parsed.documents):
            kind = scalar(get(document, "kind"))
            if kind in NOT_RESOURCES:
                notes.append(f"{kind} not resolved (overlays and patches are not applied)")
                continue
            claims += _resource(parsed, file.rel_path, document)
        self._notes[file.rel_path] = notes
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        return self._notes.pop(file.rel_path, [])


def _resources(documents: list[yaml.Node]) -> Iterator[yaml.Node]:
    """Every document, and every item of a `kind: List`."""
    for document in documents:
        if scalar(get(document, "kind")) == "List":
            yield from sequence(get(document, "items"))
        else:
            yield document


def _resource(parsed: YamlText, path: str, document: yaml.Node) -> list[Claim]:
    kind, name = scalar(get(document, "kind")), scalar(get(document, "metadata", "name"))
    if kind is None or name is None or scalar(get(document, "apiVersion")) is None:
        return []
    namespace = scalar(get(document, "metadata", "namespace"))
    subject = resource_key(kind, name, namespace)
    span = parsed.located(document)
    object_kind: Kind = "workload" if kind in WORKLOADS else RESOURCE_KINDS.get(kind, "resource")
    claims = [Claim(path, "module", DECLARES, subject, object_kind, "fact", span.start, span.end)]
    if kind in WORKLOADS:
        claims += _workload(parsed, subject, kind, document)
    elif kind == "Service":
        claims += _service(parsed, subject, document)
    elif kind == "Ingress":
        claims += _ingress(parsed, subject, document, namespace)
    return claims


def _workload(parsed: YamlText, subject: str, kind: str, document: yaml.Node) -> list[Claim]:
    if kind == "Pod":
        pod: yaml.Node | None = document
    elif kind == "CronJob":
        pod = get(document, "spec", "jobTemplate", "spec", "template")
    else:
        pod = get(document, "spec", "template")
    claims = [
        _at(parsed, subject, "workload", HAS_LABELS, label_key(key, value), "labels", node)
        for key, value, node in _pairs(get(pod, "metadata", "labels"))
    ]
    for section in ("containers", "initContainers"):
        for container in sequence(get(pod, "spec", section)):
            image = get(container, "image")
            if image is not None and scalar(image):
                claims.append(
                    _at(parsed, subject, "workload", USES_IMAGE, f"image:{scalar(image)}", "image", image)
                )
            for port in sequence(get(container, "ports")):
                number = get(port, "containerPort")
                if number is not None and scalar(number):
                    claims.append(
                        _at(parsed, subject, "workload", EXPOSES, f"port:{scalar(number)}", "port", number)
                    )
    return claims


def _service(parsed: YamlText, subject: str, document: yaml.Node) -> list[Claim]:
    claims = [
        _at(parsed, subject, "k8s-service", SELECTS, label_key(key, value), "labels", node)
        for key, value, node in _pairs(get(document, "spec", "selector"))
    ]
    for port in sequence(get(document, "spec", "ports")):
        number = get(port, "port")
        if number is not None and scalar(number):
            claims.append(
                _at(parsed, subject, "k8s-service", EXPOSES, f"port:{scalar(number)}", "port", number)
            )
    return claims


def _ingress(parsed: YamlText, subject: str, document: yaml.Node, namespace: str | None) -> list[Claim]:
    backends = [get(document, "spec", "defaultBackend"), get(document, "spec", "backend")]
    for rule in sequence(get(document, "spec", "rules")):
        backends += [get(path, "backend") for path in sequence(get(rule, "http", "paths"))]
    claims = []
    for backend in backends:
        service = get(backend, "service", "name") or get(backend, "serviceName")
        if service is not None and scalar(service):
            target = resource_key("Service", str(scalar(service)), namespace)
            claims.append(_at(parsed, subject, "ingress", ROUTES_TO, target, "k8s-service", service))
    return claims


def _pairs(mapping: yaml.Node | None) -> Iterator[tuple[str, str, yaml.Node]]:
    for key, key_node, value in items(mapping):
        if scalar(value) is not None:
            yield key, str(scalar(value)), key_node


def _at(
    parsed: YamlText, subject: str, subject_kind: Kind, relation: str, obj: str, kind: Kind, node: yaml.Node
) -> Claim:
    span = parsed.located(node)
    return Claim(subject, subject_kind, relation, obj, kind, "fact", span.start, span.end)

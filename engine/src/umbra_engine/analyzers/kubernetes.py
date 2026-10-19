"""Kubernetes manifests: workloads, their images and labels, Services and what they select, Ingress routes.

Declarations only. A Service and the workloads it reaches meet on a shared `labels:` key: the
Service `selects` it and each workload `has_labels` it, so linking needs no guess.
"""

from collections.abc import Iterable

import yaml

from umbra_engine.analyzers.yaml_nodes import YamlText, get, items, scalar, sequence
from umbra_engine.claims import DECLARES, EXPOSES, HAS_LABELS, ROUTES_TO, SELECTS, USES_IMAGE, Claim, Kind
from umbra_engine.guard import GuardedFile

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob", "Pod"}
YAML_SUFFIXES = (".yaml", ".yml")


def resource_key(kind: str, name: str) -> str:
    return f"k8s:{kind}/{name}"


def labels_key(labels: dict[str, str]) -> str:
    return "labels:" + ",".join(f"{key}={value}" for key, value in sorted(labels.items()))


class KubernetesAnalyzer:
    producer = "kubernetes@1.0"

    def accepts(self, file: GuardedFile) -> bool:
        if not file.rel_path.lower().endswith(YAML_SUFFIXES):
            return False
        return "apiVersion:" in file.text and "kind:" in file.text

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        parsed = YamlText(file.text)
        claims: list[Claim] = []
        for document in parsed.documents:
            kind, name = scalar(get(document, "kind")), scalar(get(document, "metadata", "name"))
            if kind is None or name is None or scalar(get(document, "apiVersion")) is None:
                continue
            subject = resource_key(kind, name)
            span = parsed.located(document)
            object_kind: Kind = "workload" if kind in WORKLOADS else _kind(kind)
            claims.append(
                Claim(file.rel_path, "module", DECLARES, subject, object_kind, "fact", span.start, span.end)
            )
            if kind in WORKLOADS:
                claims += _workload(parsed, subject, kind, document)
            elif kind == "Service":
                claims += _service(parsed, subject, document)
            elif kind == "Ingress":
                claims += _ingress(parsed, subject, document)
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        try:
            YamlText(file.text)
        except yaml.YAMLError:
            return ["unparsable YAML (templated manifest?)"]
        return []


def _workload(parsed: YamlText, subject: str, kind: str, document: yaml.Node) -> list[Claim]:
    pod = (
        get(document, "spec", "jobTemplate", "spec", "template")
        if kind == "CronJob"
        else get(document, "spec", "template")
    )
    pod = document if kind == "Pod" else pod
    claims = []
    labels = get(pod, "metadata", "labels")
    if labels is not None:
        claims.append(
            _at(parsed, subject, "workload", HAS_LABELS, labels_key(_mapping(labels)), "labels", labels)
        )
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
    claims = []
    selector = get(document, "spec", "selector")
    if selector is not None and _mapping(selector):
        claims.append(
            _at(parsed, subject, "k8s-service", SELECTS, labels_key(_mapping(selector)), "labels", selector)
        )
    for port in sequence(get(document, "spec", "ports")):
        number = get(port, "port")
        if number is not None and scalar(number):
            claims.append(
                _at(parsed, subject, "k8s-service", EXPOSES, f"port:{scalar(number)}", "port", number)
            )
    return claims


def _ingress(parsed: YamlText, subject: str, document: yaml.Node) -> list[Claim]:
    claims = []
    for rule in sequence(get(document, "spec", "rules")):
        for path in sequence(get(rule, "http", "paths")):
            backend = get(path, "backend", "service", "name") or get(path, "backend", "serviceName")
            if backend is not None and scalar(backend):
                target = resource_key("Service", str(scalar(backend)))
                claims.append(_at(parsed, subject, "ingress", ROUTES_TO, target, "k8s-service", backend))
    return claims


def _mapping(node: yaml.Node) -> dict[str, str]:
    return {key: str(scalar(value)) for key, _, value in items(node) if scalar(value) is not None}


RESOURCE_KINDS: dict[str, Kind] = {"Service": "k8s-service", "Ingress": "ingress"}


def _kind(kind: str) -> Kind:
    return RESOURCE_KINDS.get(kind, "resource")


def _at(
    parsed: YamlText, subject: str, subject_kind: Kind, relation: str, obj: str, kind: Kind, node: yaml.Node
) -> Claim:
    span = parsed.located(node)
    return Claim(subject, subject_kind, relation, obj, kind, "fact", span.start, span.end)

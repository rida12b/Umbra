"""Compose, Dockerfile and Kubernetes Declarations: what configuration says, at the exact lines."""

import pytest
from secret_fixtures import write_repo

from umbra_engine.coverage import coverage_report
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry

COMPOSE = """services:
  db:
    image: postgres:18
    ports:
      - "5432:5432"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"

  worker:
    image: ${IMAGE}:${TAG}-worker
    depends_on:
      - backend
"""

DOCKERFILE = """FROM python:3.13 AS builder
RUN pip install uv
FROM python:3.13-slim
COPY --from=builder /app /app
EXPOSE 8000 9000
CMD ["fastapi", "run"]
"""

K8S = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart
spec:
  template:
    metadata:
      labels:
        app: cart
    spec:
      containers:
        - name: cart
          image: shop/cart:1.0
          ports:
            - containerPort: 7070
---
apiVersion: v1
kind: Service
metadata:
  name: cart
spec:
  selector:
    app: cart
  ports:
    - port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
spec:
  rules:
    - http:
        paths:
          - path: /cart
            backend:
              service:
                name: cart
"""


@pytest.fixture
def claims(settings, make_repo):
    files = {"compose.yml": COMPOSE, "backend/Dockerfile": DOCKERFILE, "deploy/cart.yaml": K8S}
    root = write_repo(make_repo("deploy"), files, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            stored = store.claims()
            report = coverage_report(store.files())
    return {(c.subject, c.relation, c.object): (c.line_start, c.line_end, c.status) for c in stored}, report


def test_compose_services_and_their_links(claims):
    found, _ = claims
    assert found[("compose.yml", "declares", "service:db")] == (2, 5, "fact")
    assert found[("compose.yml", "declares", "service:backend")] == (7, 15, "fact")
    assert found[("service:db", "uses_image", "image:postgres:18")][:2] == (3, 3)
    assert found[("service:db", "exposes", "port:5432:5432")][:2] == (5, 5)
    assert found[("service:backend", "built_from", "build:backend/Dockerfile")][:2] == (8, 10)
    assert found[("service:backend", "depends_on", "service:db")][:2] == (12, 12)
    assert found[("service:worker", "depends_on", "service:backend")][:2] == (20, 20)
    assert ("service:worker", "uses_image", "image:${IMAGE}:${TAG}-worker") in found


def test_dockerfile_base_images_skip_internal_stages(claims):
    found, _ = claims
    build = "build:backend/Dockerfile"
    bases = {obj for subject, relation, obj in found if subject == build and relation == "based_on"}
    assert bases == {"image:python:3.13", "image:python:3.13-slim"}
    assert (build, "exposes", "port:9000") in found


def test_kubernetes_service_and_workload_meet_on_labels(claims):
    found, _ = claims
    assert found[("deploy/cart.yaml", "declares", "k8s:Deployment/cart")][:2] == (1, 15)
    assert ("k8s:Deployment/cart", "has_labels", "labels:app=cart") in found
    assert ("k8s:Service/cart", "selects", "labels:app=cart") in found
    assert found[("k8s:Deployment/cart", "uses_image", "image:shop/cart:1.0")][:2] == (13, 13)
    assert ("k8s:Ingress/web", "routes_to", "k8s:Service/cart") in found


def test_declarations_never_claim_that_anything_runs(claims):
    found, _ = claims
    relations = {relation for _, relation, _ in found}
    assert not relations & {"runs", "deployed", "running", "listens"}
    assert all(status == "fact" for _, _, status in found.values())


def test_configuration_files_are_now_covered(claims):
    _, report = claims
    states = {f.path: f.state for f in report.files}
    assert states == {
        "compose.yml": "covered",
        "backend/Dockerfile": "covered",
        "deploy/cart.yaml": "covered",
    }


def test_templated_manifests_are_reported_not_guessed(settings, make_repo):
    helm = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n"
    helm += '  name: {{ .Values.name }}\n  {{- include "x" . }}\n'
    root = write_repo(make_repo("helm"), {"chart/templates/d.yaml": helm}, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            (entry,) = store.files()
            assert store.claims() == []
    assert "kubernetes@1.0 failed" in entry.detail


def test_evidence_lines_hold_the_declared_value(settings, make_repo):
    texts = {"compose.yml": COMPOSE, "backend/Dockerfile": DOCKERFILE, "deploy/cart.yaml": K8S}
    root = write_repo(make_repo("evidence"), texts, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            stored = store.claims()
    checked = 0
    for claim in stored:
        if claim.relation in {"uses_image", "exposes", "based_on", "depends_on"}:
            value = claim.object.split(":", 1)[1]
            lines = texts[claim.file].split("\n")
            cited = "\n".join(lines[claim.line_start - 1 : claim.line_end])
            assert value in cited, (claim.file, claim.line_start, claim.object)
            checked += 1
    assert checked >= 12

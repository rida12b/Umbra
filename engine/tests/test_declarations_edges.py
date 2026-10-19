"""Edge cases found by the independent review of the Declaration Analyzers."""

from secret_fixtures import write_repo

from umbra_engine.coverage import coverage_report
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry


def index(settings, make_repo, files: dict[str, str]):
    root = write_repo(make_repo("edges"), files, git=False)
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            claims = {(c.subject, c.relation, c.object) for c in store.claims()}
            return claims, {f.path: f for f in coverage_report(store.files()).files}


def test_a_selector_is_matched_pair_by_pair_so_extra_workload_labels_do_not_break_the_link(
    settings, make_repo
):
    manifest = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: shop
spec:
  template:
    metadata:
      labels:
        app: web
        version: v1
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: shop
spec:
  selector:
    app: web
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: edge
  namespace: shop
spec:
  defaultBackend:
    service:
      name: web
"""
    claims, _ = index(settings, make_repo, {"k8s/web.yaml": manifest})
    assert ("k8s:shop/Service/web", "selects", "label:app=web") in claims
    assert {
        ("k8s:shop/Deployment/web", "has_labels", f"label:{pair}") for pair in ("app=web", "version=v1")
    } <= claims
    assert ("k8s:shop/Ingress/edge", "routes_to", "k8s:shop/Service/web") in claims


def test_list_items_are_resources_and_kustomizations_are_partial(settings, make_repo):
    listed = "apiVersion: v1\nkind: List\nitems:\n"
    listed += "  - apiVersion: v1\n    kind: Service\n    metadata:\n      name: api\n"
    kustomization = (
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n  - web.yaml\n"
    )
    claims, coverage = index(
        settings, make_repo, {"k8s/list.yaml": listed, "k8s/kustomization.yaml": kustomization}
    )
    assert ("k8s/list.yaml", "declares", "k8s:Service/api") in claims
    assert coverage["k8s/kustomization.yaml"].state == "partial"


def test_parseable_helm_templates_are_gaps_not_facts(settings, make_repo):
    helm = 'apiVersion: v1\nkind: Service\nmetadata:\n  name: "{{ .Release.Name }}-svc"\n'
    claims, coverage = index(settings, make_repo, {"chart/templates/svc.yaml": helm})
    assert claims == set()
    assert coverage["chart/templates/svc.yaml"].state == "gap"


def test_compose_merge_keys_ports_volumes_and_remote_builds(settings, make_repo):
    compose = """x-base: &base
  image: shop/base:1
  depends_on: [db]
services:
  db:
    image: postgres:18
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro
  api:
    <<: *base
    ports:
      - target: 8000
        published: 80
      - target: 9000
  web:
    build: https://github.com/acme/web.git#main
volumes:
  pgdata:
"""
    claims, _ = index(settings, make_repo, {"compose.yml": compose})
    assert ("service:api", "uses_image", "image:shop/base:1") in claims
    assert ("service:api", "depends_on", "service:db") in claims
    assert ("service:api", "exposes", "port:80:8000") in claims
    assert ("service:api", "exposes", "port:9000") in claims
    assert ("service:db", "mounts", "volume:pgdata") in claims
    assert ("service:db", "mounts", "dir:./init") in claims
    assert ("service:web", "built_from", "remote:https://github.com/acme/web.git#main") in claims


def test_documentation_about_dockerfiles_is_not_a_dockerfile(settings, make_repo):
    claims, coverage = index(
        settings, make_repo, {"docs/dockerfile.md": "# How we build\nFROM is explained here\n"}
    )
    assert claims == set()
    assert coverage["docs/dockerfile.md"].reasons == ["no analyzer for markdown"]

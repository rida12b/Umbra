"""Declared dependencies and infrastructure: what manifests and Terraform ask for, never proof it exists."""

from secret_fixtures import write_repo

from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry

FILES = {
    "web/package.json": (
        '{\n  "name": "web",\n  "dependencies": {\n    "react": "19.3.0"\n  },\n'
        '  "devDependencies": {\n    "vite": "8.3.1"\n  }\n}\n'
    ),
    "api/pyproject.toml": (
        '[project]\nname = "api"\ndependencies = [\n    "fastapi>=0.115,<1.0",\n    "PyYAML>=6.0",\n]\n'
    ),
    "api/requirements-dev.txt": "# tools\npytest==8.0\n-r requirements.txt\n\nruff>=0.5  # lint\n",
    "svc/go.mod": "module example.com/svc\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n)\n",
    "infra/main.tf": (
        'provider "aws" {\n  region = var.region\n}\n\n'
        'resource "aws_s3_bucket" "logs" {\n  bucket = "logs"\n}\n\n'
        'resource "aws_s3_bucket_policy" "p" {\n  bucket = aws_s3_bucket.logs.id  # the bucket above\n'
        "  policy = data.aws_iam_policy_document.d.json\n}\n\n"
        'module "vpc" {\n  source = "terraform-aws-modules/vpc/aws"\n  name   = local.name\n}\n\n'
        'data "aws_iam_policy_document" "d" {}\n'
    ),
}


def index(settings, root):
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            return store.claims(limit=10_000)


def test_manifest_dependencies_are_declared_with_their_line(settings, make_repo):
    claims = index(settings, write_repo(make_repo("manifests"), FILES, git=False))
    required = {(c.file, c.object, c.line_start) for c in claims if c.relation == "requires"}
    assert required == {
        ("web/package.json", "package:npm/react", 4),
        ("web/package.json", "package:npm/vite", 7),
        ("api/pyproject.toml", "package:pypi/fastapi", 4),
        ("api/pyproject.toml", "package:pypi/pyyaml", 5),
        ("api/requirements-dev.txt", "package:pypi/pytest", 2),
        ("api/requirements-dev.txt", "package:pypi/ruff", 5),
        ("svc/go.mod", "package:go/github.com/gin-gonic/gin", 4),
    }


def test_terraform_blocks_sources_and_references(settings, make_repo):
    claims = index(settings, write_repo(make_repo("terraform"), FILES, git=False))
    declared = {
        (c.object, c.line_start, c.line_end)
        for c in claims
        if c.relation == "declares" and c.object.startswith("tf:")
    }
    assert declared == {
        ("tf:infra/provider.aws", 1, 3),
        ("tf:infra/aws_s3_bucket.logs", 5, 7),
        ("tf:infra/aws_s3_bucket_policy.p", 9, 12),
        ("tf:infra/module.vpc", 14, 17),
        ("tf:infra/data.aws_iam_policy_document.d", 19, 19),
    }
    links = {(c.subject, c.relation, c.object) for c in claims if c.relation in ("references", "sources")}
    assert links == {
        ("tf:infra/aws_s3_bucket_policy.p", "references", "tf:infra/aws_s3_bucket.logs"),
        ("tf:infra/aws_s3_bucket_policy.p", "references", "tf:infra/data.aws_iam_policy_document.d"),
        ("tf:infra/module.vpc", "sources", "source:terraform-aws-modules/vpc/aws"),
    }  # `var.region` and `local.name` are inputs, not blocks
    assert all(
        c.status == "fact" for c in claims if c.object.startswith("tf:")
    )  # the text says so; no deployment

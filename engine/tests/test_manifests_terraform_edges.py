"""The independent review's cases: no invented dependency or reference, the right line every time,
and every claim confirmed by the strict fact checker against the file."""

from secret_fixtures import write_repo

from umbra_engine.fact_check import check_facts
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry

FILES = {
    "one/package.json": '{"name":"x","dependencies":{"react":"1","vite":"2"}}',
    "py/pyproject.toml": (
        '[project]\nname = "api"\ndescription = "no dependencies; wraps httpx"\n'
        'dependencies = ["PyYAML>=6.0", "Django[argon2]==4"]\n\n'
        '[tool.poetry.dependencies]\npython = "^3.11"\npytest-cov = "*"\npytest = "*"\n\n'
        '[tool.poetry.group.dev.dependencies]\nruff = "*"\n'
    ),
    "py/requirements.txt": (
        "git+https://github.com/a/b.git\nhttps://example.com/pkg.whl\n-e ./local\nfoo @ https://x/foo.whl\nbar>=1\n"
    ),
    "go/go.mod": (
        "module m\n\nrequire github.com/a/one v1.0.0\n\n"
        "require (\n\tgithub.com/a/two v1.0.0 // indirect\n)\n\n"
        "replace (\n\tgithub.com/a/two v1.0.0 => ../two\n)\n\nexclude (\n\tgithub.com/x/y v0.1.0\n)\n"
    ),
    "rs/Cargo.toml": (
        '[package]\nname = "serde-helper"\n\n[dependencies]\nserde_json = "1"\nserde = "1"\n'
        'tokio = { version = "1", features = ["serde"] }\n\n'
        '[target.\'cfg(unix)\'.dependencies]\nlibc = "0.2"\n\n[workspace.dependencies]\nanyhow = "1"\n'
    ),
    "tf/main.tf": (
        'resource "aws_s3_bucket" "b" {\n'
        '  arn  = "arn:aws:s3:::my_bucket.example_com"\n'
        '  name = "a#b ${aws_s3_bucket.c.id}"  // old: aws_s3_bucket.legacy\n'
        "  /* aws_s3_bucket.gone */\n"
        '  dynamic "ebs_block_device" {\n    for_each = var.disks\n'
        "    content { size = ebs_block_device.value.size }\n  }\n"
        "  tags = { for k_v in var.list : k_v.key => k_v.value }\n"
        "}\n\n"
        'resource "aws_s3_bucket" "c" {}\n\n'
        'module "m" { source = "./x" }\n\n'
        'module "n" {\n  source        = "git::https://x.com/vpc.git?ref=v1" # pinned\n'
        "  source_bucket = aws_s3_bucket.b.id\n}\n\n"
        'resource "aws_vpc" "a" { cidr = aws_vpc.other.cidr }\n'
    ),
}


def index(settings, root):
    with Registry(settings) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            index_project(project, store)
            return store.claims(limit=10_000), check_facts(project, store, 10_000, 0)


def test_dependencies_are_read_from_the_right_place_and_line(settings, make_repo):
    claims, _ = index(settings, write_repo(make_repo("deps"), FILES, git=False))
    required = {
        (c.file.split("/")[0], c.object.split("/", 1)[1], c.line_start)
        for c in claims
        if c.relation == "requires"
    }
    assert required == {
        ("one", "react", 1),
        ("one", "vite", 1),
        ("py", "PyYAML", 4),
        ("py", "Django", 4),
        ("py", "pytest-cov", 8),
        ("py", "pytest", 9),
        ("py", "ruff", 12),
        ("py", "foo", 4),
        ("py", "bar", 5),
        ("go", "github.com/a/one", 3),
        ("go", "github.com/a/two", 6),
        ("rs", "serde_json", 5),
        ("rs", "serde", 6),
        ("rs", "tokio", 7),
        ("rs", "libc", 10),
        ("rs", "anyhow", 13),
    }


def test_terraform_references_come_from_code_not_strings_or_comments(settings, make_repo):
    claims, _ = index(settings, write_repo(make_repo("tf"), FILES, git=False))
    links = {
        (
            c.subject.split("/")[-1],
            c.relation,
            c.object.split("/", 1)[-1] if c.relation == "references" else c.object,
        )
        for c in claims
        if c.relation in ("references", "sources")
    }
    assert links == {
        ("aws_s3_bucket.b", "references", "aws_s3_bucket.c"),
        ("module.m", "sources", "source:./x"),
        ("module.n", "sources", "source:git::https://x.com/vpc.git?ref=v1"),
        ("module.n", "references", "aws_s3_bucket.b"),
        ("aws_vpc.a", "references", "aws_vpc.other"),
    }


def test_every_new_claim_is_confirmed_by_the_strict_fact_checker(settings, make_repo):
    _, checks = index(settings, write_repo(make_repo("checked"), FILES, git=False))
    new = [c for c in checks if c.claim.relation in ("requires", "references", "sources", "declares")]
    assert new and all(c.correct for c in new), [(c.claim.object, c.cited_line) for c in new if not c.correct]

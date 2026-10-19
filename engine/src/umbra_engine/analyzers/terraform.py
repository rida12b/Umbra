"""Terraform: the resources, data sources, modules and providers a configuration declares, the module
sources it uses, and the references between blocks.

Declarations only: `resource "aws_s3_bucket" "logs"` says the configuration asks for a bucket, not
that one exists. Addresses are scoped by folder, as Terraform scopes them by module directory.
"""

import posixpath
import re
from collections.abc import Iterable

import tree_sitter_language_pack as tslp

from umbra_engine.claims import DECLARES, REFERENCES, SOURCES, Claim
from umbra_engine.guard import GuardedFile

BLOCKS = {"resource": 2, "data": 2, "module": 1, "provider": 1}  # labels each block type carries
# `module.vpc`, `data.aws_iam_policy_document.d`, `aws_s3_bucket.logs` (a type has an underscore).
_REFERENCE = re.compile(
    r"(?<![\w.])(module\.[A-Za-z_][\w-]*|data\.[a-z][\w]*\.[A-Za-z_][\w-]*|[a-z][a-z0-9]*_[a-z0-9_]+\.[A-Za-z_][\w-]*)"
)
_NOT_RESOURCES = ("var.", "local.", "each.", "count.", "path.", "self.", "terraform.")


def address(directory: str, kind: str, labels: list[str]) -> str:
    """`tf:<folder>/<address>`: `aws_s3_bucket.logs`, `data.T.N`, `module.vpc`, `provider.aws`."""
    name = ".".join(labels) if kind == "resource" else ".".join([kind, *labels])
    return f"tf:{directory}/{name}" if directory else f"tf:{name}"


class TerraformAnalyzer:
    producer = "terraform@1.0"

    def accepts(self, file: GuardedFile) -> bool:
        return file.rel_path.lower().endswith(".tf")

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        source = file.text.encode("utf-8")
        tree = tslp.get_parser("hcl").parse(source)
        directory = posixpath.dirname(file.rel_path)
        body = next((c for c in tree.root_node.children if c.type == "body"), None)
        claims: list[Claim] = []
        for block in body.children if body is not None else []:
            if block.type != "block" or not block.children:
                continue
            kind = _text(source, block.children[0])
            labels = [_label(source, c) for c in block.children if c.type == "string_lit"]
            if kind not in BLOCKS or len(labels) != BLOCKS[kind]:
                continue
            key = address(directory, kind, labels)
            first, last = block.start_point[0] + 1, block.end_point[0] + 1
            claims.append(Claim(file.rel_path, "module", DECLARES, key, "resource", "fact", first, last))
            claims += _inside(source, block, key, directory, kind)
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        return []


def _inside(source: bytes, block, key: str, directory: str, kind: str) -> list[Claim]:
    """Module sources and the references written in a block's body, each with its line."""
    claims = []
    start = block.start_point[0] + 1
    lines = source[block.start_byte : block.end_byte].decode("utf-8", errors="replace").split("\n")
    seen: set[str] = set()
    for offset, line in enumerate(lines[1:], start=1):
        number = start + offset
        stripped = line.strip()
        if kind == "module" and stripped.startswith("source"):
            value = stripped.split("=", 1)[-1].strip().strip('"')
            claims.append(
                Claim(key, "resource", SOURCES, f"source:{value}", "resource", "fact", number, number)
            )
        for found in _REFERENCE.findall(line.split("#", 1)[0]):
            if found.startswith(_NOT_RESOURCES) or found in seen:
                continue
            seen.add(found)
            target = f"tf:{directory}/{found}" if directory else f"tf:{found}"
            claims.append(Claim(key, "resource", REFERENCES, target, "resource", "fact", number, number))
    return claims


def _text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _label(source: bytes, node) -> str:
    return _text(source, node).strip('"')

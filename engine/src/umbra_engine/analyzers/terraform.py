"""Terraform: the resources, data sources, modules and providers a configuration declares, the module
sources it uses, and the references between blocks.

Read from the HCL syntax tree, so text inside strings and comments never counts as a reference, while
`${...}` interpolations do. Declarations only: `resource "aws_s3_bucket" "logs"` says the
configuration asks for a bucket, not that one exists. Addresses are scoped by folder, as Terraform
scopes them by module directory.
"""

import posixpath
import re
from collections.abc import Iterable, Iterator

import tree_sitter_language_pack as tslp

from umbra_engine.claims import DECLARES, REFERENCES, SOURCES, Claim
from umbra_engine.guard import GuardedFile

BLOCKS = {"resource": 2, "data": 2, "module": 1, "provider": 1}  # labels each block type carries
NOT_BLOCKS = {"var", "local", "each", "count", "path", "self", "terraform"}  # inputs and meta-arguments
RESOURCE_TYPE = re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+$")  # `aws_s3_bucket`: a provider prefix, then a name


def address(directory: str, kind: str, labels: list[str]) -> str:
    """`tf:<folder>/<address>`: `aws_s3_bucket.logs`, `data.T.N`, `module.vpc`, `provider.aws`."""
    name = ".".join(labels) if kind == "resource" else ".".join([kind, *labels])
    return f"tf:{directory}/{name}" if directory else f"tf:{name}"


class TerraformAnalyzer:
    producer = "terraform@1.1"

    def accepts(self, file: GuardedFile) -> bool:
        return file.rel_path.lower().endswith(".tf")

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        source = file.text.encode("utf-8")
        root = tslp.get_parser("hcl").parse(source).root_node
        directory = posixpath.dirname(file.rel_path)
        claims: list[Claim] = []
        for block in _children(root, "body", "block"):
            kind = _text(source, block.children[0]) if block.children else ""
            labels = [_text(source, c).strip('"') for c in block.children if c.type == "string_lit"]
            if kind not in BLOCKS or len(labels) != BLOCKS[kind]:
                continue
            key = address(directory, kind, labels)
            first, last = block.start_point[0] + 1, block.end_point[0] + 1
            claims.append(Claim(file.rel_path, "module", DECLARES, key, "resource", "fact", first, last))
            if kind == "module":
                claims += _module_source(source, block, key)
            claims += _references(source, block, key, directory)
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        root = tslp.get_parser("hcl").parse(file.text.encode("utf-8")).root_node
        return ["Terraform syntax errors: some blocks may be missing or cut"] if root.has_error else []


def _module_source(source: bytes, block, key: str) -> list[Claim]:
    """The `source` argument of a module, when it is a plain string."""
    for attribute in _children(block, "body", "attribute"):
        if _text(source, attribute.children[0]) != "source":
            continue
        literals = [n for n in _walk(attribute) if n.type == "template_literal"]
        interpolated = any(n.type == "template_interpolation" for n in _walk(attribute))
        if len(literals) == 1 and not interpolated:
            line = attribute.start_point[0] + 1
            value = _text(source, literals[0])
            return [Claim(key, "resource", SOURCES, f"source:{value}", "resource", "fact", line, line)]
    return []


def _references(source: bytes, block, key: str, directory: str) -> list[Claim]:
    """Addresses written as expressions in the block (comments and string text are not expressions)."""
    local_names = _iterators(source, block)
    claims, seen = [], set()
    for expression in (n for n in _walk(block) if n.type == "expression"):
        target = _address_of(source, expression, local_names)
        if target is None or target in seen:
            continue
        seen.add(target)
        line = expression.start_point[0] + 1
        full = f"tf:{directory}/{target}" if directory else f"tf:{target}"
        claims.append(Claim(key, "resource", REFERENCES, full, "resource", "fact", line, line))
    return claims


def _address_of(source: bytes, expression, local_names: set[str]) -> str | None:
    """`aws_s3_bucket.logs.id` → `aws_s3_bucket.logs`; `module.vpc.x` → `module.vpc`; else None."""
    parts = expression.children
    if not parts or parts[0].type != "variable_expr":
        return None
    root = _text(source, parts[0])
    attributes = []
    for part in parts[1:]:
        if part.type != "get_attr":
            break
        attributes.append(_text(source, part).lstrip(".").strip())
    if root in NOT_BLOCKS or root in local_names:
        return None
    if root == "module" and attributes:
        return f"module.{attributes[0]}"
    if root == "data" and len(attributes) >= 2:
        return f"data.{attributes[0]}.{attributes[1]}"
    if RESOURCE_TYPE.match(root) and attributes:
        return f"{root}.{attributes[0]}"
    return None


def _iterators(source: bytes, block) -> set[str]:
    """Names that only exist inside the block: `dynamic "x"` iterators and `for` variables."""
    names = set()
    for node in _walk(block):
        if node.type == "block" and node.children and _text(source, node.children[0]) == "dynamic":
            names |= {_text(source, c).strip('"') for c in node.children if c.type == "string_lit"}
            for attribute in _children(node, "body", "attribute"):
                if _text(source, attribute.children[0]) == "iterator":
                    names.add(_text(source, attribute.children[-1]).strip())
        elif node.type in ("for_intro",):
            names |= {_text(source, c) for c in node.children if c.type == "identifier"}
    return names


def _children(node, container: str, kind: str) -> Iterator:
    for body in (c for c in node.children if c.type == container):
        yield from (c for c in body.children if c.type == kind)


def _walk(node) -> Iterator:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

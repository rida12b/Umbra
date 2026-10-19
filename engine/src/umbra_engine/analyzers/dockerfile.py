"""Dockerfiles: the base images each build stage starts from and the ports it declares.

Declarations only: `EXPOSE 8080` says the image documents that port, not that anything listens on it.
"""

import re
from collections.abc import Iterable

from umbra_engine.claims import BASED_ON, EXPOSES, Claim
from umbra_engine.guard import GuardedFile

DOCKERFILE_NAME = re.compile(r"(?:^|/)(?:[\w.\-]+\.)?dockerfile(?:\.[\w.\-]+)?$", re.IGNORECASE)
_FROM = re.compile(r"^[ \t]*FROM[ \t]+(?:--platform=\S+[ \t]+)?(\S+)(?:[ \t]+AS[ \t]+(\S+))?", re.IGNORECASE)
_EXPOSE = re.compile(r"^[ \t]*EXPOSE[ \t]+(.+)$", re.IGNORECASE)


def build_key(path: str) -> str:
    return f"build:{path}"


class DockerfileAnalyzer:
    producer = "dockerfile@1.0"

    def accepts(self, file: GuardedFile) -> bool:
        return DOCKERFILE_NAME.search(file.rel_path) is not None and not file.rel_path.endswith(
            ".dockerignore"
        )

    def analyze(self, file: GuardedFile) -> Iterable[Claim]:
        subject = build_key(file.rel_path)
        stages: set[str] = set()
        claims = []
        for number, line in enumerate(_logical_lines(file.text), start=1):
            if line is None:
                continue
            base = _FROM.match(line)
            if base:
                image, alias = base.group(1), base.group(2)
                if image.lower() not in stages:  # `FROM builder` reuses an earlier stage, not an image
                    claims.append(
                        Claim(
                            subject, "resource", BASED_ON, f"image:{image}", "image", "fact", number, number
                        )
                    )
                if alias:
                    stages.add(alias.lower())
                continue
            exposed = _EXPOSE.match(line)
            if exposed:
                for port in exposed.group(1).split():
                    claims.append(
                        Claim(subject, "resource", EXPOSES, f"port:{port}", "port", "fact", number, number)
                    )
        return claims

    def limits(self, file: GuardedFile) -> list[str]:
        return []


def _logical_lines(text: str) -> list[str | None]:
    """One entry per physical line; continued instructions are joined on their first line."""
    physical = text.split("\n")
    result: list[str | None] = []
    index = 0
    while index < len(physical):
        line, first = physical[index].rstrip("\r"), len(result)
        result.append(line)
        while line.endswith("\\") and index + 1 < len(physical):
            index += 1
            line = line[:-1] + " " + physical[index].rstrip("\r")
            result.append(None)
        result[first] = line
        index += 1
    return result

"""Analyzers: pluggable units that turn guarded content into Claims.

An Analyzer never sees a path it could open: it receives `GuardedFile`s released by the Secret Guard
(ADR-0004). To add one, implement the `Analyzer` protocol and list it in `default_analyzers()`.
"""

from collections.abc import Iterable
from typing import Protocol

from umbra_engine.claims import Claim
from umbra_engine.guard import GuardedFile


class Analyzer(Protocol):
    @property
    def producer(self) -> str:
        """`name@version`, stored with every Claim it produces."""
        ...

    def accepts(self, file: GuardedFile) -> bool: ...

    def analyze(self, file: GuardedFile) -> Iterable[Claim]: ...

    def limits(self, file: GuardedFile) -> list[str]:
        """What this Analyzer cannot extract from this file (shown as partial coverage, never hidden)."""
        ...


def default_analyzers() -> list[Analyzer]:
    from umbra_engine.analyzers.code import CodeAnalyzer
    from umbra_engine.analyzers.compose import ComposeAnalyzer
    from umbra_engine.analyzers.dockerfile import DockerfileAnalyzer
    from umbra_engine.analyzers.kubernetes import KubernetesAnalyzer
    from umbra_engine.analyzers.manifests import ManifestAnalyzer
    from umbra_engine.analyzers.terraform import TerraformAnalyzer

    return [
        CodeAnalyzer(),
        ComposeAnalyzer(),
        DockerfileAnalyzer(),
        KubernetesAnalyzer(),
        ManifestAnalyzer(),
        TerraformAnalyzer(),
    ]

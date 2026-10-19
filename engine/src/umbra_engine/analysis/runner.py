"""One study (or update) session: build the guarded copy, let Claude Code study it, check the model.

The stored record keeps the model and the digest of every file it was built from, so the next
session knows exactly which files changed.
"""

import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path

from umbra_engine.analysis.method import study_prompt, update_prompt
from umbra_engine.analysis.mirror import write_index, write_mirror
from umbra_engine.analysis.model import checked_model, parse_answer, updated_model
from umbra_engine.claims import StoredClaim
from umbra_engine.guard import SecretGuard
from umbra_engine.project_store import FileEntry
from umbra_engine.projection.graph import ProjectGraph

MODEL_KEY = "model:"
MODEL_PRODUCER = "claude-code-study@1.1"  # another version studies the Project again from scratch
MODEL_FILE = "UMBRA_MODEL.json"
MAX_LISTED_CHANGES = 200

Study = Callable[[str, Path], str]  # (prompt, folder) -> answer


def file_digests(files: list[FileEntry]) -> dict[str, str]:
    return {f.path: f.digest for f in files if f.state == "readable"}


def project_digest(digests: dict[str, str]) -> str:
    joined = "\n".join(f"{path}\0{digest}" for path, digest in sorted(digests.items()))
    return hashlib.sha256(joined.encode()).hexdigest()[:24]


def changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def run_session(
    guard: SecretGuard,
    graph: ProjectGraph,
    imports: list[StoredClaim],
    digests: dict[str, str],
    study: Study,
    previous: dict | None,
) -> str:
    """The stored record: `{"model": ..., "digests": ...}`. A previous record makes it an update."""
    with tempfile.TemporaryDirectory(prefix="umbra-study-") as name:
        folder = Path(name)
        texts = write_mirror(guard, folder)
        write_index(graph, imports, list(texts), folder)
        line_counts = {path: text.count("\n") + 1 for path, text in texts.items()}
        directories = set(graph.directories)
        if previous is None:
            model = checked_model(parse_answer(study(study_prompt(), folder)), line_counts, directories)
        else:
            changed = changed_files(previous["digests"], digests)[:MAX_LISTED_CHANGES]
            (folder / MODEL_FILE).write_text(
                json.dumps(previous["model"], ensure_ascii=False), encoding="utf-8"
            )
            patch = parse_answer(study(update_prompt(changed), folder))
            model = updated_model(previous["model"], patch, line_counts, directories)
    return json.dumps({"model": model, "digests": digests, "producer": MODEL_PRODUCER}, ensure_ascii=False)

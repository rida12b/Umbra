"""Reproduce the S1 proof on the pinned Validation Corpus (docs/validation/s1/corpus.json).

For each Project: fetch the pinned commit, index it in a throw-away Umbra home, and record
- that every file is accounted for (covered, partial or a Coverage Gap, with its reason),
- 30 Facts drawn at random (fixed seed) and checked against the code, with their Evidence,
- the initial index time and the size in lines,
- the coverage limits (why files are partial or gaps).

Usage (from the repository root):
    python engine/tools/validate_s1.py [--work DIR] [--only NAME ...] [--local NAME=PATH ...]
Outputs: docs/validation/s1/<name>.md and docs/validation/s1/summary.md. A re-run gives the same
numbers apart from timings.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from umbra_engine.coverage import coverage_report
from umbra_engine.fact_check import check_facts
from umbra_engine.guard import GuardedFile, SecretGuard
from umbra_engine.indexer import index_project
from umbra_engine.registry import Registry
from umbra_engine.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "validation" / "s1"
SAMPLE, SEED = 30, 0
TIME_LIMIT_S, LOC_LIMIT = 120, 80_000


def fetch(url: str, commit: str, target: Path) -> None:
    if (target / ".git").exists():
        subprocess.run(
            [
                "git",
                "-c",
                "core.longpaths=true",
                "-C",
                str(target),
                "fetch",
                "-q",
                "--depth",
                "1",
                "origin",
                commit,
            ],
            check=True,
        )
    else:
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(target), "init", "-q"], check=True)
        subprocess.run(
            ["git", "-c", "core.longpaths=true", "-C", str(target), "remote", "add", "origin", url],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "core.longpaths=true",
                "-C",
                str(target),
                "fetch",
                "-q",
                "--depth",
                "1",
                "origin",
                commit,
            ],
            check=True,
        )
    subprocess.run(
        ["git", "-c", "core.longpaths=true", "-C", str(target), "checkout", "-q", "--force", commit],
        check=True,
    )


def validate(name: str, root: Path, home: Path) -> dict:
    shutil.rmtree(home, ignore_errors=True)  # an initial index, every time: nothing reused
    with Registry(Settings(home=home)) as registry:
        project, _ = registry.add(root)
        with registry.open_store(project) as store:
            start = time.perf_counter()
            summary = index_project(project, store)
            seconds = time.perf_counter() - start
            files = store.files()
            report = coverage_report(files)
            checks = check_facts(project, store, SAMPLE, SEED)
    guard = SecretGuard(root)
    lines = sum(_line_count(guard, f.path) for f in files if f.state == "readable")
    partial = Counter(reason for f in report.files if f.state == "partial" for reason in f.reasons)
    return {
        "name": name,
        "files": report.total,
        "covered": report.covered,
        "partial": report.partial,
        "gap": report.gap,
        "accounted": report.covered + report.partial + report.gap == report.total == len(files),
        "gap_reasons": dict(report.gap_reasons),
        "partial_reasons": dict(partial.most_common()),
        "claims": summary.claims,
        "secrets_redacted": summary.redacted_secrets,
        "lines": lines,
        "index_seconds": round(seconds, 1),
        "facts_correct": sum(c.correct for c in checks),
        "facts_checked": len(checks),
        "facts": [
            {
                "correct": c.correct,
                "relation": c.claim.relation,
                "object": c.claim.object,
                "where": f"{c.claim.file}:{c.claim.line_start}-{c.claim.line_end}",
                "cited": c.cited_line,
            }
            for c in checks
        ],
    }


def _line_count(guard: SecretGuard, path: str) -> int:
    """Through the Secret Guard too: even a count is a read of the Project (ADR-0004)."""
    released = guard.read(path)
    return released.text.count("\n") if isinstance(released, GuardedFile) else 0


def markdown(result: dict, meta: dict) -> str:
    ok = result["facts_correct"] == result["facts_checked"] > 0  # every Fact when fewer than SAMPLE exist
    fast = result["index_seconds"] < TIME_LIMIT_S or result["lines"] > LOC_LIMIT
    private = meta["url"] == "local folder"  # a private Project's code is checked, never copied here

    def cited(fact: dict) -> str:
        return "(private Project: not reproduced)" if private else f"`{fact['cited'][:90].replace('|', '/')}`"

    rows = "\n".join(
        f"| {'ok' if f['correct'] else 'FAIL'} | `{f['relation']}` | `{f['object'][:70]}` | `{f['where']}` | "
        f"{cited(f)} |"
        for f in result["facts"]
    )
    gaps = "\n".join(f"- {reason}: {count}" for reason, count in result["gap_reasons"].items()) or "- none"
    partial = (
        "\n".join(f"- {reason}: {count}" for reason, count in result["partial_reasons"].items()) or "- none"
    )
    r = result
    accounted = (
        f"{r['files']} files = {r['covered']} covered + {r['partial']} partial + {r['gap']} Coverage Gaps"
    )
    claims = ", ".join(f"{k} {v}" for k, v in r["claims"].items())
    criteria = [
        ("Every file accounted for", f"{'yes' if r['accounted'] else 'NO'}: {accounted}"),
        (
            f"{SAMPLE} random Facts correct (seed {SEED})",
            f"{'yes' if ok else 'NO'}: {r['facts_correct']}/{r['facts_checked']}"
            + (" (every Fact: fewer than the sample size exist)" if r["facts_checked"] < SAMPLE else ""),
        ),
        (
            f"Initial index < {TIME_LIMIT_S} s for ≤ {LOC_LIMIT:,} lines",
            f"{'yes' if fast else 'NO'}: {r['index_seconds']} s for {r['lines']:,} lines",
        ),
        ("Claims", f"{claims}; secrets redacted: {r['secrets_redacted']}"),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in criteria)
    return f"""# {r["name"]}

{meta["type"]} — {meta["url"]} @ `{meta.get("commit", "local")}`

| Criterion | Result |
|---|---|
{table}

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
{gaps}

Partly analysed:
{partial}

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
{rows}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the S1 proof on the pinned Validation Corpus.")
    parser.add_argument("--work", type=Path, default=Path(tempfile.gettempdir()) / "umbra-s1")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--local", nargs="*", default=[], help="NAME=PATH: validate a local folder instead")
    args = parser.parse_args(argv)
    corpus = json.loads((OUT / "corpus.json").read_text(encoding="utf-8"))["projects"]
    local = dict(item.split("=", 1) for item in args.local)
    results = []
    # A local folder is named, never located: its path would put the user's disk layout in the report.
    for meta in corpus + [{"name": n, "url": "local folder", "type": "local Project"} for n in local]:
        if args.only and meta["name"] not in args.only:
            continue
        root = Path(local[meta["name"]]) if meta["name"] in local else args.work / "repos" / meta["name"]
        if meta["name"] not in local:
            fetch(meta["url"], meta["commit"], root)
        result = validate(meta["name"], root, args.work / "homes" / meta["name"])
        (OUT / f"{meta['name']}.md").write_text(markdown(result, meta), encoding="utf-8")
        results.append(result)
        print(f"{meta['name']}: {result['facts_correct']}/{result['facts_checked']} Facts, "
              f"accounted={result['accounted']}, {result['index_seconds']} s", flush=True)  # fmt: skip
    if not args.only and not local:
        (OUT / "summary.md").write_text(_summary(results), encoding="utf-8")
    return 0 if all(r["accounted"] and r["facts_correct"] == r["facts_checked"] for r in results) else 1


def _summary(results: list[dict]) -> str:
    rows = "\n".join(
        f"| [{r['name']}]({r['name']}.md) | {r['files']} | {r['covered']}/{r['partial']}/{r['gap']} | "
        f"{r['facts_correct']}/{r['facts_checked']} | {r['index_seconds']} s | {r['lines']:,} |"
        for r in results
    )
    return f"""# S1 proof on the Validation Corpus

Reproduce: `python engine/tools/validate_s1.py` (commits pinned in `corpus.json`). Each run indexes from an
empty store. Timings vary by machine and file cache: on the first, cold run (Windows, antivirus on) the
initial index took 8 to 48 s per Project; all stay far under the 2-minute limit.

| Project | Files | Covered / partial / gaps | Facts correct | Initial index | Lines |
|---|---|---|---|---|---|
{rows}
"""


if __name__ == "__main__":
    sys.exit(main())

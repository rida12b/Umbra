"""`umbra-engine` command line: register Projects and run the local daemon.

Named `umbra-engine` while the v0.7 `umbra` command still exists; renamed when v0.7 is removed.
"""

import argparse
import sqlite3
import sys

from umbra_engine.registry import ProjectIdCollisionError, ProjectPathError, Registry
from umbra_engine.settings import API_HOST, Settings, TokenFileError, load_or_create_token


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(prog="umbra-engine", description="Umbra System Explorer engine")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="register a folder as a Project")
    add.add_argument("path")
    commands.add_parser("list", help="list registered Projects")
    index = commands.add_parser("index", help="index a registered Project (id or path)")
    index.add_argument("project")
    verify = commands.add_parser("verify-facts", help="check a random sample of Facts against the code")
    verify.add_argument("project")
    verify.add_argument("--sample", type=int, default=30)
    verify.add_argument("--seed", type=int, default=0)
    commands.add_parser("serve", help=f"run the local API on {API_HOST}")
    commands.add_parser("token", help="print the local API token")
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except (TokenFileError, ProjectIdCollisionError, sqlite3.Error) as error:
        print(f"umbra-engine: {error}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    if args.command == "add":
        return _add(settings, args.path)
    if args.command == "index":
        return _index(settings, args.project)
    if args.command == "verify-facts":
        return _verify_facts(settings, args.project, args.sample, args.seed)
    if args.command == "list":
        with Registry(settings) as registry:
            for project in registry.list():
                print(f"{project.id}\t{project.root}")
        return 0
    if args.command == "token":
        print(load_or_create_token(settings))
        return 0
    return _serve(settings)


def _use_utf8_output() -> None:
    """Project paths can hold any character; a piped Windows console defaults to a legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _add(settings: Settings, path: str) -> int:
    try:
        with Registry(settings) as registry:
            project, created = registry.add(path)
    except ProjectPathError as error:
        print(f"umbra-engine: {error}", file=sys.stderr)
        return 2
    print(f"{'added' if created else 'already registered'}: {project.id}\t{project.root}")
    return 0


def _index(settings: Settings, project_ref: str) -> int:
    from umbra_engine.indexer import index_project

    with Registry(settings) as registry:
        project = registry.get(project_ref)
        if project is None:
            try:
                project, _ = registry.add(project_ref)
            except ProjectPathError as error:
                print(f"umbra-engine: unknown project or path: {project_ref} ({error})", file=sys.stderr)
                return 2
        with registry.open_store(project) as store:
            summary = index_project(project, store)
    print(
        f"indexed {project.id}: {summary.files} files, {summary.readable} readable "
        f"({summary.redacted_secrets} secrets redacted), skipped {summary.skipped}, claims {summary.claims}"
    )
    return 0


def _verify_facts(settings: Settings, project_ref: str, sample: int, seed: int) -> int:
    from umbra_engine.fact_check import check_facts

    with Registry(settings) as registry:
        project = registry.get(project_ref)
        if project is None:
            print(f"umbra-engine: unknown project: {project_ref}", file=sys.stderr)
            return 2
        with registry.open_store(project) as store:
            checks = check_facts(project, store, sample, seed)
    for check in checks:
        c = check.claim
        mark = "ok  " if check.correct else "FAIL"
        where = f"{c.file}:{c.line_start}-{c.line_end}"
        print(f"{mark} {c.relation:8} {c.object[:70]:70} {where}  | {check.cited_line}")
    correct = sum(check.correct for check in checks)
    print(f"{correct}/{len(checks)} Facts correct (seed {seed})")
    return 0 if checks and correct == len(checks) else 1


def _serve(settings: Settings) -> int:
    import uvicorn

    from umbra_engine.api import create_app

    uvicorn.run(create_app(settings), host=API_HOST, port=settings.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())

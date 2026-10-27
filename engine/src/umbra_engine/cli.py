"""`umbra-engine` command line: register Projects and run the local daemon.

Named `umbra-engine` while the v0.7 `umbra` command still exists; renamed when v0.7 is removed.
"""

import argparse
import sqlite3
import sys
from collections import Counter
from typing import TYPE_CHECKING

from umbra_engine.project_store import STALE_INDEX
from umbra_engine.registry import Project, ProjectIdCollisionError, ProjectPathError, Registry
from umbra_engine.settings import API_HOST, Settings, TokenFileError, load_or_create_token

if TYPE_CHECKING:
    from umbra_engine.indexer import IndexSummary  # imported when indexing: it loads the parsers


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(prog="umbra-engine", description="Umbra System Explorer engine")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="register a folder as a Project")
    add.add_argument("path")
    commands.add_parser("list", help="list registered Projects")
    index = commands.add_parser("index", help="index a registered Project (id or path)")
    index.add_argument("project")
    coverage = commands.add_parser("coverage", help="show which files are covered, partial or Coverage Gaps")
    coverage.add_argument("project")
    coverage.add_argument("--state", choices=["covered", "partial", "gap"], help="also list these files")
    verify = commands.add_parser("verify-facts", help="check a random sample of Facts against the code")
    verify.add_argument("project")
    verify.add_argument("--sample", type=int, default=30)
    verify.add_argument("--seed", type=int, default=0)
    start = commands.add_parser("start", help="register and index a folder, then open it in the web app")
    start.add_argument("path")
    start.add_argument("--no-browser", action="store_true", help="print the login link, do not open it")
    serve = commands.add_parser("serve", help=f"run the local API and web app on {API_HOST}")
    serve.add_argument("--no-browser", action="store_true", help="print the login link, do not open it")
    open_ = commands.add_parser("open", help="open the web app of a running engine in the browser")
    open_.add_argument("path", nargs="?", help="a folder: register it if needed and open its map")
    commands.add_parser("mcp", help="run the MCP server Claude Code talks to (stdio): the `show` tool")
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
    if args.command == "coverage":
        return _coverage(settings, args.project, args.state)
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
    if args.command == "open":
        return _open(settings, args.path)
    if args.command == "mcp":
        from umbra_engine.mcp_server import serve

        serve()
        return 0
    if args.command == "start":
        return _start(settings, args.path, open_browser=not args.no_browser)
    return _serve(settings, open_browser=not args.no_browser)


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
    _print_indexed(project, summary)
    return 0


def _print_indexed(project: Project, summary: "IndexSummary") -> None:
    print(
        f"indexed {project.id}: {summary.files} files, {summary.readable} readable "
        f"({summary.redacted_secrets} secrets redacted), skipped {summary.skipped}, claims {summary.claims}"
    )


def _start(settings: Settings, path: str, open_browser: bool) -> int:
    """A first run in one command: register (idempotent), index (only changed files are read again), serve,
    and open the login link straight on this Project. Nothing runs a model (ADR-0007)."""
    from umbra_engine.indexer import index_project

    try:
        with Registry(settings) as registry:
            project, _ = registry.add(path)
            print(f"indexing {project.root} ...")
            with registry.open_store(project) as store:
                summary = index_project(project, store)
    except ProjectPathError as error:
        print(f"umbra-engine: {error}", file=sys.stderr)
        return 2
    _print_indexed(project, summary)
    return _serve(settings, open_browser, project.id)


def _coverage(settings: Settings, project_ref: str, state: str | None) -> int:
    from umbra_engine.coverage import coverage_report

    with Registry(settings) as registry:
        project = registry.get(project_ref)
        if project is None:
            print(f"umbra-engine: unknown project: {project_ref}", file=sys.stderr)
            return 2
        with registry.open_store(project) as store:
            if not store.index_is_current():
                print(f"umbra-engine: {STALE_INDEX}", file=sys.stderr)
                return 1
            report = coverage_report(store.files())
    counts = f"{report.covered} covered, {report.partial} partial, {report.gap} Coverage Gaps"
    print(f"{report.total} files: {counts}")
    for reason, count in report.gap_reasons.items():
        print(f"  gap  {count:5}  {reason}")
    partial = Counter(r for f in report.files if f.state == "partial" for r in f.reasons)
    for reason, count in partial.most_common():
        print(f"  part {count:5}  {reason}")
    for file in (f for f in report.files if state and f.state == state):
        print(f"{file.state:8} {file.path}  {'; '.join(file.reasons)}")
    return 0


def _verify_facts(settings: Settings, project_ref: str, sample: int, seed: int) -> int:
    from umbra_engine.fact_check import check_facts

    with Registry(settings) as registry:
        project = registry.get(project_ref)
        if project is None:
            print(f"umbra-engine: unknown project: {project_ref}", file=sys.stderr)
            return 2
        with registry.open_store(project) as store:
            if not store.index_is_current():
                print(f"umbra-engine: {STALE_INDEX}", file=sys.stderr)
                return 1
            checks = check_facts(project, store, sample, seed)
    for check in checks:
        c = check.claim
        mark = "ok  " if check.correct else "FAIL"
        where = f"{c.file}:{c.line_start}-{c.line_end}"
        print(f"{mark} {c.relation:8} {c.object[:70]:70} {where}  | {check.cited_line}")
    correct = sum(check.correct for check in checks)
    print(f"{correct}/{len(checks)} Facts correct (seed {seed})")
    return 0 if checks and correct == len(checks) else 1


def _serve(settings: Settings, open_browser: bool, project_id: str | None = None) -> int:
    import threading
    import webbrowser

    import uvicorn

    from umbra_engine.api import create_app

    app = create_app(settings, live=True)
    link = _login_link(settings, app.state.ui_sessions.new_login_code(), project_id)
    print(f"Umbra web app: {link}")
    print("(one-time link, valid 2 minutes; `umbra-engine open` makes a new one)")
    sys.stdout.flush()  # the link must reach a redirected log now, not when the server stops
    if open_browser:
        threading.Timer(1.0, webbrowser.open_new_tab, args=(link,)).start()
    uvicorn.run(app, host=API_HOST, port=settings.port, log_level="info")
    return 0


def _open(settings: Settings, path: str | None = None) -> int:
    """Ask the running engine for a one-time login code: the token itself never leaves the terminal.
    With a folder, the engine registers it (and reads it if new) and the page lands on its map."""
    import webbrowser
    from pathlib import Path

    try:
        project_id = None
        if path is not None:
            folder = str(Path(path).expanduser().resolve())
            project_id = _engine_call(settings, "/v1/projects", {"path": folder})["id"]
        code = _engine_call(settings, "/v1/ui/login-codes", None)["code"]
    except _EngineRefusedError as error:
        print(f"umbra-engine: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as error:
        print(f"umbra-engine: no engine answers on {API_HOST}:{settings.port} ({error})", file=sys.stderr)
        print("Start it with `umbra-engine serve`.", file=sys.stderr)
        return 1
    link = _login_link(settings, code, project_id)
    print(link)
    webbrowser.open_new_tab(link)
    return 0


class _EngineRefusedError(Exception):
    """The engine answered, and said no (a folder that cannot be a Project)."""


def _engine_call(settings: Settings, route: str, body: dict[str, str] | None) -> dict:
    import json
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        f"http://{API_HOST}:{settings.port}{route}",
        data=json.dumps(body or {}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {load_or_create_token(settings)}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code in (400, 409):
            raise _EngineRefusedError(json.loads(error.read()).get("detail", error.reason)) from error
        raise


def _login_link(settings: Settings, code: str, project_id: str | None = None) -> str:
    """The code sits in the fragment: browsers never send it to the server, so no log records it.
    With a Project, the page lands on it once signed in."""
    from urllib.parse import quote

    landing = f"&p={quote(project_id, safe='')}" if project_id else ""
    return f"http://{API_HOST}:{settings.port}/#login={code}{landing}"


if __name__ == "__main__":
    sys.exit(main())

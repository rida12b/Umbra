"""The Event Journal: what Claude Code did, as its hooks reported it (SPEC S5).

Each hook call drops one event file into Umbra's spool folder (written whole, then renamed: a power
cut leaves either nothing or a complete file). The engine ingests the spool into the Project the
event belongs to, once per event id (replaying the spool changes nothing), then removes the file.
Events are grouped into turns: a prompt, the files Claude edited, Claude's final message.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from umbra_engine.guard import redact_output
from umbra_engine.project_store import ProjectStore
from umbra_engine.registry import Project

SPOOL = "spool"  # under <UMBRA_HOME>/journal/
MAX_TEXT = 4000  # prompts and messages are kept short: they label a change, they are not a transcript
KINDS = ("prompt", "edit", "stop", "session_start", "session_end")
ABANDONED_TMP_S = 3600  # a hook writes its temporary file in milliseconds


@dataclass(frozen=True)
class Event:
    id: str
    at: str
    kind: str
    session: str
    cwd: str
    files: list[str] = field(default_factory=list)  # absolute paths, as Claude Code reported them
    text: str = ""  # the prompt, or Claude's final message
    tool: str = ""
    prompt_id: str = ""  # given by Claude Code to every hook call of one prompt: the surest link


@dataclass
class Turn:
    session: str
    started: str
    prompt: str = ""
    files: list[str] = field(default_factory=list)  # relative to the Project
    message: str = ""
    ended: str | None = None


def spool_folder(home: Path) -> Path:
    return home / "journal" / SPOOL


def read_event(path: Path) -> Event | None:
    """One spooled event, or None when the file is not a complete event (half-written temp files)."""
    if path.suffix != ".json":
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS or not raw.get("id"):
        return None
    files = [f for f in raw.get("files", []) if isinstance(f, str)]
    text = redact_output(str(raw.get("text", ""))[:MAX_TEXT], "claude hook")
    return Event(str(raw["id"]), str(raw.get("at", "")), raw["kind"], str(raw.get("session", "")),
                 str(raw.get("cwd", "")), files, text, str(raw.get("tool", "")),
                 str(raw.get("prompt_id", "")))  # fmt: skip


def belongs_to(event: Event, project: Project) -> bool:
    """Its session works in the Project, or it edits a file of the Project."""
    root = _norm(str(project.root))
    paths = [event.cwd, *event.files]
    return any(_norm(p) == root or _norm(p).startswith(root + "/") for p in paths if p)


def relative_files(event: Event, project: Project) -> list[str]:
    root = _norm(str(project.root))
    return [_norm(f)[len(root) + 1 :] for f in event.files if _norm(f).startswith(root + "/")]


def turns(events: list[Event], project: Project) -> list[Turn]:
    """A prompt opens a turn, edits join it, Claude's final message closes it. Events carrying Claude
    Code's prompt id join the turn of that prompt; others join the session's current turn, in time
    order. Edits seen without a prompt (a session already running) get a turn of their own."""
    result: list[Turn] = []
    by_prompt: dict[tuple[str, str], Turn] = {}
    current: dict[str, Turn] = {}  # per session, for events without a prompt id
    for event in sorted(events, key=lambda e: (e.at, e.id)):
        turn = (
            by_prompt.get((event.session, event.prompt_id)) if event.prompt_id else current.get(event.session)
        )
        if event.kind == "prompt" or (turn is None and event.kind == "edit"):
            turn = Turn(event.session, event.at, prompt=event.text if event.kind == "prompt" else "")
            result.append(turn)
            current[event.session] = turn
            if event.prompt_id:
                by_prompt[(event.session, event.prompt_id)] = turn
        if turn is None:
            continue
        if event.kind == "edit":
            turn.files += [f for f in relative_files(event, project) if f not in turn.files]
        elif event.kind == "stop":
            turn.message, turn.ended = event.text, event.at
            if current.get(event.session) is turn:
                del current[event.session]
    return sorted(result, key=lambda t: t.started, reverse=True)


def ingest(home: Path, projects: list[Project], open_store) -> dict[str, int]:
    """Move every complete spooled event into its Project's store; returns new events per Project id.
    An event is removed from the spool only after it is stored (a crash in between stores it again,
    which the event id makes harmless)."""
    folder = spool_folder(home)
    if not folder.is_dir():
        return {}
    added: dict[str, int] = {}
    for path in sorted(folder.iterdir()):
        event = read_event(path)
        if event is None:
            if path.suffix == ".json" or _abandoned(path):  # renamed whole: it can never become valid
                path.unlink(missing_ok=True)
            continue
        for project in (p for p in projects if belongs_to(event, p)):
            with open_store(project) as store:
                if store.add_event(_row(event)):
                    added[project.id] = added.get(project.id, 0) + 1
        path.unlink(missing_ok=True)
    return added


def stored_events(store: ProjectStore) -> list[Event]:
    return [
        Event(row[0], row[1], row[2], row[3], row[4], json.loads(row[5]), row[6], row[7], row[8])
        for row in store.events()
    ]


def _row(event: Event) -> tuple[str, ...]:
    return (
        event.id,
        event.at,
        event.kind,
        event.session,
        event.cwd,
        json.dumps(event.files),
        event.text,
        event.tool,
        event.prompt_id,
    )


def _abandoned(path: Path) -> bool:
    """A temporary file left by a hook that died before its rename."""
    try:
        return path.suffix == ".tmp" and time.time() - path.stat().st_mtime > ABANDONED_TMP_S
    except OSError:
        return False


def _norm(path: str) -> str:
    """Comparable form of a path as hooks write it on any platform: forward slashes, no case on Windows."""
    text = path.replace("\\", "/").rstrip("/")
    return text.lower() if len(text) > 1 and text[1] == ":" else text

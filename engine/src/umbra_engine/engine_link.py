"""A client of the running engine's local API, for the MCP server (`umbra-engine mcp`): it finds the Project
of the folder Claude Code works in and posts to it. Errors come back as plain sentences for Claude."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from umbra_engine.settings import API_HOST, Settings, load_or_create_token

TIMEOUT_S = 10.0
FOLDER_VARS = ("UMBRA_PROJECT_DIR", "CLAUDE_PROJECT_DIR")  # else the current directory


class EngineError(RuntimeError):
    """What went wrong, said so that Claude can act on it (start the engine, fix the parts, retry)."""


class EngineLink:
    def __init__(self, settings: Settings, folder: Path) -> None:
        self._settings = settings
        self._folder = folder
        self._base = f"http://{API_HOST}:{settings.port}"

    @classmethod
    def from_env(cls) -> "EngineLink":
        named = next((os.environ[v] for v in FOLDER_VARS if os.environ.get(v)), "")
        return cls(Settings.from_env(), Path(named) if named else Path.cwd())

    def project_id(self) -> str:
        """The registered Project that holds the working folder (the deepest one when they nest)."""
        here = _same(self._folder)
        best: tuple[int, str] | None = None
        for project in self._call("GET", "/v1/projects"):
            root = _same(Path(project["root"]))
            if here == root or here.startswith(root.rstrip(os.sep) + os.sep):
                if best is None or len(root) > best[0]:
                    best = (len(root), project["id"])
        if best is None:
            raise EngineError(
                f"this folder is not open in Umbra ({self._folder}): run /umbra first, it opens the map"
            )
        return best[1]

    def show(self, caption: str, parts: list[str], path: list[Any]) -> dict[str, Any]:
        project = self.project_id()
        body = {"caption": caption, "parts": parts, "path": path}
        return self._call("POST", f"/v1/projects/{project}/show", body)

    def _call(self, method: str, route: str, body: object | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {load_or_create_token(self._settings)}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self._base + route, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                return json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            raise EngineError(_detail(error)) from error
        except (urllib.error.URLError, OSError) as error:
            raise EngineError(
                f"Umbra's engine does not answer on {API_HOST}:{self._settings.port} ({error}): "
                "run /umbra to start it and open the map"
            ) from error


def _same(path: Path) -> str:
    """One spelling per folder: absolute, links resolved, case folded where the system ignores case."""
    return os.path.normcase(os.path.realpath(path))


def _detail(error: urllib.error.HTTPError) -> str:
    try:
        detail = json.loads(error.read()).get("detail")
    except (ValueError, AttributeError, OSError):
        detail = None
    if error.code == 409:
        return "Umbra is still reading this project: wait a few seconds and call show again"
    return str(detail) if detail else f"the engine answered {error.code} {error.reason}"

"""#104 end to end, on a real engine over HTTP: the `show` tool, called by an MCP client over stdio (as Claude
Code does), reaches the open tab through the live stream (`/events`) within 2 s. No Claude anywhere."""

import json
import os
import socket
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import anyio
import httpx
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session
from secret_fixtures import write_repo
from system_fixtures import TEMPLATE
from test_system import commit

import umbra_engine
from umbra_engine.api import create_app
from umbra_engine.engine_link import EngineError
from umbra_engine.mcp_server import build_server
from umbra_engine.settings import Settings, load_or_create_token

PRICE = "où j'ajoute un champ prix à Item ?"
PUSH_S = 2.0  # acceptance: the open tab lights up within 2 s


def no_claude(*_: object) -> str:
    raise AssertionError("show must never call Claude")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def engine(tmp_path: Path, make_repo) -> Iterator[tuple[Settings, str, Path]]:
    """A running engine on a free port with the template indexed: (settings, project id, project folder)."""
    settings = Settings(home=tmp_path / "home", port=free_port())
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings, ask=no_claude, study=no_claude), port=settings.port, log_level="error"
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    root = write_repo(make_repo("tpl"), TEMPLATE)
    commit(root, "2026-04-16")
    with httpx.Client(base_url=f"http://127.0.0.1:{settings.port}", headers=bearer(settings)) as api:
        project = api.post("/v1/projects", json={"path": str(root)}).json()["id"]
        assert api.post(f"/v1/projects/{project}/index").status_code == 200
        assert api.get(f"/v1/projects/{project}/system").status_code == 200
    yield settings, project, root
    server.should_exit = True
    thread.join(timeout=10)


def bearer(settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {load_or_create_token(settings)}"}


def test_a_show_reaches_the_open_tab_over_the_live_stream(engine):
    settings, project, _ = engine
    base = f"http://127.0.0.1:{settings.port}/v1/projects/{project}"
    seen: list[dict] = []

    def tab() -> None:  # what the page does: follow /events, read each `data:` line
        with httpx.stream("GET", f"{base}/events", headers=bearer(settings), timeout=10) as stream:
            for line in stream.iter_lines():
                if line.startswith("data: "):
                    seen.append(json.loads(line[6:]))
                    if seen[-1]["type"] == "cleared":
                        return

    follower = threading.Thread(target=tab, daemon=True)
    follower.start()
    time.sleep(0.5)  # the tab is open before the question is asked
    sent = time.monotonic()
    body = {"caption": PRICE, "parts": ["Base"], "path": ["backend/app/models.py"]}
    assert httpx.post(f"{base}/show", json=body, headers=bearer(settings)).status_code == 200
    while not seen and time.monotonic() - sent < PUSH_S:
        time.sleep(0.05)
    assert seen and seen[0]["type"] == "show", "the tab did not get the highlight within 2 s"
    assert seen[0]["highlight"]["caption"] == PRICE
    assert [s["label"] for s in seen[0]["highlight"]["steps"]] == ["models.py"]
    assert httpx.delete(f"{base}/show", headers=bearer(settings)).status_code == 200
    follower.join(timeout=PUSH_S)
    assert [e["type"] for e in seen] == ["show", "cleared"]


def test_claude_code_calls_show_over_stdio_and_the_map_lights_up(engine):
    """The MCP server as Claude Code starts it (`umbra-engine mcp`), driven by the Python MCP client."""
    settings, project, root = engine
    source = str(Path(str(umbra_engine.__file__)).parents[1])  # this checkout, not another installed copy
    env = {"UMBRA_HOME": str(settings.home), "UMBRA_PORT": str(settings.port), "PYTHONPATH": source}
    env["UMBRA_PROJECT_DIR"] = str(root / "backend")  # Claude Code may run in a subfolder of the Project
    server = StdioServerParameters(command=sys.executable, args=["-m", "umbra_engine.cli", "mcp"], env=env)

    async def session() -> tuple[list[str], str, str]:
        async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            tools = [t.name for t in (await client.list_tools()).tools]
            path = [{"part": "backend/app/models.py", "note": "ajouter le champ"}, "frontend/src/client/"]
            good = await client.call_tool("show", {"caption": PRICE, "parts": ["Base"], "path": path})
            bad = await client.call_tool("show", {"caption": PRICE, "parts": ["Serveurs"]})
            assert not good.isError and bad.isError
            return tools, good.content[0].text, bad.content[0].text  # type: ignore[union-attr]

    tools, said, refused = anyio.run(session)
    assert tools == ["show"]
    assert said.startswith("Shown on the map: 1 models.py (ajouter le champ); 2 client/; 3 boxes lit")
    assert "unknown part: 'Serveurs'" in refused and "server:backend (Serveur, backend/app/)" in refused
    lit = httpx.get(
        f"http://127.0.0.1:{settings.port}/v1/projects/{project}/show", headers=bearer(settings)
    ).json()
    assert lit["caption"] == PRICE and lit["files"] == ["backend/app/models.py", "frontend/src/client/"]
    assert os.environ.get("UMBRA_PROJECT_DIR") is None  # the test set it for the child only


class DownEngine:
    def show(self, caption, parts, path):
        raise EngineError("Umbra's engine does not answer on 127.0.0.1:7811: run /umbra to start it")


def test_an_engine_that_is_down_is_said_to_claude_not_raised():
    async def call() -> tuple[bool, str]:
        async with create_connected_server_and_client_session(build_server(DownEngine())) as client:
            result = await client.call_tool("show", {"caption": "x", "parts": ["Base"]})
            return result.isError, result.content[0].text  # type: ignore[union-attr]

    is_error, text = anyio.run(call)
    assert is_error and "run /umbra to start it" in text

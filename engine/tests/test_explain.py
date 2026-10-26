"""Explanation cards: only the critical paths — what reaches Claude, the child environment, the cache
and its invalidation, the budget. No real Claude call: a fake answers."""

import json
import time

import pytest
from fastapi.testclient import TestClient
from secret_fixtures import PLANTED, write_repo

from umbra_engine.api import create_app
from umbra_engine.gateways.claude import child_environment

FILES = {
    "app/main.py": "from .db import save\n\n\ndef handle(order):\n    return save(order)\n",
    "app/db.py": f'TOKEN = "{PLANTED["github"]}"\n\n\ndef save(order):\n    return order\n',
    ".env": f"API_TOKEN={PLANTED['env_file']}\n",
}
CARD = {
    "role": "Enregistre une commande.",
    "entrees": ["une commande"],
    "sorties": ["la commande enregistree"],
    "etapes": [
        {"texte": "appelle save", "fichier": "app/main.py", "lignes": [4, 5]},
        {"texte": "x", "lignes": [9, 2]},
    ],
    "points_entree": [{"nom": "handle", "fichier": "app/main.py", "lignes": [4, 5]}],
    "depend_de": ["app/db.py"],
    "enfants": {"app": "le code", "dir:invented": "inventé"},
    "incertitudes": [],
}


class FakeClaude:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "Here it is:\n" + json.dumps(CARD)


@pytest.fixture
def fake() -> FakeClaude:
    return FakeClaude()


@pytest.fixture
def setup(settings, auth, make_repo, fake):
    root = write_repo(make_repo("shop"), FILES, git=False)
    client = TestClient(create_app(settings, ask=fake), base_url="http://127.0.0.1")
    project = client.post("/v1/projects", json={"path": str(root)}, headers=auth).json()["id"]
    assert client.post(f"/v1/projects/{project}/index", headers=auth).status_code == 200
    return client, project, root


def explain(client, auth, project, node="app:", method="get") -> dict:
    url = f"/v1/projects/{project}/explain"
    response = client.request(method.upper(), url, params={"node": node}, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def settle(client, auth, project, node="app:") -> dict:
    for _ in range(100):
        state = explain(client, auth, project, node)
        if state["state"] not in ("queued", "working"):
            return state
        time.sleep(0.05)
    raise AssertionError("the card never finished")


def test_claude_never_sees_secrets_or_excluded_files(setup, auth, fake):
    client, project, _ = setup
    for node in ("app:", "dir:app", "app/db.py", "app/main.py::handle"):
        explain(client, auth, project, node, "post")
        settle(client, auth, project, node)
    sent = "\n".join(fake.prompts)
    assert len(fake.prompts) == 4
    assert PLANTED["github"] not in sent and PLANTED["env_file"] not in sent
    assert "def save(order)" in sent  # the code itself is shown, as released by the Secret Guard


def test_child_environment_cannot_switch_to_an_api_key():
    env = child_environment(
        {"PATH": "x", "ANTHROPIC_API_KEY": "k", "ANTHROPIC_AUTH_TOKEN": "t", "CLAUDE_CODE_OAUTH_TOKEN": "o",
         "CLAUDE_CODE_USE_BEDROCK": "1"}
    )  # fmt: skip
    assert env == {"PATH": "x", "UMBRA_CHILD": "1"}


def test_a_card_is_reused_until_its_code_changes(setup, auth, fake):
    client, project, root = setup
    assert explain(client, auth, project, "app/main.py")["state"] == "missing"
    explain(client, auth, project, "app/main.py", "post")
    ready = settle(client, auth, project, "app/main.py")
    assert ready["state"] == "ready" and ready["card"]["role"] == CARD["role"]
    assert ready["card"]["etapes"][1]["lignes"] is None  # an impossible line range is dropped

    explain(client, auth, project, "app/main.py", "post")
    assert len(fake.prompts) == 1  # up to date: no new call

    (root / "app/main.py").write_text("def handle(order):\n    return None\n")
    assert explain(client, auth, project, "app/main.py")["state"] == "stale"  # read live, before re-indexing
    explain(client, auth, project, "app/main.py", "post")
    assert settle(client, auth, project, "app/main.py")["state"] == "ready"
    assert len(fake.prompts) == 2


def test_child_roles_are_kept_only_for_real_children(setup, auth):
    client, project, _ = setup
    explain(client, auth, project, "app:", "post")
    assert settle(client, auth, project)["card"]["enfants"] == {"dir:app": "le code"}


def test_the_daily_budget_stops_background_calls(setup, auth, fake):
    client, project, _ = setup
    client.app.state.explainer._budget = 1  # noqa: SLF001 — test knob
    explain(client, auth, project, "app/main.py", "post")
    settle(client, auth, project, "app/main.py")
    refused = explain(client, auth, project, "app/db.py", "post")
    assert refused["state"] == "error" and "budget" in refused["message"]
    assert len(fake.prompts) == 1


def test_a_machine_without_claude_code_is_told_so_in_plain_words(monkeypatch):
    """#98: a first-time user saw « claude did not answer: FileNotFoundError »."""
    import subprocess

    import pytest

    from umbra_engine.gateways import claude

    def missing(*args, **kwargs):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(claude.ClaudeUnavailableError, match="not installed on this machine"):
        claude.ask("hello")
    assert "not installed" in (claude.readiness_problem() or "")

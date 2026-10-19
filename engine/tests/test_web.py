"""The web app's access: one-time login codes, header sessions, and the token never in a URL."""

import pytest
from fastapi.testclient import TestClient

from umbra_engine import web
from umbra_engine.api import create_app
from umbra_engine.ui_session import LOGIN_CODE_TTL, SESSION_HEADER, UiSessions


def login(client: TestClient, code: str):
    return client.post("/v1/ui/session", json={"code": code})


@pytest.fixture
def code(client, auth) -> str:
    return client.post("/v1/ui/login-codes", headers=auth).json()["code"]


def test_a_login_code_opens_one_session_once(client, code):
    response = login(client, code)
    assert response.status_code == 200
    session = response.json()["session"]
    assert "set-cookie" not in response.headers

    assert client.get("/v1/projects", headers={SESSION_HEADER: session}).status_code == 200
    assert login(client, code).status_code == 401  # used
    assert client.get("/v1/projects", headers={SESSION_HEADER: "forged"}).status_code == 401


def test_no_ambient_credential_is_accepted(client, code):
    """Browsers send cookies to every port of 127.0.0.1: a session must never ride on a cookie."""
    session = login(client, code).json()["session"]
    client.cookies.set("umbra_session", session)
    assert client.get("/v1/projects").status_code == 401


def test_minting_login_codes_needs_the_token(client):
    assert client.post("/v1/ui/login-codes").status_code == 401
    assert login(client, "made-up").status_code == 401


def test_login_codes_expire():
    now = [1000.0]
    sessions = UiSessions(clock=lambda: now[0])
    code = sessions.new_login_code()
    now[0] += LOGIN_CODE_TTL + 1
    assert sessions.redeem(code) is None


def test_sessions_do_not_survive_a_restart(settings, client, code):
    session = login(client, code).json()["session"]
    restarted = TestClient(create_app(settings), base_url="http://127.0.0.1")
    assert restarted.get("/v1/projects", headers={SESSION_HEADER: session}).status_code == 401


def test_the_built_app_is_served_and_its_absence_is_explained(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(web, "WEB_ROOT", tmp_path / "missing")
    missing = TestClient(create_app(settings), base_url="http://127.0.0.1").get("/")
    assert missing.status_code == 503 and "npm run build" in missing.text

    built = tmp_path / "built"
    built.mkdir()
    (built / "index.html").write_text("<!doctype html><title>Umbra</title>")
    monkeypatch.setattr(web, "WEB_ROOT", built)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    assert "<title>Umbra</title>" in client.get("/").text
    assert client.get("/v1/health").json()["status"] == "ok"  # the mount at `/` does not shadow the API

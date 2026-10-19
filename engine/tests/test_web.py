"""The web app's access: one-time login codes, HttpOnly sessions, and the token never in a URL."""

import pytest
from fastapi.testclient import TestClient

from umbra_engine import web
from umbra_engine.api import create_app
from umbra_engine.ui_session import LOGIN_CODE_TTL, SESSION_COOKIE, UI_CLIENT_HEADER, UiSessions

UI = {UI_CLIENT_HEADER: "web"}


def login(client: TestClient, code: str):
    return client.post("/v1/ui/session", json={"code": code})


@pytest.fixture
def code(client, auth) -> str:
    return client.post("/v1/ui/login-codes", headers=auth).json()["code"]


def test_a_login_code_opens_one_httponly_session_once(client, code):
    response = login(client, code)
    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/v1" in cookie

    assert client.get("/v1/projects", headers=UI).status_code == 200
    assert login(client, code).status_code == 401  # used


def test_a_session_needs_the_ui_header(client, code):
    """Another page on 127.0.0.1 is same-site: the cookie alone must not be enough."""
    login(client, code)
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
    login(client, code)
    session = client.cookies[SESSION_COOKIE]
    restarted = TestClient(create_app(settings), base_url="http://127.0.0.1")
    restarted.cookies.set(SESSION_COOKIE, session)
    assert restarted.get("/v1/projects", headers=UI).status_code == 401


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

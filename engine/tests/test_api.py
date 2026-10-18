import pytest


def test_health_needs_no_token(client):
    assert client.get("/v1/health").json()["status"] == "ok"


@pytest.mark.parametrize(
    ("method", "url"),
    [("GET", "/v1/projects"), ("POST", "/v1/projects"), ("GET", "/v1/projects/any")],
)
def test_project_endpoints_reject_missing_or_wrong_token(client, method, url):
    assert client.request(method, url, json={"path": "."}).status_code == 401
    wrong = {"Authorization": "Bearer wrong"}
    assert client.request(method, url, json={"path": "."}, headers=wrong).status_code == 401


def test_token_in_query_string_is_not_accepted(client, auth):
    token = auth["Authorization"].removeprefix("Bearer ")
    assert client.get("/v1/projects", params={"token": token}).status_code == 401


@pytest.mark.parametrize("presented", ["", " ", "é", "Bearer"])
def test_empty_or_non_ascii_tokens_get_401_not_500(client, presented):
    headers = {"Authorization": f"Bearer {presented}".encode()}
    assert client.get("/v1/projects", headers=headers).status_code == 401


@pytest.mark.parametrize("path", ["", ".", "relative/dir"])
def test_relative_paths_are_rejected(client, auth, path):
    response = client.post("/v1/projects", json={"path": path}, headers=auth)
    assert response.status_code == 400


def test_register_list_and_get(client, auth, make_repo):
    repo = make_repo("billing")

    created = client.post("/v1/projects", json={"path": str(repo)}, headers=auth)
    assert created.status_code == 200
    project = created.json()

    assert client.post("/v1/projects", json={"path": str(repo)}, headers=auth).json()["id"] == project["id"]
    assert [p["id"] for p in client.get("/v1/projects", headers=auth).json()] == [project["id"]]
    assert client.get(f"/v1/projects/{project['id']}", headers=auth).json() == project


def test_missing_path_returns_400_with_reason(client, auth, tmp_path):
    response = client.post("/v1/projects", json={"path": str(tmp_path / "nope")}, headers=auth)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_unknown_project_returns_404(client, auth):
    assert client.get("/v1/projects/unknown-1234", headers=auth).status_code == 404


def test_a_project_endpoint_only_returns_that_project(client, auth, make_repo):
    a = client.post("/v1/projects", json={"path": str(make_repo("a"))}, headers=auth).json()
    b = client.post("/v1/projects", json={"path": str(make_repo("b"))}, headers=auth).json()

    assert client.get(f"/v1/projects/{a['id']}", headers=auth).json()["root"] == a["root"]
    assert client.get(f"/v1/projects/{b['id']}", headers=auth).json()["root"] == b["root"]
    assert a["root"] != b["root"]


@pytest.mark.parametrize("host", ["evil.example", "127.0.0.1.nip.io", "attacker.localhost.example"])
def test_requests_for_another_host_name_are_refused(client, auth, host):
    """DNS rebinding: a page on a foreign host name that resolves to 127.0.0.1 must not reach the API."""
    for url in ("/v1/health", "/v1/projects"):
        assert client.get(url, headers={**auth, "Host": host}).status_code == 400


def test_localhost_by_name_is_accepted(client, auth):
    assert client.get("/v1/projects", headers={**auth, "Host": "localhost:7811"}).status_code == 200

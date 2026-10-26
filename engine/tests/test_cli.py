from umbra_engine import cli


def test_add_prints_id_then_reports_already_registered(settings, make_repo, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    repo = make_repo("watchdog")

    assert cli.main(["add", str(repo)]) == 0
    first = capsys.readouterr().out
    assert first.startswith("added: watchdog-")

    assert cli.main(["add", str(repo)]) == 0
    assert capsys.readouterr().out.startswith("already registered: watchdog-")


def test_add_missing_path_exits_2_with_message(settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))

    assert cli.main(["add", str(tmp_path / "nope")]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_serve_uses_loopback_host(settings, monkeypatch):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    seen = {}

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda app, host, port, log_level: seen.update(host=host, port=port))
    assert cli.main(["serve"]) == 0
    assert seen["host"] == "127.0.0.1"


def test_non_ascii_paths_survive_piped_output(settings, make_repo, monkeypatch):
    import os
    import subprocess
    import sys

    repo = make_repo("projé ünï 日本")
    env = {**os.environ, "UMBRA_HOME": str(settings.home), "PYTHONIOENCODING": ""}
    for args in (["add", str(repo)], ["list"]):
        result = subprocess.run(
            [sys.executable, "-m", "umbra_engine.cli", *args], env=env, capture_output=True
        )
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        assert "projé ünï 日本" in result.stdout.decode("utf-8")


def test_add_empty_path_exits_2(settings, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["add", ""]) == 2
    assert "empty" in capsys.readouterr().err


def test_engine_errors_are_one_line_messages_not_tracebacks(settings, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    settings.home.mkdir(parents=True)
    (settings.home / "token").write_text("")
    monkeypatch.setattr("umbra_engine.settings.TOKEN_READ_RETRIES", 1)
    assert cli.main(["token"]) == 1
    assert capsys.readouterr().err.startswith("umbra-engine: empty token file")


def test_start_registers_indexes_and_serves_a_link_that_lands_on_the_project(
    settings, make_repo, monkeypatch, capsys
):
    """#98: one command from a folder to the web app, on that Project."""
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    repo = make_repo("watchdog")
    seen = {}

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda app, host, port, log_level: seen.update(host=host))
    monkeypatch.setattr("umbra_engine.gateways.claude.readiness_problem", lambda: None)
    assert cli.main(["start", str(repo), "--no-browser"]) == 0
    out = capsys.readouterr().out
    project_id = out.split("indexed ", 1)[1].split(":", 1)[0]
    assert project_id.startswith("watchdog-")
    assert "#login=" in out and f"&p={project_id}" in out
    assert seen["host"] == "127.0.0.1"
    assert "Warning" not in out

    assert cli.main(["start", str(repo), "--no-browser"]) == 0  # a second run reuses the same Project
    assert f"indexed {project_id}:" in capsys.readouterr().out


def test_start_says_when_claude_code_is_missing_and_still_serves(settings, make_repo, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    repo = make_repo("watchdog")

    import subprocess

    import uvicorn

    def no_claude(*args, **kwargs):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(uvicorn, "run", lambda app, host, port, log_level: None)
    monkeypatch.setattr(subprocess, "run", no_claude)
    assert cli.main(["start", str(repo), "--no-browser"]) == 0
    assert "Claude Code is not installed on this machine" in capsys.readouterr().out


def test_start_on_a_missing_folder_exits_2(settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UMBRA_HOME", str(settings.home))
    assert cli.main(["start", str(tmp_path / "nope"), "--no-browser"]) == 2
    assert "does not exist" in capsys.readouterr().err

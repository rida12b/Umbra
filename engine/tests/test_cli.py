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

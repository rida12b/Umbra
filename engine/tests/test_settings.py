import threading

import pytest

from umbra_engine.settings import TOKEN_FILE, TokenFileError, load_or_create_token


def test_token_is_created_once_and_reused(settings):
    first = load_or_create_token(settings)
    assert len(first) >= 32
    assert load_or_create_token(settings) == first


def test_concurrent_first_use_yields_one_token(settings):
    tokens: list[str] = []
    threads = [
        threading.Thread(target=lambda: tokens.append(load_or_create_token(settings))) for _ in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(tokens)) == 1
    assert [p.name for p in settings.home.iterdir()] == [TOKEN_FILE]


def test_empty_token_file_is_an_error_not_an_open_door(settings):
    settings.home.mkdir(parents=True)
    (settings.home / TOKEN_FILE).write_text("  \n")
    with pytest.raises(TokenFileError):
        load_or_create_token(settings)


def test_token_is_created_on_filesystems_without_hard_links(settings, monkeypatch):
    import os

    def no_links(*_args):
        raise OSError("hard links not supported")

    monkeypatch.setattr(os, "link", no_links)
    token = load_or_create_token(settings)
    assert token and load_or_create_token(settings) == token
    assert sorted(p.name for p in settings.home.iterdir()) == [TOKEN_FILE]

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from umbra_engine.api import create_app
from umbra_engine.settings import Settings, load_or_create_token


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(home=tmp_path / "umbra-home")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def auth(settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {load_or_create_token(settings)}"}


@pytest.fixture
def make_repo(tmp_path: Path):
    def _make(name: str) -> Path:
        path = tmp_path / "repos" / name
        path.mkdir(parents=True)
        return path

    return _make

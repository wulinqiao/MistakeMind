import pytest


@pytest.fixture(autouse=True)
def offline_by_default(monkeypatch):
    """A developer's local .env/key must never make pytest send paid requests."""
    monkeypatch.setenv("AGENT_MODE", "mock")

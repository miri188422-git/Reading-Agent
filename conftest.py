import pytest


@pytest.fixture(autouse=True)
def clean_data_dir(tmp_path, monkeypatch):
    """Every test runs on its own empty data dir."""
    monkeypatch.setenv("READING_AGENT_DATA", str(tmp_path))
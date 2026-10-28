"""Persistent state for the reading agent. Shared by API/ and SDK/."""
import json
import os
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "data"


def data_dir() -> Path:
    """Where state lives. Override with READING_AGENT_DATA (tests, clean runs)."""
    d = Path(os.environ.get("READING_AGENT_DATA", DEFAULT_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(name: str) -> Path:
    return data_dir() / f"{name}.json"


def load(name: str, default):
    p = _path(name)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save(name: str, value) -> None:
    p = _path(name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)  # atomic replace, so a crash never leaves a half-written file
"""User configuration manager.

Persists last-used settings to ~/.noveltrad/config.json (CDC §6 arborescence,
config.json). Privacy note: the api_key is stored locally only; remote use is
always opt-in (provider != "ollama").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    return Path.home() / ".noveltrad"


def _config_path() -> Path:
    return _config_dir() / "config.json"


DEFAULTS: dict[str, Any] = {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "ollama_host": "http://localhost:11434",
    "remote_base_url": "",
    "api_key": "",
    "source_lang": "Anglais",
    "target_lang": "Français",
    "profile": "Général",
    "expert_mode": True,  # True = 4 agents, False = Mode Rapide (1 agent)
    "check_updates_on_startup": True,
}


class Config:
    """Singleton-ish config backed by a JSON file."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        path = _config_path()
        if path.exists():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass  # corrupt file -> keep defaults

    def save(self) -> None:
        _config_dir().mkdir(parents=True, exist_ok=True)
        _config_path().write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, **kwargs: Any) -> None:
        self._data.update(kwargs)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

"""Application configuration for the v4 PyQt client.

The v4 app only needs a small JSON-backed store shared by the first-run wizard
and the settings tab.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


class ConfigManager:
    """Small singleton JSON config store for the desktop client."""

    _instance: "ConfigManager | None" = None
    CONFIG_FILE = (
        Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        / "NovelTrad"
        / "config.json"
    )
    INSTALLER_LANGUAGE_FILE = (
        Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        / "NovelTrad"
        / "installer_language.txt"
    )
    LEGACY_CONFIG_FILE = Path("config.json")

    DEFAULT_CONFIG: dict[str, Any] = {
        "first_run": True,
        "workspace_dir": str(Path.home() / "Documents" / "NovelTradProjects"),
        "ui": {"dark": True, "language": "en"},
        "llm": {
            "provider": "ollama",
            "model": "gemma3:4b",
            "base_url": "http://127.0.0.1:11434",
            "api_key": "",
            "parallel": 1,
            "draft_fallback": False,
        },
        "nllb": {
            "model": "facebook/nllb-200-distilled-600M",
            "device": "auto",
        },
    }

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = cls._instance.load_config()
        return cls._instance

    def load_config(self) -> dict[str, Any]:
        path = self.CONFIG_FILE
        if not path.exists() and self.LEGACY_CONFIG_FILE.exists():
            path = self.LEGACY_CONFIG_FILE
        if not path.exists():
            config = copy.deepcopy(self.DEFAULT_CONFIG)
            installer_lang = self._installer_language()
            if installer_lang:
                config.setdefault("ui", {})["language"] = installer_lang
            return config
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return copy.deepcopy(self.DEFAULT_CONFIG)
        return _deep_merge(copy.deepcopy(self.DEFAULT_CONFIG), loaded)

    def _installer_language(self) -> str:
        try:
            raw = self.INSTALLER_LANGUAGE_FILE.read_text(encoding="utf-8")
        except OSError:
            return ""
        code = raw.strip().lower()
        if code.startswith("fr"):
            return "fr"
        if code.startswith("en"):
            return "en"
        return ""

    def save_config(self) -> None:
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with self.CONFIG_FILE.open("w", encoding="utf-8") as handle:
                json.dump(self.config, handle, indent=4)
        except OSError as exc:
            print(f"Error saving config: {exc}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()

    def is_first_run(self) -> bool:
        return bool(self.config.get("first_run", True))

    def set_first_run_complete(self) -> None:
        self.config["first_run"] = False
        self.save_config()

    def apply_environment(self) -> None:
        llm = dict(self.config.get("llm", {}) or {})
        nllb = dict(self.config.get("nllb", {}) or {})
        provider = llm.get("provider", "ollama")
        model = llm.get("model", "gemma3:4b")
        base_url = llm.get("base_url", "http://127.0.0.1:11434")
        if provider == "ollama":
            os.environ["OLLAMA_BASE_URL"] = base_url
            os.environ["OLLAMA_MODEL"] = model
            os.environ["OLLAMA_PARALLEL"] = str(llm.get("parallel", 1))
        else:
            os.environ["OPENAI_BASE_URL"] = base_url
            os.environ["OPENAI_MODEL"] = model
            if llm.get("api_key"):
                os.environ["OPENAI_API_KEY"] = str(llm["api_key"])
            os.environ["OPENAI_PARALLEL"] = str(llm.get("parallel", 4))
        os.environ["NOVELTRAD_LLM_DRAFT_ON_NLLB_MISSING"] = (
            "1" if llm.get("draft_fallback") else "0"
        )
        os.environ["NLLB_MODEL"] = str(
            nllb.get("model", "facebook/nllb-200-distilled-600M")
        )
        os.environ["NLLB_DEVICE"] = str(nllb.get("device", "auto"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


__all__ = ["ConfigManager"]

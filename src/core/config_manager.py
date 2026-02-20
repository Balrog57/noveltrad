import json
import os
from pathlib import Path

class ConfigManager:
    _instance = None
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "first_run": True,
        "theme": "dark",
        "workspace_dir": str(Path.home() / "Documents" / "NovelTradProjects"),
        "api_keys": {
            "openai": "",
            "gemini": "",
            "anthropic": ""
        },
        "llm_provider": "gemini",
        "target_language": "fr"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.config = cls._instance.load_config()
        return cls._instance

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            return self.DEFAULT_CONFIG.copy()
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**self.DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, IOError, OSError):
            return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def is_first_run(self):
        return self.config.get("first_run", True)

    def set_first_run_complete(self):
        self.config["first_run"] = False
        self.save_config()

import os
import json

class ShortcutManager:
    """
    Manages application keyboard shortcuts.
    Allows users to customize key bindings and persists them to a JSON file.
    """
    DEFAULT_SHORTCUTS = {
        "new_project": "Ctrl+N",
        "open_project": "Ctrl+O",
        "save_segment": "Ctrl+S",
        "batch_translate": "Ctrl+Shift+C",
        "search_replace": "Ctrl+F",
        "glossary_scan": "Ctrl+G",
        "auto_translate": "Ctrl+R",
        "ai_refine": "Ctrl+E",
        "settings": "Ctrl+,",
        "statistics": "F5",
        "confirm_segment": "Ctrl+Return",
        "prev_segment": "Ctrl+Up",
        "next_segment": "Ctrl+Down",
        "backups": "Ctrl+B",
        "qa_check": "Ctrl+Q"
    }

    def __init__(self, config_dir=None):
        if not config_dir:
            # Standard location for config
            config_dir = os.path.join(os.path.expanduser("~"), ".noveltrad")
            
        self.config_path = os.path.join(config_dir, "shortcuts.json")
        self.shortcuts = self.DEFAULT_SHORTCUTS.copy()
        self.load()

    def load(self):
        """Loads user-defined shortcuts from the config file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_shortcuts = json.load(f)
                    # We only update if the keys exist in our defaults (prevention against junk data)
                    for k, v in user_shortcuts.items():
                        if k in self.DEFAULT_SHORTCUTS:
                            self.shortcuts[k] = v
            except Exception:
                # Silently fail and use defaults if file is corrupt
                pass

    def save(self):
        """Saves current shortcuts to the config file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.shortcuts, f, indent=4)
        except Exception:
            pass

    def get(self, action_name):
        """Returns the shortcut for a given action."""
        return self.shortcuts.get(action_name, self.DEFAULT_SHORTCUTS.get(action_name))

    def set(self, action_name, key_sequence):
        """Updates and saves a shortcut."""
        if action_name in self.DEFAULT_SHORTCUTS:
            self.shortcuts[action_name] = key_sequence
            self.save()

    def reset_to_defaults(self):
        """Resets all shortcuts to their factory defaults."""
        self.shortcuts = self.DEFAULT_SHORTCUTS.copy()
        self.save()

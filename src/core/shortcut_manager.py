import os
import json

class ShortcutManager:
    """
    Manages application keyboard shortcuts.
    Allows users to customize key bindings and persists them to a TOML file.
    """
    DEFAULT_SHORTCUTS = {
        "navigation": {
            "prev_segment": "Ctrl+Up",
            "next_segment": "Ctrl+Down",
            "next_auto_populated": "Ctrl+Alt+,",
            "prev_auto_populated": "Ctrl+Alt+<",
            "next_enforced": "Ctrl+Alt+.",
            "prev_enforced": "Ctrl+Alt+>",
            "history_back": "Ctrl+Shift+P",
            "history_forward": "Ctrl+Shift+N",
        },
        "translation": {
            "auto_translate": "Ctrl+R",
            "insert_fuzzy": "Ctrl+I",
            "translate_chapter": "Ctrl+Shift+T",
            "ai_refine": "Ctrl+E",
            "mt_translate": "Ctrl+Alt+T",
            "regenerate_suggestion": "Ctrl+G",
            "batch_translate": "Ctrl+Shift+C",
            "confirm_segment": "Ctrl+Return",
        },
        "edit": {
            "undo": "Ctrl+Z",
            "redo": "Ctrl+Y",
            "search_replace": "Ctrl+F",
            "search_prev": "Shift+F3",
            "search_next": "F3",
        },
        "project": {
            "new_project": "Ctrl+Shift+N",
            "open_project": "Ctrl+O",
            "save_segment": "Ctrl+S",
            "save_all": "Ctrl+Shift+S",
            "export_project": "Ctrl+E",
            "settings": "Ctrl+,",
            "statistics": "F5",
            "backups": "Ctrl+B",
            "qa_check": "Ctrl+Q",
        },
        "glossary": {
            "open_glossary": "Ctrl+Alt+G",
            "add_to_glossary": "Ctrl+G",
            "search_glossary": "Ctrl+Alt+F",
            "glossary_scan": "Ctrl+Shift+G",
        },
        "dictionary": {
            "open_dictionary": "Alt+Shift+D",
            "search_dictionary": "Ctrl+D",
        },
        "alignment": {
            "open_alignment": "Ctrl+Shift+A",
            "split_segment": "Ctrl+Alt+S",
        },
        "tags": {
            "tag_painter": "Ctrl+Shift+T", 
            "next_missing_tag": "Ctrl+T",
            "lock_cursor": "F2",
        }
    }

    def __init__(self, main_window=None):
        self.main_window = main_window
        config_dir = os.path.join(os.path.expanduser("~"), ".noveltrad")
        self.config_path = os.path.join(config_dir, "shortcuts.toml")
        
        from PyQt6.QtGui import QShortcut, QKeySequence
        self._qshortcut_cls = QShortcut
        self._qkeysequence_cls = QKeySequence
        
        self.shortcuts = {}
        self._flat_shortcuts = {}
        self.active_qshortcuts = {} # action_name -> (QShortcut, callback)
        
        self.reset_to_defaults()
        if os.path.exists(self.config_path):
            self.load_shortcuts_from_file(self.config_path)

    def init_shortcuts(self):
        """Called to initialize standard bindings after UI is loaded."""
        pass

    def register_shortcut(self, action_name, keyseq, callback):
        """Registers a shortcut and its callback."""
        if not self.main_window:
            return
            
        if not keyseq:
            keyseq = self._flat_shortcuts.get(action_name)
            
        if not keyseq:
            return
            
        # Recreate shortcut if exists
        if action_name in self.active_qshortcuts:
            old_shortcut, old_cb = self.active_qshortcuts[action_name]
            old_shortcut.setParent(None)
            old_shortcut.deleteLater()
            
        from PyQt6.QtCore import Qt
        shortcut = self._qshortcut_cls(self._qkeysequence_cls(keyseq), self.main_window)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(callback)
        self.active_qshortcuts[action_name] = (shortcut, callback)
        
        self._flat_shortcuts[action_name] = keyseq

    def _read_toml(self, path):
        data = {}
        current_section = None
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].strip()
                    data[current_section] = {}
                elif '=' in line and current_section:
                    k, v = line.split('=', 1)
                    data[current_section][k.strip()] = v.strip().strip('"').strip("'")
        return data

    def _write_toml(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            for section, keys in data.items():
                f.write(f"[{section}]\n")
                for k, v in keys.items():
                    val = str(v).replace('"', '\\"')
                    f.write(f'{k} = "{val}"\n')
                f.write("\n")

    def load_shortcuts_from_file(self, path):
        try:
            user_shortcuts = self._read_toml(path)
            for category, bindings in user_shortcuts.items():
                if category in self.shortcuts:
                    for k, v in bindings.items():
                        if k in self.shortcuts[category]:
                            self.shortcuts[category][k] = v
                            self._flat_shortcuts[k] = v
        except Exception as e:
            print(f"Error loading shortcuts from {path}: {e}")

    def save_shortcuts_to_file(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            self._write_toml(path, self.shortcuts)
        except Exception as e:
            print(f"Error saving shortcuts to {path}: {e}")
            
    def get_all_shortcuts(self) -> dict:
        return self.shortcuts
        
    def get(self, action_name):
        return self._flat_shortcuts.get(action_name, "")
        
    def set(self, action_name, key_sequence):
        for cat, bindings in self.shortcuts.items():
            if action_name in bindings:
                bindings[action_name] = key_sequence
                self._flat_shortcuts[action_name] = key_sequence
                if action_name in self.active_qshortcuts:
                    _, cb = self.active_qshortcuts[action_name]
                    self.register_shortcut(action_name, key_sequence, cb)
                break
        self.save_shortcuts_to_file(self.config_path)

    def reset_to_defaults(self):
        import copy
        self.shortcuts = copy.deepcopy(self.DEFAULT_SHORTCUTS)
        self._flat_shortcuts = {}
        for cat, bindings in self.shortcuts.items():
            for k, v in bindings.items():
                self._flat_shortcuts[k] = v
        self.save_shortcuts_to_file(self.config_path)

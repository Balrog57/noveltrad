from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QTabWidget, QWidget, QFormLayout, QFileDialog)
from src.gui.shortcut_config_dialog import ShortcutConfigDialog
from PyQt6.QtCore import Qt
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 450)
        
        self.layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # General Tab
        self.general_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        self.init_general_tab()
        
        # Translation Tab
        self.translation_tab = QWidget()
        self.tabs.addTab(self.translation_tab, "Translation")
        self.init_translation_tab()
        
        # Appearance Tab
        self.appearance_tab = QWidget()
        self.tabs.addTab(self.appearance_tab, "Appearance")
        self.init_appearance_tab()
        
        # Tools Tab
        self.tools_tab = QWidget()
        self.tabs.addTab(self.tools_tab, "Language Store")
        self.init_tools_tab()
        
        # Shortcuts Tab
        self.shortcuts_tab = QWidget()
        self.tabs.addTab(self.shortcuts_tab, "Shortcuts")
        self.init_shortcuts_tab()
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)
        btns.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        
        self.layout.addLayout(btns)
        
        self.load_settings()
        
    def save_and_close(self):
        self.save_settings()
        self.accept()
        
    def get_config_path(self):
        return CONFIG_FILE

    def init_general_tab(self):
        layout = QFormLayout(self.general_tab)
        
        self.backup_check = QCheckBox("Enable Automatic Backups")
        layout.addRow(self.backup_check)
        
        self.backup_interval = QComboBox()
        self.backup_interval.addItems(["Every 5 mins", "Every 15 mins", "Every hour"])
        layout.addRow("Backup Interval:", self.backup_interval)

    def init_translation_tab(self):
        layout = QFormLayout(self.translation_tab)
        
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Argos Translate (Offline)", "NLLB (Offline)", "LLM (Online/Local)"])
        layout.addRow("Default Engine:", self.engine_combo)
        
        # LLM Settings
        layout.addRow(QLabel("<b>LLM Settings</b>"))
        self.llm_url = QLineEdit("http://localhost:1234/v1")
        layout.addRow("API Base URL:", self.llm_url)
        self.llm_key = QLineEdit("lm-studio")
        self.llm_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API Key:", self.llm_key)
        self.llm_model = QLineEdit("gemma-2-9b-it")
        layout.addRow("Model Name:", self.llm_model)

    def init_tools_tab(self):
        layout = QVBoxLayout(self.tools_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(15)
        
        layout.addWidget(QLabel("<b>Resource Management</b>"))
        
        btn_store = QPushButton("Open Language Store")
        btn_store.setToolTip("Download and install offline models (Argos, NLLB)")
        btn_store.setMinimumHeight(40)
        btn_store.clicked.connect(self.open_store)
        layout.addWidget(btn_store)
        
    def init_shortcuts_tab(self):
        layout = QVBoxLayout(self.shortcuts_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label = QLabel("Configurez vos raccourcis clavier pour une productivité maximale.")
        label.setWordWrap(True)
        label.setStyleSheet("color: #94a3b8; font-style: italic; margin-bottom: 20px;")
        layout.addWidget(label)
        
        btn_shortcuts = QPushButton("Modifier les Raccourcis...")
        btn_shortcuts.setMinimumHeight(50)
        btn_shortcuts.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold;")
        btn_shortcuts.clicked.connect(self.open_shortcuts_config)
        layout.addWidget(btn_shortcuts)
        
        layout.addStretch()

    def open_shortcuts_config(self):
        if self.parent() and hasattr(self.parent(), 'shortcut_manager'):
            dialog = ShortcutConfigDialog(self.parent().shortcut_manager, self)
            if dialog.exec():
                # Trigger shortcut refresh in main window
                if hasattr(self.parent(), 'setup_shortcuts'):
                    self.parent().setup_shortcuts()
        else:
            QMessageBox.warning(self, "Erreur", "Manager de raccourcis non trouvé.")

    def open_store(self):
        self.accept()
        if self.parent() and hasattr(self.parent(), 'show_language_store'):
            self.parent().show_language_store()


    def init_appearance_tab(self):
        layout = QFormLayout(self.appearance_tab)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "High Contrast", "Deuteranopia", "Protanopia", "Tritanopia"])
        layout.addRow("Theme:", self.theme_combo)
        
        self.font_size = QComboBox()
        self.font_size.addItems(["Small", "Medium", "Large"])
        self.font_size.setCurrentText("Medium")
        layout.addRow("Font Size:", self.font_size)

    def load_settings(self):
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # General
                self.backup_check.setChecked(config.get('backup_enabled', False))
                interval = config.get('backup_interval', 'Every 15 mins')
                self.backup_interval.setCurrentText(interval)
                
                # Translation
                self.llm_url.setText(config.get('llm_url', 'http://localhost:1234/v1'))
                self.llm_key.setText(config.get('llm_key', 'lm-studio'))
                self.llm_model.setText(config.get('llm_model', 'gemma-2-9b-it'))
                self.engine_combo.setCurrentText(config.get('default_engine', 'LLM (Online/Local)'))
                
                # Appearance
                theme = config.get('theme', 'Dark (Default)')
                self.theme_combo.setCurrentText(theme)
                self.font_size.setCurrentText(config.get('font_size', 'Medium'))
                
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_settings(self):
        config_path = self.get_config_path()
        
        config = {
            'backup_enabled': self.backup_check.isChecked(),
            'backup_interval': self.backup_interval.currentText(),
            'llm_url': self.llm_url.text(),
            'llm_key': self.llm_key.text(),
            'llm_model': self.llm_model.text(),
            'default_engine': self.engine_combo.currentText(),
            'theme': self.theme_combo.currentText(),
            'font_size': self.font_size.currentText()
        }
        
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

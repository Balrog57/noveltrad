from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QTabWidget, QWidget, QFormLayout, QFileDialog)
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
        self.tabs.addTab(self.tools_tab, "Tools")
        self.init_tools_tab()
        
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
        
        layout.addWidget(QLabel("<b>Project Analytics</b>"))
        
        btn_stats = QPushButton("Show Project Statistics")
        btn_stats.setToolTip("View word count, progress and status breakdown")
        btn_stats.setMinimumHeight(40)
        btn_stats.clicked.connect(self.open_stats)
        layout.addWidget(btn_stats)
        
        layout.addStretch()

    def open_store(self):
        self.accept()
        if self.parent() and hasattr(self.parent(), 'show_language_store'):
            self.parent().show_language_store()

    def open_stats(self):
        self.accept()
        if self.parent() and hasattr(self.parent(), 'show_statistics'):
            self.parent().show_statistics()

    def init_appearance_tab(self):
        layout = QFormLayout(self.appearance_tab)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Default)", "Light", "High Contrast"])
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
            'theme': self.theme_combo.currentText(),
            'font_size': self.font_size.currentText()
        }
        
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

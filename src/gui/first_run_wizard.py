from PyQt6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QRadioButton, 
                             QButtonGroup, QFormLayout, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt
import os
import urllib.request
from src.gui.app_config import ConfigManager

class FirstRunWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad - Initial Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(600, 400)
        
        self.config = ConfigManager()
        
        # Pages
        self.addPage(WelcomePage())
        self.addPage(WorkspacePage(self.config))
        self.addPage(LLMPage(self.config))
        self.addPage(NLLBPage(self.config))
        self.addPage(ThemePage(self.config))
        self.addPage(FinishPage())
        
        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        if result == QWizard.DialogCode.Accepted:
            self.config.set_first_run_complete()

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to NovelTrad")
        self.setSubTitle("The AI-powered translation tool for web novels.")
        
        layout = QVBoxLayout()
        label = QLabel("This wizard will help you configure the basic settings for your first use.\n\n"
                       "You can change these settings later in the application.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class WorkspacePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("Workspace Location")
        self.setSubTitle("Where should your projects be saved?")
        
        layout = QVBoxLayout()
        
        self.path_edit = QLineEdit(self.config.get("workspace_dir"))
        self.path_edit.setReadOnly(True)
        layout.addWidget(self.path_edit)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse)
        layout.addWidget(btn_browse)
        
        self.registerField("workspace", self.path_edit)
        self.setLayout(layout)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace Directory")
        if directory:
            self.path_edit.setText(directory)
            self.config.set("workspace_dir", directory)

class ThemePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("Interface Theme")
        self.setSubTitle("Choose your preferred visual style.")
        
        layout = QVBoxLayout()
        
        self.group = QButtonGroup()
        
        self.radio_dark = QRadioButton("Dark Mode (Recommended)")
        self.radio_light = QRadioButton("Light Mode")
        
        if (self.config.get("ui", {}) or {}).get("dark", True):
            self.radio_dark.setChecked(True)
        else:
            self.radio_light.setChecked(True)
            
        self.group.addButton(self.radio_dark)
        self.group.addButton(self.radio_light)
        
        self.radio_dark.toggled.connect(self.save_theme)
        
        layout.addWidget(self.radio_dark)
        layout.addWidget(self.radio_light)
        self.setLayout(layout)

    def save_theme(self):
        ui = dict(self.config.get("ui", {}) or {})
        ui["dark"] = self.radio_dark.isChecked()
        self.config.set("ui", ui)


class LLMPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("LLM Provider")
        self.setSubTitle("Configure the model used by lexicon, QA, and polishing agents.")

        layout = QVBoxLayout()
        form = QFormLayout()
        llm = dict(self.config.get("llm", {}) or {})

        self.provider = QComboBox()
        self.provider.addItem("Ollama (local)", "ollama")
        self.provider.addItem("OpenAI-compatible", "openai")
        idx = self.provider.findData(llm.get("provider", "ollama"))
        if idx >= 0:
            self.provider.setCurrentIndex(idx)
        form.addRow("Provider:", self.provider)

        self.base_url = QLineEdit(llm.get("base_url", "http://127.0.0.1:11434"))
        form.addRow("Base URL:", self.base_url)
        self.model = QLineEdit(llm.get("model", "gemma3:4b"))
        form.addRow("Model:", self.model)
        self.api_key = QLineEdit(llm.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API key:", self.api_key)
        self.draft_fallback = QCheckBox("Use LLM draft if NLLB is unavailable")
        self.draft_fallback.setChecked(bool(llm.get("draft_fallback", False)))
        form.addRow("", self.draft_fallback)
        layout.addLayout(form)

        self.status = QLabel("")
        layout.addWidget(self.status)
        test_btn = QPushButton("Test Ollama endpoint")
        test_btn.clicked.connect(self.test_ollama)
        layout.addWidget(test_btn)
        self.setLayout(layout)

    def validatePage(self):
        llm = dict(self.config.get("llm", {}) or {})
        llm.update(
            {
                "provider": self.provider.currentData(),
                "base_url": self.base_url.text().strip() or "http://127.0.0.1:11434",
                "model": self.model.text().strip() or "gemma3:4b",
                "api_key": self.api_key.text().strip(),
                "draft_fallback": self.draft_fallback.isChecked(),
            }
        )
        self.config.set("llm", llm)
        return True

    def test_ollama(self):
        try:
            with urllib.request.urlopen(
                self.base_url.text().strip().rstrip("/") + "/api/tags",
                timeout=2,
            ) as resp:
                ok = resp.status < 400
        except Exception as exc:
            self.status.setText(f"Ollama test failed: {exc}")
            return
        self.status.setText("Ollama endpoint responded." if ok else "Ollama endpoint returned an error.")


class NLLBPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("NLLB Fast Draft")
        self.setSubTitle("Choose a local CTranslate2 NLLB model directory for hybrid mode.")

        layout = QVBoxLayout()
        nllb = dict(self.config.get("nllb", {}) or {})
        self.path_edit = QLineEdit(nllb.get("model", ""))
        layout.addWidget(self.path_edit)
        browse = QPushButton("Browse model directory...")
        browse.clicked.connect(self.browse)
        layout.addWidget(browse)
        self.device = QComboBox()
        self.device.addItems(["cpu", "cuda", "auto"])
        idx = self.device.findText(nllb.get("device", "cpu"))
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        layout.addWidget(self.device)
        self.status = QLabel(
            "The installer does not bundle large models. If this is left as a Hugging Face id, NovelTrad will report NLLB unavailable until a local model is configured."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setLayout(layout)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Select CTranslate2 NLLB model")
        if directory:
            self.path_edit.setText(directory)

    def validatePage(self):
        nllb = dict(self.config.get("nllb", {}) or {})
        nllb.update(
            {
                "model": self.path_edit.text().strip() or "facebook/nllb-200-distilled-600M",
                "device": self.device.currentText(),
            }
        )
        self.config.set("nllb", nllb)
        return True

class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("You are ready to start translating!")
        
        layout = QVBoxLayout()
        label = QLabel("Click 'Finish' to launch the main application.")
        layout.addWidget(label)
        self.setLayout(layout)

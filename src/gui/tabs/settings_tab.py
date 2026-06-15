"""Settings tab — LLM provider, model, NLLB parameters.

Persists settings to `config.json` (the v4 ConfigManager). The
backend reads the env vars (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
`OPENAI_API_KEY`, …) at startup, so changing a value here is a
guideline — the GUI nudges the user to restart the backend for the
change to take effect (the live router is per-process).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src import __version__ as APP_VERSION
from src.gui.a11y import configure
from src.gui.app_config import ConfigManager
from src.gui.i18n import available_languages
from src.gui.updater import Updater, is_skipped


class SettingsTab(QWidget):
    checkForUpdatesRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(
            QLabel(
                self.tr(
                    "Settings are stored in your NovelTrad app data folder."
                )
            )
        )

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._version = QLabel(APP_VERSION)
        self._version.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._version.setToolTip(
            self.tr(
                "Version baked into the running build. "
                "Compare it with the value on the GitHub Releases page."
            )
        )
        form.addRow(self.tr("Version:"), self._version)

        self._provider = QComboBox()
        self._provider.addItem(self.tr("Ollama (local)"), "ollama")
        self._provider.addItem(self.tr("OpenAI-compatible (cloud)"), "openai")
        self._provider.currentIndexChanged.connect(self._on_provider_changed)
        configure(self._provider, name=self.tr("LLM Provider"))
        form.addRow(self.tr("Provider:"), self._provider)

        self._model = QComboBox()
        self._model.setEditable(True)
        self._model.setMinimumWidth(200)
        configure(self._model, name=self.tr("LLM Model"))
        form.addRow(self.tr("Model:"), self._model)

        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText(self.tr("http://127.0.0.1:11434"))
        form.addRow(self.tr("Base URL:"), self._base_url)

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(self.tr("API key (cloud):"), self._api_key)

        self._parallel = QSpinBox()
        self._parallel.setRange(1, 16)
        self._parallel.setValue(1)
        form.addRow(self.tr("Parallel chunks (Ollama):"), self._parallel)

        self._draft_fallback = QCheckBox(
            self.tr("Use LLM draft if NLLB is unavailable")
        )
        form.addRow("", self._draft_fallback)

        self._nllb_model = QLineEdit()
        self._nllb_model.setPlaceholderText(
            self.tr("facebook/nllb-200-distilled-600M")
        )
        form.addRow(self.tr("NLLB model:"), self._nllb_model)

        self._nllb_device = QComboBox()
        self._nllb_device.addItems(["cpu", "cuda", "auto"])
        configure(self._nllb_device, name=self.tr("NLLB device"))
        form.addRow(self.tr("NLLB device:"), self._nllb_device)

        self._language = QComboBox()
        for code, native in available_languages():
            self._language.addItem(native, code)
        configure(self._language, name=self.tr("Language"))
        form.addRow(self.tr("Language:"), self._language)

        layout.addLayout(form)

        row = QHBoxLayout()
        self._save_btn = QPushButton(self.tr("Save"))
        self._save_btn.clicked.connect(self._save)
        configure(self._save_btn, name=self.tr("Save settings"))
        row.addWidget(self._save_btn)
        self._restart_btn = QPushButton(self.tr("Save & Restart backend"))
        self._restart_btn.clicked.connect(self._save_and_restart)
        configure(self._restart_btn, name=self.tr("Save and Restart backend"))
        row.addWidget(self._restart_btn)
        self._check_updates_btn = QPushButton(self.tr("Check for updates"))
        configure(
            self._check_updates_btn,
            name=self.tr("Check for updates"),
            tooltip=self.tr("Check GitHub Releases for a newer version of NovelTrad."),
        )
        self._check_updates_btn.clicked.connect(
            self.checkForUpdatesRequested.emit
        )
        row.addWidget(self._check_updates_btn)
        row.addStretch(1)
        self._status = QLabel("")
        row.addWidget(self._status)
        layout.addLayout(row)
        layout.addStretch(1)

        self._config = ConfigManager()
        self._load()

    def _load(self) -> None:
        cfg = self._config.config
        llm = cfg.get("llm", {})
        nllb = cfg.get("nllb", {})
        ui = cfg.get("ui", {})
        idx = self._provider.findData(llm.get("provider", "ollama"))
        if idx >= 0:
            self._provider.setCurrentIndex(idx)
        self._model.setCurrentText(llm.get("model", "gemma3:4b"))
        self._base_url.setText(llm.get("base_url", "http://127.0.0.1:11434"))
        self._api_key.setText(llm.get("api_key", ""))
        self._parallel.setValue(int(llm.get("parallel", 1)))
        self._draft_fallback.setChecked(bool(llm.get("draft_fallback", False)))
        self._nllb_model.setText(nllb.get("model", "facebook/nllb-200-distilled-600M"))
        dev = nllb.get("device", "auto")
        idx = self._nllb_device.findText(dev)
        if idx >= 0:
            self._nllb_device.setCurrentIndex(idx)
        lang_idx = self._language.findData(ui.get("language", "en"))
        if lang_idx >= 0:
            self._language.setCurrentIndex(lang_idx)
        self._on_provider_changed()

    def _on_provider_changed(self) -> None:
        provider = self._provider.currentData()
        current = self._model.currentText()
        self._model.clear()
        if provider == "ollama":
            self._model.addItem(self.tr("Fast — gemma3:4b"), "gemma3:4b")
            self._model.addItem(self.tr("Balanced — llama3.1:8b"), "llama3.1:8b")
            self._model.addItem(self.tr("Quality — mistral:7b"), "mistral:7b")
            self._model.addItem(self.tr("Other — qwen2.5:7b"), "qwen2.5:7b")
            self._model.addItem(self.tr("Other — phi4:14b"), "phi4:14b")
        else:
            self._model.addItem(self.tr("Fast — gpt-4o-mini"), "gpt-4o-mini")
            self._model.addItem(self.tr("Balanced — gpt-4o"), "gpt-4o")
            self._model.addItem(self.tr("Quality — gpt-4o"), "gpt-4o")
            self._model.addItem(self.tr("Other — gpt-3.5-turbo"), "gpt-3.5-turbo")
        if current:
            self._model.setCurrentText(current)

    def _collect(self) -> dict:
        return {
            "llm": {
                "provider": self._provider.currentData(),
                "model": self._model.currentText().strip() or "gemma3:4b",
                "base_url": self._base_url.text().strip() or "http://127.0.0.1:11434",
                "api_key": self._api_key.text().strip(),
                "parallel": self._parallel.value(),
                "draft_fallback": self._draft_fallback.isChecked(),
            },
            "nllb": {
                "model": self._nllb_model.text().strip() or "facebook/nllb-200-distilled-600M",
                "device": self._nllb_device.currentText(),
            },
            "ui": {
                "language": self._language.currentData() or "en",
            },
        }

    def _save(self) -> None:
        cfg = self._config.config
        old_lang = str((cfg.get("ui", {}) or {}).get("language", "en"))
        collected = self._collect()
        new_lang = str((collected.get("ui", {}) or {}).get("language", "en"))
        for section, values in collected.items():
            if isinstance(values, dict) and isinstance(cfg.get(section), dict):
                cfg[section].update(values)
            else:
                cfg[section] = values
        self._config.save_config()
        self._config.apply_environment()
        if new_lang != old_lang:
            self._status.setText(
                self.tr("Saved. Restart NovelTrad to apply the language.")
            )
        else:
            self._status.setText(self.tr("Saved."))
        self._status.setStyleSheet("color: #7be395;")

    def _save_and_restart(self) -> None:
        self._save()
        self._status.setText(
            self.tr("Saved. Restart NovelTrad to apply backend changes.")
        )

__all__ = ["SettingsTab"]

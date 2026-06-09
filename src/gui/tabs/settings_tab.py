"""Settings tab — LLM provider, model, NLLB parameters.

Persists settings to `config.json` (the existing ConfigManager). The
backend reads the env vars (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
`OPENAI_API_KEY`, …) at startup, so changing a value here is a
guideline — the GUI nudges the user to restart the backend for the
change to take effect (the live router is per-process).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import ConfigManager


class SettingsTab(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Settings are stored in config.json."))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._provider = QComboBox()
        self._provider.addItem("Ollama (local)", "ollama")
        self._provider.addItem("OpenAI-compatible (cloud)", "openai")
        form.addRow("Provider:", self._provider)

        self._model = QLineEdit()
        self._model.setPlaceholderText("e.g. gemma3:4b / gpt-4o-mini")
        form.addRow("Model:", self._model)

        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("http://127.0.0.1:11434")
        form.addRow("Base URL:", self._base_url)

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API key (cloud):", self._api_key)

        self._parallel = QSpinBox()
        self._parallel.setRange(1, 16)
        self._parallel.setValue(1)
        form.addRow("Parallel chunks (Ollama):", self._parallel)

        self._nllb_model = QLineEdit()
        self._nllb_model.setPlaceholderText("facebook/nllb-200-distilled-600M")
        form.addRow("NLLB model:", self._nllb_model)

        self._nllb_device = QComboBox()
        self._nllb_device.addItems(["cpu", "cuda", "auto"])
        form.addRow("NLLB device:", self._nllb_device)

        self._dark_mode = QCheckBox("Dark theme")
        form.addRow("", self._dark_mode)

        layout.addLayout(form)

        row = QHBoxLayout()
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save)
        row.addWidget(self._save_btn)
        self._restart_btn = QPushButton("Save & Restart backend")
        self._restart_btn.clicked.connect(self._save_and_restart)
        row.addWidget(self._restart_btn)
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
        self._model.setText(llm.get("model", "gemma3:4b"))
        self._base_url.setText(llm.get("base_url", "http://127.0.0.1:11434"))
        self._api_key.setText(llm.get("api_key", ""))
        self._parallel.setValue(int(llm.get("parallel", 1)))
        self._nllb_model.setText(nllb.get("model", "facebook/nllb-200-distilled-600M"))
        dev = nllb.get("device", "cpu")
        idx = self._nllb_device.findText(dev)
        if idx >= 0:
            self._nllb_device.setCurrentIndex(idx)
        self._dark_mode.setChecked(bool(ui.get("dark", True)))

    def _collect(self) -> dict:
        return {
            "llm": {
                "provider": self._provider.currentData(),
                "model": self._model.text().strip() or "gemma3:4b",
                "base_url": self._base_url.text().strip() or "http://127.0.0.1:11434",
                "api_key": self._api_key.text().strip(),
                "parallel": self._parallel.value(),
            },
            "nllb": {
                "model": self._nllb_model.text().strip() or "facebook/nllb-200-distilled-600M",
                "device": self._nllb_device.currentText(),
            },
            "ui": {"dark": self._dark_mode.isChecked()},
        }

    def _save(self) -> None:
        cfg = self._config.config
        cfg.update(self._collect())
        self._config.save_config()
        self._apply_env()
        self._status.setText("Saved.")
        self._status.setStyleSheet("color: #7be395;")

    def _save_and_restart(self) -> None:
        self._save()
        self._status.setText("Saved. Restart NovelTrad to apply backend changes.")

    def _apply_env(self) -> None:
        llm = self._collect()["llm"]
        os.environ["OLLAMA_BASE_URL"] = llm["base_url"]
        os.environ["OLLAMA_MODEL"] = llm["model"]
        os.environ["OLLAMA_PARALLEL"] = str(llm["parallel"])
        if llm.get("api_key"):
            os.environ["OPENAI_API_KEY"] = llm["api_key"]
        nllb = self._collect()["nllb"]
        os.environ["NLLB_MODEL"] = nllb["model"]
        os.environ["NLLB_DEVICE"] = nllb["device"]


__all__ = ["SettingsTab"]

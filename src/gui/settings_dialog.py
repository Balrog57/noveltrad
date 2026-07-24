"""Settings dialog (CDC arborescence §1: gui/widgets/settings.py).

Configure: provider (local/remote), model, Ollama host, remote base URL + API
key, expert mode toggle. Reads from / writes to the Config singleton.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from src.core.llm import REMOTE_PRESETS
from src.gui.a11y import configure
from src.utils.config import Config

LANGUAGES = ["Français", "Anglais", "Espagnol", "Allemand", "Italien", "Chinois", "Japonais"]
TONES = ["Professional", "Familiar", "Technical"]


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Configuration — AgentTranslate")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # --- Backend AI ---
        self.combo_provider = QComboBox()
        configure(
            self.combo_provider,
            accessible_name="Fournisseur d'intelligence artificielle",
            tooltip="Choisir le fournisseur d'intelligence artificielle",
        )
        self.combo_provider.addItems(["ollama"] + list(REMOTE_PRESETS.keys()))
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        form.addRow("Provider :", self.combo_provider)

        self.edit_model = QLineEdit()
        configure(
            self.edit_model,
            accessible_name="Nom du modèle",
            tooltip="Nom du modèle",
        )
        form.addRow("Modèle :", self.edit_model)

        self.edit_ollama_host = QLineEdit()
        configure(
            self.edit_ollama_host,
            accessible_name="Hôte Ollama",
            tooltip="URL de l'hôte Ollama",
        )
        form.addRow("Hôte Ollama :", self.edit_ollama_host)

        self.edit_remote_url = QLineEdit()
        configure(
            self.edit_remote_url,
            accessible_name="URL API distante",
            tooltip="URL de l'API distante",
        )
        self.edit_remote_url.setPlaceholderText("https://api.groq.com/openai/v1")
        form.addRow("URL API distante :", self.edit_remote_url)

        self.edit_api_key = QLineEdit()
        configure(
            self.edit_api_key,
            accessible_name="Clé API",
            tooltip="Clé API",
        )
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Clé API :", self.edit_api_key)

        # --- Pipeline ---
        self.check_expert = QCheckBox("Mode Expert (pipeline 4 agents)")
        configure(
            self.check_expert,
            accessible_name="Activer le mode expert",
        )
        self.check_expert.setToolTip(
            "Décoché = Mode Rapide (agent unique, < 3s par paragraphe)."
        )
        form.addRow(self.check_expert)

        layout.addLayout(form)

        hint = QLabel(
            "<i>🔒 Confidentialité : Ollama local par défaut. Aucune donnée ne quitte votre "
            "machine tant que vous ne sélectionnez pas un provider distant.</i>"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self) -> None:
        self.combo_provider.setCurrentText(self.config.get("provider", "ollama"))
        self.edit_model.setText(self.config.get("model", "qwen2.5:7b"))
        self.edit_ollama_host.setText(self.config.get("ollama_host", "http://localhost:11434"))
        self.edit_remote_url.setText(self.config.get("remote_base_url", ""))
        self.edit_api_key.setText(self.config.get("api_key", ""))
        self.check_expert.setChecked(self.config.get("expert_mode", True))
        self._on_provider_changed(self.combo_provider.currentText())

    def _on_provider_changed(self, provider: str) -> None:
        is_local = provider == "ollama"
        self.edit_ollama_host.setEnabled(is_local)
        self.edit_remote_url.setEnabled(not is_local)
        self.edit_api_key.setEnabled(not is_local)
        if not is_local and not self.edit_remote_url.text():
            self.edit_remote_url.setText(REMOTE_PRESETS.get(provider, ""))

    def _on_save(self) -> None:
        provider = self.combo_provider.currentText()
        if provider != "ollama" and not self.edit_api_key.text().strip():
            QMessageBox.warning(
                self, "Clé API requise",
                f"Le provider distant « {provider} » nécessite une clé API.",
            )
            return
        self.config.update(
            provider=provider,
            model=self.edit_model.text().strip() or "qwen2.5:7b",
            ollama_host=self.edit_ollama_host.text().strip() or "http://localhost:11434",
            remote_base_url=self.edit_remote_url.text().strip(),
            api_key=self.edit_api_key.text().strip(),
            expert_mode=self.check_expert.isChecked(),
        )
        self.config.save()
        self.accept()

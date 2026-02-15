from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QComboBox, QTabWidget, QWidget,
    QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres")
        self.resize(600, 400)
        self.settings = QSettings("NovelTrad", "Config")
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- General Tab ---
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        # Add general settings here if needed
        self.tabs.addTab(general_tab, "Général")

        # --- NLLB Tab ---
        nllb_tab = QWidget()
        nllb_layout = QFormLayout(nllb_tab)
        
        self.nllb_model_path = QLineEdit()
        self.nllb_browse_btn = QPushButton("Parcourir...")
        self.nllb_browse_btn.clicked.connect(self.browse_nllb_model)
        
        nllb_path_layout = QHBoxLayout()
        nllb_path_layout.addWidget(self.nllb_model_path)
        nllb_path_layout.addWidget(self.nllb_browse_btn)
        
        nllb_layout.addRow("Chemin Modèle NLLB (ctranslate2):", nllb_path_layout)
        nllb_layout.addRow(QLabel("Le dossier doit contenir 'model.bin'"))
        
        self.tabs.addTab(nllb_tab, "NLLB (Offline)")

        # --- LLM Tab ---
        llm_tab = QWidget()
        llm_layout = QFormLayout(llm_tab)
        
        self.llm_provider = QComboBox()
        self.llm_provider.addItems(["OpenAI", "Local (Ollama/LM Studio)"])
        self.llm_provider.currentTextChanged.connect(self.on_provider_changed)
        
        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("ex: http://localhost:11434/v1")
        
        self.llm_model_name = QLineEdit()
        self.llm_model_name.setPlaceholderText("ex: gpt-3.5-turbo, mistral")

        llm_layout.addRow("Fournisseur:", self.llm_provider)
        llm_layout.addRow("API Key:", self.llm_api_key)
        llm_layout.addRow("Base URL:", self.llm_base_url)
        llm_layout.addRow("Nom du Modèle:", self.llm_model_name)
        
        self.tabs.addTab(llm_tab, "IA / LLM")

        layout.addWidget(self.tabs)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_nllb_model(self):
        directory = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier du modèle NLLB")
        if directory:
            self.nllb_model_path.setText(directory)

    def on_provider_changed(self, text):
        if text == "OpenAI":
            self.llm_base_url.setText("https://api.openai.com/v1")
            self.llm_base_url.setEnabled(False)
        else:
            self.llm_base_url.setText("http://localhost:1234/v1") # Default for LM Studio
            self.llm_base_url.setEnabled(True)

    def load_settings(self):
        # NLLB
        self.nllb_model_path.setText(self.settings.value("nllb_path", ""))
        
        # LLM
        self.llm_provider.setCurrentText(self.settings.value("llm_provider", "Local (Ollama/LM Studio)"))
        self.llm_api_key.setText(self.settings.value("llm_api_key", ""))
        self.llm_base_url.setText(self.settings.value("llm_base_url", "http://localhost:1234/v1"))
        self.llm_model_name.setText(self.settings.value("llm_model", "mistral"))

    def save_settings(self):
        self.settings.setValue("nllb_path", self.nllb_model_path.text())
        self.settings.setValue("llm_provider", self.llm_provider.currentText())
        self.settings.setValue("llm_api_key", self.llm_api_key.text())
        self.settings.setValue("llm_base_url", self.llm_base_url.text())
        self.settings.setValue("llm_model", self.llm_model_name.text())
        self.accept()

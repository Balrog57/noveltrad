"""First-run wizard for the v4 PyQt client.

Walks the user through:
  1. Welcome
  2. Workspace location
  3. LLM provider — auto-detects Ollama + suggests cloud models
  4. NLLB fast-draft — with dependency & model checks
  5. Theme
  6. Finish
"""

from PyQt6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QRadioButton,
                             QButtonGroup, QFormLayout, QComboBox, QCheckBox,
                             QListWidget, QListWidgetItem, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
import os
import urllib.request
from pathlib import Path
from src.gui.app_config import ConfigManager
from src.gui.llm_discovery import (
    ProviderChoice,
    fetch_provider_choices,
    refresh_router,
)


def _check_ctranslate2() -> tuple[bool, str]:
    """Check if ctranslate2 + sentencepiece are importable."""
    try:
        import ctranslate2  # noqa: F401
        import sentencepiece  # noqa: F401
    except ImportError as exc:
        return False, str(exc)
    return True, ""


def _find_nllb_model() -> str | None:
    """Look for a CTranslate2 NLLB model in standard locations."""
    candidates = [
        # The default install path
        Path(os.environ.get("APPDATA", "")) / ".." / "Local" / "NovelTrad" / "models" / "nllb-200-distilled-600M-ct2-int8",
        Path(os.environ.get("LOCALAPPDATA", "")) / "NovelTrad" / "models" / "nllb-200-distilled-600M-ct2-int8",
        Path.home() / ".cache" / "nllb" / "models--nllb-200-distilled-600M-ct2-int8",
        Path("C:/ProgramData/NovelTrad/models/nllb-200-distilled-600M-ct2-int8"),
    ]
    for p in candidates:
        if p.exists() and (p / "sentencepiece.bpe.model").exists():
            return str(p.resolve())
    return None


def _validate_nllb_model(path: str) -> tuple[bool, str]:
    """Validate that path points to a valid CTranslate2 model directory."""
    p = Path(path)
    if not p.is_dir():
        return False, "Not a directory"
    required = ["sentencepiece.bpe.model", "model.bin", "config.json"]
    missing = [f for f in required if not (p / f).exists()]
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, ""


class FirstRunWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("NovelTrad - Initial Setup"))
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
        self.setTitle(self.tr("Welcome to NovelTrad"))
        self.setSubTitle(self.tr("The AI-powered translation tool for web novels."))

        layout = QVBoxLayout()
        label = QLabel(
            self.tr(
                "This wizard will help you configure the basic settings for your first use.\n\n"
                "You can change these settings later in the application."
            )
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)


class WorkspacePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle(self.tr("Workspace Location"))
        self.setSubTitle(self.tr("Where should your projects be saved?"))

        layout = QVBoxLayout()

        self.path_edit = QLineEdit(self.config.get("workspace_dir"))
        self.path_edit.setReadOnly(True)
        layout.addWidget(self.path_edit)

        btn_browse = QPushButton(self.tr("Browse..."))
        btn_browse.clicked.connect(self.browse)
        layout.addWidget(btn_browse)

        self.registerField("workspace", self.path_edit)
        self.setLayout(layout)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Select Workspace Directory")
        )
        if directory:
            self.path_edit.setText(directory)
            self.config.set("workspace_dir", directory)


class ThemePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle(self.tr("Interface Theme"))
        self.setSubTitle(self.tr("Choose your preferred visual style."))

        layout = QVBoxLayout()

        self.group = QButtonGroup()

        self.radio_dark = QRadioButton(self.tr("Dark Mode (Recommended)"))
        self.radio_light = QRadioButton(self.tr("Light Mode"))

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
    """LLM provider auto-discovery.

    The page calls ``GET /llm/providers`` on the running backend and
    populates a single ``QListWidget`` with three sections:

    * **Installed (auto-detected)**: models the local Ollama instance
      already has on disk.
    * **Local suggestions**: curated models the user can install with
      ``ollama pull <name>``.
    * **Cloud**: a small list of OpenAI-compatible endpoints with one
      click.

    The user can also type any custom model name or base URL — the
    widgets stay editable so power users aren't blocked.
    """

    BACKEND_URL = "http://127.0.0.1:8765"

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle(self.tr("LLM Provider"))
        self.setSubTitle(
            self.tr(
                "Pick a model for the lexicon, QA, and polishing agents. "
                "Ollama models installed on this machine are detected "
                "automatically; you can also pick a cloud provider or "
                "type your own."
            )
        )

        self._choices: dict[str, list[ProviderChoice]] = {
            "installed": [],
            "suggestions": [],
            "cloud": [],
        }
        self._ollama_meta: dict = {"reachable": False, "version": None, "error": None}

        layout = QVBoxLayout()

        # ---- picker (auto-detected) ----
        picker_label = QLabel(self.tr("Discovered models:"))
        layout.addWidget(picker_label)
        self.picker = QListWidget()
        self.picker.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.picker.currentItemChanged.connect(self._on_pick)
        layout.addWidget(self.picker, 1)

        self.status = QLabel(self.tr("Detecting Ollama…"))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton(self.tr("Re-detect"))
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)
        self.test_btn = QPushButton(self.tr("Test endpoint"))
        self.test_btn.clicked.connect(self.test_ollama)
        btn_row.addWidget(self.test_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # ---- manual override ----
        form = QFormLayout()
        llm = dict(self.config.get("llm", {}) or {})

        self.provider = QComboBox()
        self.provider.addItem(self.tr("Ollama (local)"), "ollama")
        self.provider.addItem(self.tr("OpenAI-compatible"), "openai")
        idx = self.provider.findData(llm.get("provider", "ollama"))
        if idx >= 0:
            self.provider.setCurrentIndex(idx)
        self.provider.currentIndexChanged.connect(self._sync_provider_visibility)
        form.addRow(self.tr("Provider kind:"), self.provider)

        self.base_url = QLineEdit(llm.get("base_url", "http://127.0.0.1:11434"))
        form.addRow(self.tr("Base URL:"), self.base_url)

        self.model = QLineEdit(llm.get("model", "gemma3:4b"))
        form.addRow(self.tr("Model:"), self.model)

        self.api_key = QLineEdit(llm.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(self.tr("API key:"), self.api_key)

        self.draft_fallback = QCheckBox(
            self.tr("Use LLM draft if NLLB is unavailable")
        )
        self.draft_fallback.setChecked(bool(llm.get("draft_fallback", False)))
        form.addRow("", self.draft_fallback)
        layout.addLayout(form)
        self.setLayout(layout)

        self._sync_provider_visibility()
        # Kick off an initial discovery in the background.
        self._refresh()

    # ----- discovery -------------------------------------------------

    def _refresh(self):
        self.refresh_btn.setEnabled(False)
        self.status.setText(self.tr("Detecting Ollama…"))
        worker = _DiscoveryWorker(self.BACKEND_URL)
        worker.finished.connect(self._on_discovery)
        worker.start()
        self._worker = worker  # keep alive

    def _on_discovery(self, payload: dict):
        self.refresh_btn.setEnabled(True)
        self._choices["installed"] = payload.get("ollama_choices") or []
        self._choices["suggestions"] = payload.get("ollama_suggestions") or []
        self._choices["cloud"] = payload.get("cloud_choices") or []
        self._ollama_meta = payload.get("ollama") or {}
        self._rebuild_picker()

    def _rebuild_picker(self):
        self.picker.clear()
        sections = [
            (
                self.tr("Installed on this PC")
                if self._ollama_meta.get("reachable")
                else self.tr("Local — Ollama not reachable"),
                self._choices["installed"],
            ),
            (self.tr("Local — suggestions to install"), self._choices["suggestions"]),
            (self.tr("Cloud — OpenAI-compatible"), self._choices["cloud"]),
        ]
        for header, items in sections:
            if not items:
                continue
            head = QListWidgetItem(header)
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            head.setData(Qt.ItemDataRole.UserRole, None)
            self.picker.addItem(head)
            for ch in items:
                li = QListWidgetItem(ch.display())
                li.setData(Qt.ItemDataRole.UserRole, ch)
                self.picker.addItem(li)
        # Status line.
        if self._ollama_meta.get("reachable"):
            version = self._ollama_meta.get("version") or "?"
            self.status.setText(
                self.tr("✓ Ollama {ver} — {n} model(s) installed.").format(
                    ver=version, n=len(self._choices["installed"])
                )
            )
        elif self._ollama_meta.get("error"):
            self.status.setText(
                self.tr("Ollama not reachable. {err}. ").format(
                    err=self._ollama_meta["error"]
                )
                + self.tr(
                    "Pick a suggestion and run 'ollama pull <name>' later, "
                    "or use a cloud model."
                )
            )
        else:
            self.status.setText(
                self.tr(
                    "No Ollama instance found. Pick a cloud model or install Ollama."
                )
            )
        self._sync_provider_visibility()

    def _on_pick(self, current: QListWidgetItem | None, _previous):
        if current is None:
            return
        ch = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(ch, ProviderChoice):
            return
        self.model.setText(ch.model)
        if ch.base_url:
            self.base_url.setText(ch.base_url)
        # Switch provider kind to match the choice.
        idx = self.provider.findData(ch.provider_kind)
        if idx >= 0:
            self.provider.setCurrentIndex(idx)

    def _sync_provider_visibility(self):
        is_ollama = self.provider.currentData() == "ollama"
        self.api_key.setEnabled(not is_ollama)

    # ----- validation -------------------------------------------------

    def test_ollama(self):
        try:
            with urllib.request.urlopen(
                self.base_url.text().strip().rstrip("/") + "/api/tags",
                timeout=2,
            ) as resp:
                ok = resp.status < 400
        except Exception as exc:
            self.status.setText(
                self.tr("Ollama test failed: {err}").format(err=exc)
            )
            return
        self.status.setText(
            self.tr("Ollama endpoint responded.")
            if ok
            else self.tr("Ollama endpoint returned an error.")
        )

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


class _DiscoveryWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, backend_url: str):
        super().__init__()
        self.backend_url = backend_url

    def run(self):
        try:
            payload = fetch_provider_choices(self.backend_url)
        except Exception as exc:  # noqa: BLE001
            payload = {
                "ollama_choices": [],
                "ollama_suggestions": [],
                "cloud_choices": [],
                "ollama": {"reachable": False, "version": None, "error": str(exc)},
                "error": str(exc),
            }
        self.finished.emit(payload)


class NLLBPage(QWizardPage):
    """NLLB model path configuration with auto-detection and validation."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle(self.tr("NLLB Fast Draft"))
        self.setSubTitle(
            self.tr(
                "NLLB provides a fast, local translation draft. "
                "The installer should have placed a CTranslate2 NLLB "
                "model on your machine."
            )
        )

        layout = QVBoxLayout()

        # Dependency check
        ctranslate2_ok, ctranslate2_err = _check_ctranslate2()
        dep_status = QLabel()
        if ctranslate2_ok:
            dep_status.setText(self.tr("✓ CTranslate2 + SentencePiece — available"))
            dep_status.setStyleSheet("color: #7be395;")
        else:
            dep_status.setText(
                self.tr("✗ CTranslate2 / SentencePiece not installed: {err}").format(
                    err=ctranslate2_err
                )
            )
            dep_status.setStyleSheet("color: #e3746b;")
        dep_status.setWordWrap(True)
        layout.addWidget(dep_status)

        # Model path
        nllb = dict(self.config.get("nllb", {}) or {})
        saved_path = nllb.get("model", "")
        auto_path = _find_nllb_model()

        layout.addWidget(QLabel(self.tr("NLLB model directory:")))
        self.path_edit = QLineEdit()
        # Prefer saved path; fall back to auto-detected; else empty.
        prefill = saved_path or auto_path or ""
        self.path_edit.setText(prefill)
        self.path_edit.setPlaceholderText(
            self.tr("e.g. facebook/nllb-200-distilled-600M")
        )
        layout.addWidget(self.path_edit)

        browse = QPushButton(self.tr("Browse model directory..."))
        browse.clicked.connect(self.browse)
        layout.addWidget(browse)

        # Validation status
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # Device selector
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel(self.tr("Device:")))
        self.device = QComboBox()
        self.device.addItems(["cpu", "cuda", "auto"])
        idx = self.device.findText(nllb.get("device", "auto"))
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        device_row.addWidget(self.device)
        device_row.addStretch(1)
        layout.addLayout(device_row)

        layout.addStretch(1)

        # Run validation on path change
        self.path_edit.textChanged.connect(self._validate)

        self.setLayout(layout)

        # Initial validation
        if prefill:
            self._validate()

    def _validate(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            self.status.setText("")
            return
        valid, reason = _validate_nllb_model(path)
        if valid:
            self.status.setText(
                self.tr("✓ Valid CTranslate2 model directory (NLLB-200)")
            )
            self.status.setStyleSheet("color: #7be395;")
        else:
            self.status.setText(
                self.tr("⚠ {reason}").format(reason=reason)
            )
            self.status.setStyleSheet("color: #e9c46a;")

    def browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Select CTranslate2 NLLB model")
        )
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
        self.setTitle(self.tr("Setup Complete"))
        self.setSubTitle(self.tr("You are ready to start translating!"))

        layout = QVBoxLayout()
        label = QLabel(
            self.tr("Click 'Finish' to launch the main application.")
        )
        layout.addWidget(label)
        self.setLayout(layout)

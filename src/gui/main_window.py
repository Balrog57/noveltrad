"""Main window (CDC §5), enriched with CDC F1.b inspector, F1.d selectors,
F2.c glossary loading, F3.b copy, and Mode Rapide/Expert toggle.

Layout (CDC §5): top selector bar + 3-pane splitter (source 40% / target 40% /
inspector 20%).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.glossary import GlossaryError, load_glossary
from src.core.state import make_initial_state
from src.gui.inspector import InspectorPanel
from src.gui.settings_dialog import LANGUAGES, TONES, SettingsDialog
from src.gui.worker import TranslationWorker
from src.utils import history as history_db
from src.utils.config import Config


class MainWindow(QMainWindow):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.worker: TranslationWorker | None = None
        self.glossary: dict[str, str] = {}
        self.setWindowTitle("AgentTranslate — Multi-Agent Desktop Translation")
        self.resize(1100, 680)
        self._build_ui()
        self._load_selector_values()

    # ------------------------------------------------------------------ UI -- #
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Top selector bar (F1.d) ---
        bar = QHBoxLayout()
        bar.addWidget(QLabel("De :"))
        self.combo_source = QComboBox()
        self.combo_source.addItems(LANGUAGES)
        bar.addWidget(self.combo_source)

        bar.addWidget(QLabel("Vers :"))
        self.combo_target = QComboBox()
        self.combo_target.addItems(LANGUAGES)
        bar.addWidget(self.combo_target)

        bar.addWidget(QLabel("Ton :"))
        self.combo_tone = QComboBox()
        self.combo_tone.addItems(TONES)
        bar.addWidget(self.combo_tone)

        bar.addWidget(QLabel("Modèle :"))
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)
        bar.addWidget(self.combo_model, 1)

        self.check_fast = QCheckBox("Mode Rapide")
        self.check_fast.setToolTip("Agent unique (< 3s) au lieu du pipeline 4 agents.")
        self.check_fast.toggled.connect(self._on_fast_toggle)
        bar.addWidget(self.check_fast)

        root.addLayout(bar)

        # --- Action bar ---
        actions = QHBoxLayout()
        self.btn_translate = QPushButton("▶  Traduire (Pipeline Multi-Agent)")
        self.btn_translate.clicked.connect(self.start_translation)
        actions.addWidget(self.btn_translate)

        self.btn_copy = QPushButton("📋 Copier")
        self.btn_copy.setToolTip("Copier la traduction dans le presse-papier (F3.b)")
        self.btn_copy.clicked.connect(self.copy_result)
        actions.addWidget(self.btn_copy)

        self.btn_glossary = QPushButton("📖 Glossaire…")
        self.btn_glossary.setToolTip("Charger un glossaire JSON/CSV (F2.c)")
        self.btn_glossary.clicked.connect(self.load_glossary_file)
        actions.addWidget(self.btn_glossary)

        self.btn_ocr = QPushButton("🖼 OCR Image…")
        self.btn_ocr.setToolTip(
            "Extraire le texte d'une image puis le traduire (CDC Phase 3)"
        )
        self.btn_ocr.clicked.connect(self.import_image_ocr)
        # The OCR button is enabled only when Tesseract is available.
        from src.core import ocr as ocr_mod

        self.btn_ocr.setEnabled(ocr_mod.is_available())
        if not ocr_mod.is_available():
            self.btn_ocr.setToolTip(ocr_mod.install_hint())
        actions.addWidget(self.btn_ocr)

        self.btn_settings = QPushButton("⚙ Configuration")
        self.btn_settings.clicked.connect(self.open_settings)
        actions.addWidget(self.btn_settings)

        actions.addStretch()
        self.lbl_glossary = QLabel("")
        self.lbl_glossary.setStyleSheet("color: #666;")
        actions.addWidget(self.lbl_glossary)
        root.addLayout(actions)

        # --- Splitter (40 / 40 / 20) per CDC §5 ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.txt_source = QTextEdit()
        self.txt_source.setPlaceholderText("Entrez le texte à traduire…")
        self.txt_target = QTextEdit()
        self.txt_target.setReadOnly(True)
        self.txt_target.setPlaceholderText("La traduction apparaîtra ici…")
        self.inspector = InspectorPanel()
        splitter.addWidget(self.txt_source)
        splitter.addWidget(self.txt_target)
        splitter.addWidget(self.inspector)
        splitter.setSizes([440, 440, 220])
        root.addWidget(splitter, 1)

    def _load_selector_values(self) -> None:
        self.combo_source.setCurrentText(self.config.get("source_lang", "Anglais"))
        self.combo_target.setCurrentText(self.config.get("target_lang", "Français"))
        self.combo_tone.setCurrentText(self.config.get("tone", "Professional"))
        model = self.config.get("model", "qwen2.5:7b")
        self.combo_model.addItem(model)
        self.combo_model.setCurrentText(model)
        # Mode Rapide = inverse of expert_mode.
        self.check_fast.setChecked(not self.config.get("expert_mode", True))

    def _on_fast_toggle(self, fast: bool) -> None:
        self.config.set("expert_mode", not fast)
        self.config.save()
        self.btn_translate.setText(
            "▶  Traduire (Mode Rapide)" if fast else "▶  Traduire (Pipeline Multi-Agent)"
        )

    # ----------------------------------------------------------- Actions ---- #
    def open_settings(self) -> None:
        before_provider = self.config.get("provider", "ollama")
        before_model = self.config.get("model", "qwen2.5:7b")
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            # Reflect possible config changes in the selectors.
            self.combo_model.setCurrentText(self.config.get("model", before_model))
            if before_provider != self.config.get("provider"):
                QMessageBox.information(
                    self,
                    "Provider modifié",
                    "Le changement de provider sera effectif à la prochaine traduction.",
                )

    def load_glossary_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Charger un glossaire",
            "",
            "Glossaires (*.json *.csv *.tsv);;Tous les fichiers (*)",
        )
        if not path:
            return
        try:
            self.glossary = load_glossary(path)
            n = len(self.glossary)
            self.lbl_glossary.setText(f"Glossaire : {n} terme(s) chargé(s)")
        except GlossaryError as exc:
            QMessageBox.warning(self, "Glossaire invalide", str(exc))

    def import_image_ocr(self) -> None:
        """CDC Phase 3: extract text from an image via OCR, then translate it."""
        from src.core import ocr as ocr_mod

        if not ocr_mod.is_available():
            QMessageBox.information(self, "OCR indisponible", ocr_mod.install_hint())
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer une image pour OCR",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tous les fichiers (*)",
        )
        if not path:
            return
        try:
            extracted = ocr_mod.extract_text(path)
        except ocr_mod.OcrUnavailable as exc:
            QMessageBox.warning(self, "OCR indisponible", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Échec OCR", f"Impossible de lire l'image :\n{exc}")
            return
        if not extracted:
            QMessageBox.information(self, "OCR", "Aucun texte détecté dans l'image.")
            return
        self.txt_source.setPlainText(extracted)
        self.inspector.append_log(f"[ocr] {len(extracted)} caractères extraits de l'image")
        # Auto-trigger the translation pipeline on the extracted text.
        self.start_translation()

    def copy_result(self) -> None:
        text = self.txt_target.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)

    def start_translation(self) -> None:
        source_text = self.txt_source.toPlainText().strip()
        if not source_text:
            return

        self.btn_translate.setEnabled(False)
        self.txt_target.clear()
        self.inspector.reset()
        self.inspector.append_log("=== Lancement du pipeline ===")

        state = make_initial_state(
            source_text=source_text,
            source_lang=self.combo_source.currentText(),
            target_lang=self.combo_target.currentText(),
            tone=self.combo_tone.currentText(),
            glossary=dict(self.glossary),
        )

        self.worker = TranslationWorker(state, self.config)
        self.worker.step_completed.connect(self._on_step_completed)
        self.worker.stage_output.connect(self._on_stage_output)
        self.worker.translation_finished.connect(self._on_translation_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    # -------------------------------------------------------- Slots --------- #
    def _on_step_completed(self, node_name: str, log_msg: str) -> None:
        # The previous stage is now done; mark the current one running.
        order = ["translator", "proofreader", "glossary", "validator"]
        if node_name in order:
            self.inspector.mark_done(node_name)
            idx = order.index(node_name)
            if idx + 1 < len(order):
                self.inspector.mark_running(order[idx + 1])
        self.inspector.append_log(f"✓ {log_msg}")

    def _on_stage_output(self, stage: str, payload: dict) -> None:
        self.inspector.populate_stage(stage, payload)

    def _on_translation_finished(self, final_state: dict) -> None:
        final_text = final_state.get("final_text") or final_state.get("draft_translation") or ""
        self.txt_target.setText(final_text)
        self.inspector.append_log("=== Traduction terminée avec succès ===")
        score = final_state.get("fidelity_score")
        if score is not None:
            self.inspector.append_log(f"Score de fidélité : {score}/100")
        self.btn_translate.setEnabled(True)

        # F3.a: persist to local history if enabled.
        if self.config.get("history_enabled", True):
            try:
                history_db.add_entry(
                    source_lang=self.combo_source.currentText(),
                    target_lang=self.combo_target.currentText(),
                    tone=self.combo_tone.currentText(),
                    source_text=final_state.get("source_text", ""),
                    final_text=final_text,
                    fidelity=score,
                    status=final_state.get("status"),
                )
            except Exception:  # noqa: BLE001 - history is best-effort
                pass

    def _on_error(self, err_msg: str) -> None:
        self.inspector.append_log(f"❌ Erreur : {err_msg}")
        QMessageBox.critical(
            self,
            "Erreur de traduction",
            f"Le pipeline a échoué :\n\n{err_msg}\n\n"
            "Vérifiez qu'Ollama tourne (ollama serve) et que le modèle est tiré.",
        )
        self.btn_translate.setEnabled(True)

    # ------------------------------------------------- Tray / close hook ---- #
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        # Persist the selector choices.
        self.config.update(
            source_lang=self.combo_source.currentText(),
            target_lang=self.combo_target.currentText(),
            tone=self.combo_tone.currentText(),
        )
        self.config.save()
        # If a tray icon is attached, prefer hiding instead of quitting.
        tray = getattr(self, "_tray", None)
        if tray is not None and tray.isVisible() and not getattr(self, "_force_quit", False):
            event.ignore()
            self.hide()
            tray.showMessage(
                "AgentTranslate",
                "L'application continue en arrière-plan. Cliquez sur l'icône pour revenir.",
            )
            return
        super().closeEvent(event)

from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox, 
    QInputDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDialogButtonBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSettings
from src.ui.editor import EditorWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.dictionary_dialog import DictionaryDialog
from src.core.project_manager import ProjectManager
from src.engines.nllb_engine import NLLBEngine
from src.engines.llm_engine import LLMEngine
import os

class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Langues du Projet")
        self.init_ui()
        self.source_lang = "en"
        self.target_lang = "fr"

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Source
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Langue Source:"))
        self.src_combo = QComboBox()
        self.src_combo.addItems(["Anglais (en)", "Chinois (zh)", "Français (fr)", "Allemand (de)", "Japonais (ja)", "Espagnol (es)"])
        src_layout.addWidget(self.src_combo)
        layout.addLayout(src_layout)
        
        # Target
        tgt_layout = QHBoxLayout()
        tgt_layout.addWidget(QLabel("Langue Cible:"))
        self.tgt_combo = QComboBox()
        self.tgt_combo.addItems(["Français (fr)", "Anglais (en)", "Allemand (de)", "Espagnol (es)", "Italien (it)"])
        tgt_layout.addWidget(self.tgt_combo)
        layout.addLayout(tgt_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_languages(self):
        # Extract codes (simple extraction for now)
        src = self.src_combo.currentText().split('(')[-1].strip(')')
        tgt = self.tgt_combo.currentText().split('(')[-1].strip(')')
        return src, tgt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad v2.0")
        self.resize(1200, 800)
        
        self.project_manager = ProjectManager()
        self.settings = QSettings("NovelTrad", "Config")
        self.engine = None
        
        self.editor = EditorWidget()
        self.setCentralWidget(self.editor)
        
        self.init_menus()
        self.statusBar().showMessage("Prêt")
        
        # Initialize Engine if configured
        self.init_engine()

    def init_engine(self):
        # Load engine preference
        # For now, default to NLLB if path set, else LLM
        nllb_path = self.settings.value("nllb_path", "")
        llm_key = self.settings.value("llm_api_key", "")
        
        # Reset engine
        self.engine = None
        
        if nllb_path and os.path.exists(nllb_path):
            self.engine = NLLBEngine()
            if self.engine.load_model(nllb_path):
                self.statusBar().showMessage(f"Moteur: NLLB ({nllb_path})")
                return

        if llm_key:
             provider = self.settings.value("llm_provider", "OpenAI")
             base_url = self.settings.value("llm_base_url", None)
             model = self.settings.value("llm_model", "gpt-3.5-turbo")
             
             self.engine = LLMEngine(api_key=llm_key, base_url=base_url if provider != "OpenAI" else None, model=model)
             self.statusBar().showMessage(f"Moteur: LLM ({model})")
             return
             
        self.statusBar().showMessage("Aucun moteur de traduction configuré.")

    def init_menus(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&Fichier")
        
        new_action = QAction("&Nouveau Projet", self)
        new_action.setStatusTip("Créer un nouveau projet")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Ouvrir...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Sauvegarder", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("&Paramètres...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Quitter", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Édition")
        undo_action = QAction("&Annuler", self)
        edit_menu.addAction(undo_action)
        
        # Translation Menu
        trans_menu = menubar.addMenu("&Traduction")
        trans_segment_action = QAction("&Traduire Segment Courant", self)
        trans_segment_action.setShortcut("Ctrl+T")
        trans_segment_action.triggered.connect(self.translate_current_segment)
        trans_menu.addAction(trans_segment_action)
        
        trans_menu.addSeparator()
        
        dict_action = QAction("&Dictionnaire Global...", self)
        dict_action.triggered.connect(self.open_dictionary)
        trans_menu.addAction(dict_action)
        
        # Help Menu
        help_menu = menubar.addMenu("&Aide")
        about_action = QAction("&À propos", self)
        help_menu.addAction(about_action)

    def open_dictionary(self):
        # Default to current project langs if open
        src, tgt = "en", "fr"
        if self.project_manager.current_project:
            src = self.project_manager.current_project.source_language
            tgt = self.project_manager.current_project.target_language
            
        dialog = DictionaryDialog(self, initial_src=src, initial_tgt=tgt)
        dialog.exec()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Reload engine configuration when settings dialog acts as 'save'
            self.init_engine()

    def new_project(self):
        name, ok = QInputDialog.getText(self, "Nouveau Projet", "Nom du projet:")
        if ok and name:
            # 1. Select Source File
            source_file, _ = QFileDialog.getOpenFileName(self, "Sélectionner le fichier source", "", "Documents (*.txt *.epub *.docx *.pdf)")
            if not source_file:
                return

            # 2. Select Languages
            lang_dialog = LanguageDialog(self)
            if lang_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            src_lang, tgt_lang = lang_dialog.get_languages()

            # 3. Select Project Location
            file_path, _ = QFileDialog.getSaveFileName(self, "Créer le fichier projet", f"{name}.ntrad", "NovelTrad Files (*.ntrad)")
            
            if file_path:
                try:
                    self.project_manager.create_project(name, file_path, source_file, src_lang, tgt_lang)
                    self.statusBar().showMessage(f"Projet '{name}' créé ({src_lang}->{tgt_lang})")
                    self.setWindowTitle(f"NovelTrad v2.0 - {name}")
                    self.load_project_segments()
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Impossible de créer le projet: {str(e)}")

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un projet", "", "NovelTrad Files (*.ntrad)")
        if file_path:
            try:
                project = self.project_manager.load_project(file_path)
                self.statusBar().showMessage(f"Projet '{project.name}' chargé")
                self.setWindowTitle(f"NovelTrad v2.0 - {project.name}")
                self.load_project_segments()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de charger le projet: {str(e)}")

    def load_project_segments(self):
        segments = self.project_manager.get_segments()
        self.editor.load_segments(segments)

    def translate_current_segment(self):
        if not self.project_manager.current_project:
            self.statusBar().showMessage("Aucun projet ouvert.")
            return

        idx = self.editor.get_current_segment_index()
        segments = self.project_manager.get_segments()
        
        if 0 <= idx < len(segments):
            segment = segments[idx]
            src_text = segment.source_text
            
            if not self.engine or not self.engine.is_available():
                self.init_engine() # Retry loading
                if not self.engine or not self.engine.is_available():
                    QMessageBox.warning(self, "Erreur", "Aucun moteur de traduction configuré ou chargé correctement.")
                    return
            
            project = self.project_manager.current_project
            # check_msg = f"Traduction: {src_text[:20]}... ({project.source_language} -> {project.target_language})"
            # self.statusBar().showMessage(check_msg)
            
            try:
                translation = self.engine.translate(src_text, project.source_language, project.target_language)
                
                # Update DB
                self.project_manager.save_translation(segment.id, translation)
                
                # Update UI
                self.editor.update_target_segment(idx, translation)
                self.statusBar().showMessage("Traduction terminée.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur Traduction", str(e))
        else:
             self.statusBar().showMessage("Aucun segment sélectionné.")

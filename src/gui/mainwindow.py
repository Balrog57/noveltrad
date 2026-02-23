from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QSplitter, 
                             QListWidget, QTextEdit, QLabel, QFileDialog, QDockWidget, QTabWidget, QMenu,
                             QStatusBar, QToolBar, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidgetItem,
                             QScrollArea, QFrame, QGridLayout, QCheckBox, QProgressDialog, QStackedWidget, QInputDialog)
from src.gui.components import SegmentCard, Sidebar
from src.gui.settings_dialog import SettingsDialog
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QColor, QPixmap, QFont
import os
import sys

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.project_manager import ProjectManager
from src.engines import get_engine_instance, list_engines
from src.core.database import Segment, GlossaryTerm, Chapter, SegmentStatus
from src.core.language_manager import LanguageManager
from src.gui.alignment_dialog import AlignmentDialog
from src.gui.qa_dialog import QADialog
from src.gui.chat_widget import ChatWidget
from src.gui.custom_instructions_dialog import CustomInstructionsDialog
from src.core.concordancer import Concordancer
from src.core.dictionary_manager import DictionaryManager
from src.gui.glossary_editor_dialog import GlossaryEditorDialog
from src.gui.statistics_dialog import StatisticsDialog
from src.gui.batch_translation_dialog import BatchTranslationDialog
from src.gui.search_replace_dialog import SearchReplaceDialog
from src.core.backup_manager import BackupManager
from src.core.shortcut_manager import ShortcutManager
from src.utils.connectivity_manager import ConnectivityManager
from src.gui.fuzzy_match_viewer import FuzzyMatchViewer
from src.gui.preview_widget import create_preview_panel

from src.gui.controllers.project_controller import ProjectController
from src.gui.controllers.ai_controller import AIController
from src.gui.controllers.tm_controller import TMController
from src.gui.controllers.editor_controller import EditorController
from src.gui.controllers.tools_controller import ToolsController
from src.gui.panels.header_panel import HeaderPanel
from src.gui.panels.footer_panel import FooterPanel
from src.gui.panels.tools_panel import ToolsPanel
from PyQt6.QtCore import Qt, QSize, QTimer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad - Desktop")
        self.setGeometry(100, 100, 1280, 800)
        
        self.project_manager = ProjectManager()
        self.language_manager = LanguageManager()
        # Use factory to get default engine, or None if failed
        self.llm_engine = get_engine_instance('LLM') or None
        self.current_segment_index = -1
        self.current_layout_mode = "horizontal"
        self.backup_manager = None
        self.realtime_grammar_enabled = True # Default
        
        # Setup Auto-Snapshot Timer (15 minutes)
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.auto_snapshot)
        self.backup_timer.start(15 * 60 * 1000)
        
        # Shortcut Manager
        self.shortcut_manager = ShortcutManager()
        
        # Connectivity Manager (Offline Rescue Mode)
        self.connectivity_manager = ConnectivityManager(parent=self)
        self.connectivity_manager.status_changed.connect(self.update_connectivity_ui)
        
        # Apply Styles (load from config)
        self.apply_theme()
        
        # Real-time Preview Widget
        self.preview_panel = create_preview_panel(self)
        self.is_dark_theme = True # Used by preview widget

        # Initialize Controllers
        self.project_ctrl = ProjectController(self)
        self.ai_ctrl = AIController(self)
        self.tm_ctrl = TMController(self)
        self.editor_ctrl = EditorController(self)
        self.tools_ctrl = ToolsController(self)

        self.init_ui()
        self.setup_shortcuts()

    def auto_snapshot(self):
        """Triggered by timer, creates an automatic backup snaphot."""
        if self.backup_manager:
            path = self.backup_manager.create_snapshot(label="auto")
            if path:
                self.statusBar().showMessage(f"Auto-snapshot created: {os.path.basename(path)}", 5000)
        
    def setup_shortcuts(self):
        """Set up keyboard shortcuts using ShortcutManager."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Mapping of shortcut names to methods
        mappings = [
            ("new_project", self.project_ctrl.new_project),
            ("open_project", lambda: self.project_ctrl.load_project()),
            ("undo", self.editor_ctrl.undo),
            ("redo", self.editor_ctrl.redo),
            ("save_segment", self.editor_ctrl.save_active_segment),
            ("batch_translate", self.ai_ctrl.batch_translate),
            ("search_replace", self.tools_ctrl.show_search_replace),
            ("glossary_scan", self.ai_ctrl.run_glossary_ai),
            ("auto_translate", self.editor_ctrl.auto_translate_current),
            ("ai_refine", self.ai_ctrl.editor_ai_refine),
            ("settings", self.show_settings),
            ("statistics", self.tools_ctrl.show_statistics),
            ("backups", self.project_ctrl.show_backup_dialog),
            ("qa_check", self.tools_ctrl.run_qa_check)
        ]
        
        for name, slot in mappings:
            sequence = self.shortcut_manager.get(name)
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)


    
    def update_current_chapter_progress(self):
        """Update the progress bar for the current chapter in the sidebar."""
        if not hasattr(self, 'current_chapter_id') or not self.current_chapter_id:
            return
            
        chapter = Chapter.get_by_id(self.current_chapter_id)
        total = chapter.segments.count()
        translated = chapter.segments.where(Segment.status != SegmentStatus.UNTRANSLATED.value).count()
        
        progress = int((translated / total) * 100) if total > 0 else 0
        self.sidebar.update_item_progress(self.current_chapter_id, progress)
        
    def colorize_icon(self, icon_name, color="#e2e8f0"):
        border_color = color
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icons", f"{icon_name}.svg")
        if not os.path.exists(icon_path): return QIcon()
        
        pixmap = QIcon(icon_path).pixmap(24, 24)
        mask = pixmap.createMaskFromColor(Qt.GlobalColor.transparent, Qt.MaskMode.MaskInColor)
        
        pixmap.fill(QColor(color))
        pixmap.setMask(mask)
        return QIcon(pixmap)

    def init_ui(self):
        self.create_menu_bar()

        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.setup_workspace(main_layout)
        
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #1e1e1e;
                color: #e2e8f0;
                border-bottom: 1px solid #333333;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #333333;
            }
            QMenu {
                background-color: #1e1e1e;
                color: #e2e8f0;
                border: 1px solid #333333;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
            }
            QMenu::item:selected {
                background-color: #0d7ff2;
                color: white;
            }
        """)
        
        # File Menu
        file_menu = menu_bar.addMenu("&Fichier")
        
        new_action = QAction(self.colorize_icon("add_circle", "#e2e8f0"), "&Nouveau Projet", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.project_ctrl.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction(self.colorize_icon("folder_open", "#e2e8f0"), "&Ouvrir Projet...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(lambda: self.project_ctrl.load_project())
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        import_tm_tmx_action = QAction("Importer Mémoire TMX (Global)...", self)
        import_tm_tmx_action.triggered.connect(self.tm_ctrl.import_global_tmx)
        file_menu.addAction(import_tm_tmx_action)
        
        export_tm_tmx_action = QAction("Exporter Mémoire TMX (Global)...", self)
        export_tm_tmx_action.triggered.connect(self.tm_ctrl.export_global_tmx)
        file_menu.addAction(export_tm_tmx_action)

        file_menu.addSeparator()

        import_project_tmx_action = QAction("Importer TMX dans le Projet...", self)
        import_project_tmx_action.triggered.connect(self.tm_ctrl.import_project_tmx)
        file_menu.addAction(import_project_tmx_action)
        
        export_project_tmx_action = QAction("Exporter Projet en TMX...", self)
        export_project_tmx_action.triggered.connect(self.tm_ctrl.export_project_tmx)
        file_menu.addAction(export_project_tmx_action)

        file_menu.addSeparator()
        
        export_action = QAction(self.colorize_icon("file_download", "#e2e8f0"), "&Exporter Traductions...", self)
        export_action.triggered.connect(self.project_ctrl.export_project)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Quitter", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menu_bar.addMenu("&Édition")
        
        find_action = QAction(self.colorize_icon("search", "#e2e8f0"), "&Rechercher et Remplacer", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.tools_ctrl.show_search_replace)
        edit_menu.addAction(find_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction(self.colorize_icon("settings", "#e2e8f0"), "&Paramètres", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        edit_menu.addSeparator()
        
        custom_inst_action = QAction(self.colorize_icon("psychology", "#e2e8f0"), "&Instructions IA Projet", self)
        custom_inst_action.triggered.connect(self.show_custom_instructions_dialog)
        edit_menu.addAction(custom_inst_action)

        # Translation Menu
        translation_menu = menu_bar.addMenu("&Traduction")
        
        translate_segment_action = QAction(self.colorize_icon("translate", "#e2e8f0"), "Traduire le &paragraphe", self)
        translate_segment_action.setShortcut("Ctrl+Enter")
        translate_segment_action.triggered.connect(self.editor_ctrl.auto_translate_current)
        
        translate_selection_action = QAction("Traduire la &sélection", self)
        translation_menu.addAction(translate_selection_action)
        
        translate_chapter_action = QAction("Traduire le &chapitre", self)
        translate_chapter_action.setShortcut("Ctrl+Shift+T")
        translate_chapter_action.triggered.connect(self.ai_ctrl.batch_translate)
        translation_menu.addAction(translate_chapter_action)
        
        translation_menu.addSeparator()
        
        choose_engine_action = QAction("&Choisir le moteur de traduction...", self)
        choose_engine_action.triggered.connect(self.show_engine_selection)
        translation_menu.addAction(choose_engine_action)

        # Dictionary Menu
        dictionary_menu = menu_bar.addMenu("&Dictionnaire")
        
        search_dict_action = QAction(self.colorize_icon("search", "#e2e8f0"), "&Rechercher un mot...", self)
        search_dict_action.setShortcut("Ctrl+D")
        search_dict_action.triggered.connect(self.tools_ctrl.search_dictionary)
        dictionary_menu.addAction(search_dict_action)
        
        dictionary_menu.addSeparator()
        
        configure_dict_action = QAction("&Configurer les dictionnaires...", self)
        configure_dict_action.triggered.connect(self.show_dict_config)
        dictionary_menu.addAction(configure_dict_action)

        dictionary_menu.addSeparator()
        
        add_term_action = QAction("Ajouter un Terme au Glossaire...", self)
        add_term_action.triggered.connect(self.editor_ctrl.add_glossary_term)
        dictionary_menu.addAction(add_term_action)

        # IA Menu
        ia_menu = menu_bar.addMenu("&IA")
        
        configure_models_action = QAction(self.colorize_icon("settings", "#e2e8f0"), "Configurer les &modèles...", self)
        configure_models_action.triggered.connect(self.show_models_config)
        ia_menu.addAction(configure_models_action)
        
        ia_menu.addSeparator()
        
        editor_ai_action = QAction(self.colorize_icon("auto_fix", "#e2e8f0"), "&Editor AI - Raffiner la traduction", self)
        editor_ai_action.setShortcut("Ctrl+Shift+R")
        editor_ai_action.triggered.connect(self.ai_ctrl.editor_ai_refine)
        ia_menu.addAction(editor_ai_action)
        
        chat_context_action = QAction(self.colorize_icon("chat", "#e2e8f0"), "Chat &contextuel IA...", self)
        chat_context_action.triggered.connect(self.ai_ctrl.show_chat)
        ia_menu.addAction(chat_context_action)
        
        ia_menu.addSeparator()
        
        glossary_ai_action = QAction(self.colorize_icon("auto_awesome", "#e2e8f0"), "Glossary &AI - Générer glossaire...", self)
        glossary_ai_action.triggered.connect(self.ai_ctrl.run_glossary_ai)
        ia_menu.addAction(glossary_ai_action)

        ia_menu.addSeparator()
        
        suggest_action = QAction(self.colorize_icon("auto_awesome", "#e2e8f0"), "Régénérer Suggestion (Segment)", self)
        suggest_action.setShortcut("Ctrl+G")
        suggest_action.triggered.connect(self.editor_ctrl.auto_translate_current)
        ia_menu.addAction(suggest_action)

        # Tools Menu
        tools_menu = menu_bar.addMenu("&Outils")
        
        batch_action = QAction(self.colorize_icon("library_books", "#e2e8f0"), "&Traduction par Lot...", self)
        batch_action.triggered.connect(self.ai_ctrl.batch_translate)
        tools_menu.addAction(batch_action)
        
        stats_action = QAction(self.colorize_icon("analytics", "#e2e8f0"), "&Statistiques du Projet...", self)
        stats_action.triggered.connect(self.tools_ctrl.show_statistics)
        tools_menu.addAction(stats_action)
        
        tools_menu.addSeparator()
        
        glossary_action = QAction(self.colorize_icon("menu_book", "#e2e8f0"), "&Gérer Glossaire...", self)
        glossary_action.triggered.connect(self.tools_ctrl.open_glossary_manager)
        tools_menu.addAction(glossary_action)
        
        qa_action = QAction(self.colorize_icon("verified", "#e2e8f0"), "&Vérification Qualité (QA)...", self)
        qa_action.triggered.connect(self.tools_ctrl.run_qa_check)
        tools_menu.addAction(qa_action)
        
        tools_menu.addSeparator()
        
        self.grammar_toggle_action = QAction("Vérification Grammaticale &en temps réel", self)
        self.grammar_toggle_action.setCheckable(True)
        self.grammar_toggle_action.setChecked(self.realtime_grammar_enabled)
        self.grammar_toggle_action.triggered.connect(self.toggle_realtime_grammar)
        tools_menu.addAction(self.grammar_toggle_action)
        
        align_action = QAction(self.colorize_icon("compare_arrows", "#e2e8f0"), "&Outil d'Alignement...", self)
        align_action.triggered.connect(self.tools_ctrl.open_alignment_tool)
        tools_menu.addAction(align_action)

        backup_action = QAction(self.colorize_icon("history", "#e2e8f0"), "&Historique / Sauvegardes...", self)
        backup_action.triggered.connect(self.project_ctrl.show_backup_dialog)
        tools_menu.addAction(backup_action)
        
        # View Menu
        view_menu = menu_bar.addMenu("&Affichage")
        
        toggle_preview_action = QAction(self.colorize_icon("visibility", "#e2e8f0"), "&Aperçu temps réel", self)
        toggle_preview_action.setShortcut("F12")
        toggle_preview_action.triggered.connect(self.preview_panel.toggle_visibility)
        view_menu.addAction(toggle_preview_action)
        
        view_menu.addSeparator()
        
        toggle_layout_action = QAction("&Alterner Disposition Horiz/Vert", self)
        toggle_layout_action.triggered.connect(self.toggle_layout_mode)
        view_menu.addAction(toggle_layout_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Aide")
        
        documentation_action = QAction(self.colorize_icon("menu_book", "#e2e8f0"), "&Documentation", self)
        documentation_action.setShortcut("F1")
        help_menu.addAction(documentation_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(self.colorize_icon("info", "#e2e8f0"), "À &propos de NovelTrad...", self)
        help_menu.addAction(about_action)


    def setup_workspace(self, main_layout):
        # 1. Header Area
        self.header_panel = HeaderPanel(self)
        main_layout.addWidget(self.header_panel)
        
        # 2. Main Workspace (Splitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #333333; }")
        
        # Left: Chapters (Sidebar)
        self.sidebar_container = QFrame()
        self.sidebar_container.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 8, 0, 0)
        
        chapters_header = QHBoxLayout()
        chapters_header.setContentsMargins(16, 8, 16, 8)
        ch_label = QLabel("CHAPITRES")
        ch_label.setObjectName("SidebarTitle")
        chapters_header.addWidget(ch_label)
        chapters_header.addStretch()
        
        # Chapter Actions
        add_chapter_btn = self.create_icon_btn("add", "Importer un Chapitre", self.project_ctrl.import_chapter)
        self.auto_struct_btn = self.create_icon_btn("auto_fix_high", "Structure Auto (IA)", self.editor_ctrl.run_structure_ai)
        chapters_header.addWidget(add_chapter_btn)
        chapters_header.addWidget(self.auto_struct_btn)
        sidebar_layout.addLayout(chapters_header)
        
        self.sidebar = Sidebar()
        self.sidebar.itemClicked.connect(self.editor_ctrl.select_chapter)
        sidebar_layout.addWidget(self.sidebar)
        
        # Center: Editor
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(24, 24, 24, 24)
        self.cards_layout.setSpacing(24)
        self.cards_layout.addStretch()
        
        self.scroll_area.setWidget(self.cards_container)
        editor_layout.addWidget(self.scroll_area)
        
        # Right: Tools Panel (Modularized)
        self.tools_panel = ToolsPanel(self)
        
        self.splitter.addWidget(self.sidebar_container)
        self.splitter.addWidget(editor_container)
        self.splitter.addWidget(self.tools_panel)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
        
        # 3. Footer Area
        self.footer_panel = FooterPanel(self)
        main_layout.addWidget(self.footer_panel)
        
        # Compatibility aliases for legacy code
        self.project_name_label = self.header_panel.project_name_label
        self.progress_pct = self.footer_panel.progress_pct
        self.progress_fill = self.footer_panel.progress_fill
        self.segments_count = self.footer_panel.segments_count
        self.words_count = self.footer_panel.words_count
        self.connectivity_point = self.footer_panel.connectivity_point
        self.connectivity_label = self.footer_panel.connectivity_label
        
        self.load_languages_into_footer()

    def create_icon_btn(self, icon_name, tooltip, callback):
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setIcon(self.colorize_icon(icon_name, "#cbd5e1"))
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def create_separator(self):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(12)
        sep.setStyleSheet("background-color: #333333;")
        return sep





    def update_footer_stats(self):
        """Update Footer with project statistics and progress."""
        if not self.project_manager.current_project:
            return
            
        project = self.project_manager.current_project
        segments = list(self.project_manager.get_segments())
        
        total = len(segments)
        translated = sum(1 for s in segments if s.status and s.status != SegmentStatus.UNTRANSLATED.value)
        
        # Word counts
        source_words = sum(len(s.source_text.split()) for s in segments)
        target_words = sum(len(s.target_text.split()) if s.target_text else 0 for s in segments)
        
        progress = int((translated / total) * 100) if total > 0 else 0
        
        # Update UI
        self.source_lang_label.setText(f"Source: {project.source_language.upper()}")
        self.target_lang_label.setText(f"Target: {project.target_language.upper()}")
        
        self.progress_pct.setText(f"{progress}%")
        
        # Progress Bar fill (max width 200 as defined in UI)
        fill_width = int((progress / 100.0) * 200)
        self.progress_fill.setFixedWidth(fill_width)
        
        self.segments_count.setText(f"Segments : {translated} / {total}")
        self.words_count.setText(f"Mots : {target_words:,} / {source_words:,}")
    def show_settings(self):
        from src.gui.settings_dialog import SettingsDialog
        from src.core.config_manager import ConfigManager
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Refresh settings
            cfg = ConfigManager()
            # Note: SettingsDialog currently writes directly to config.json
            # We should probably reload ConfigManager
            cfg.config = cfg.load_config()
            self.realtime_grammar_enabled = cfg.get("grammar_enabled", True)
            self.grammar_toggle_action.setChecked(self.realtime_grammar_enabled)
            self.update_all_cards_grammar()
            
            self.apply_theme()
            self.statusBar().showMessage("Paramètres sauvegardés.", 3000)

    def toggle_realtime_grammar(self, checked):
        """Toggle grammar checking via menu."""
        from src.core.config_manager import ConfigManager
        self.realtime_grammar_enabled = checked
        ConfigManager().set("grammar_enabled", checked)
        self.update_all_cards_grammar()
        self.statusBar().showMessage(f"Vérification grammaire : {'Activée' if checked else 'Désactivée'}", 3000)

    def update_all_cards_grammar(self):
        """Propagate grammar toggle to all cards."""
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, SegmentCard):
                    widget.set_grammar_enabled(self.realtime_grammar_enabled)

    def show_language_store(self):
        from src.gui.language_store import LanguageStore
        dialog = LanguageStore(self)
        dialog.exec()

    def load_languages_into_footer(self):
        languages = self.language_manager.get_supported_languages()
        
        self.source_lang_combo.blockSignals(True)
        self.target_lang_combo.blockSignals(True)
        
        self.source_lang_combo.clear()
        self.target_lang_combo.clear()
        
        for lang in languages:
            if not lang['installed']:
                continue
            icon = self.colorize_icon("check_circle", "#22c55e")
            self.source_lang_combo.addItem(icon, lang['name'], lang['code'])
            self.target_lang_combo.addItem(icon, lang['name'], lang['code'])
            
        self.source_lang_combo.blockSignals(False)
        self.target_lang_combo.blockSignals(False)

    def on_language_changed(self, mode):
        if not self.project_manager.current_project:
            return
            
        src_idx = self.source_lang_combo.currentIndex()
        tgt_idx = self.target_lang_combo.currentIndex()
        
        if src_idx >= 0:
            src_code = self.source_lang_combo.itemData(src_idx)
            self.project_manager.current_project.source_language = src_code
            
        if tgt_idx >= 0:
            tgt_code = self.target_lang_combo.itemData(tgt_idx)
            self.project_manager.current_project.target_language = tgt_code
            
        self.project_manager.current_project.save()
        self.statusBar().showMessage(f"Project languages updated: {self.source_lang_combo.currentText()} -> {self.target_lang_combo.currentText()}", 3000)

    def get_current_translation_engine(self):
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        default_engine_name = "LLM (Online/Local)"
        
        if os.path.exists(config_path):
             try:
                 with open(config_path, 'r', encoding='utf-8') as f:
                     config = json.load(f)
                 default_engine_name = config.get('default_engine', 'LLM (Online/Local)')
             except:
                 pass
        
        if "Argos" in default_engine_name:
            if self.language_manager.argos:
                return self.language_manager.argos
        elif "NLLB" in default_engine_name:
            if self.language_manager.nllb:
                 return self.language_manager.nllb
        
        # Offline Rescue Mode logic
        is_online = self.connectivity_manager.is_online if self.connectivity_manager else True
        if not is_online:
            # If we are offline and using an online engine (like default LLM usually is), 
            # try to switch to a local one
            if self.language_manager.argos:
                return self.language_manager.argos
            if self.language_manager.nllb:
                return self.language_manager.nllb
        
        # Fallback to LLM
        return self.llm_engine

    def update_connectivity_ui(self, is_online):
        """Updates the footer status based on internet connectivity."""
        if is_online:
            self.connectivity_point.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
            self.connectivity_label.setText("ONLINE")
        else:
            self.connectivity_point.setStyleSheet("background-color: #ef4444; border-radius: 4px;")
            self.connectivity_label.setText("OFFLINE (RESCUE MODE)")

    def show_custom_instructions_dialog(self):
        """Open dialog to edit custom AI instructions."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet ouvert.")
            return

        current_instructions = self.project_manager.current_project.custom_instructions
        from src.gui.custom_instructions_dialog import CustomInstructionsDialog
        dialog = CustomInstructionsDialog(self, current_instructions)
        if dialog.exec():
            new_instructions = dialog.get_instructions()
            self.project_manager.current_project.custom_instructions = new_instructions
            self.project_manager.current_project.save()
            QMessageBox.information(self, "Succès", "Instructions enregistrées.")

    def toggle_layout_mode(self):
        """Toggle between horizontal and vertical layout for segments."""
        if self.current_layout_mode == "horizontal":
            self.current_layout_mode = "vertical"
            self.btn_layout.setToolTip("Vue : Verticale (cliquer pour changer)")
        else:
            self.current_layout_mode = "horizontal"
            self.btn_layout.setToolTip("Vue : Horizontale (cliquer pour changer)")
            
        # Update visible cards
        # iterate self.cards_layout
        layout = self.cards_layout
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    from src.gui.segment_card import SegmentCard
                    if isinstance(widget, SegmentCard):
                        widget.set_layout_mode(self.current_layout_mode)

    def apply_theme(self):
        """Apply the selected theme from configuration."""
        from src.core.config_manager import ConfigManager
        from src.gui.styles import (DARK_THEME, LIGHT_THEME, HIGH_CONTRAST_THEME, 
                                     DEUTERANOPIA_THEME, PROTANOPIA_THEME, TRITANOPIA_THEME)
        
        cfg = ConfigManager()
        theme = cfg.get("theme", "Dark")
        
        # Mapping
        themes = {
            "Dark": DARK_THEME,
            "Light": LIGHT_THEME,
            "High Contrast": HIGH_CONTRAST_THEME,
            "Deuteranopia": DEUTERANOPIA_THEME,
            "Protanopia": PROTANOPIA_THEME,
            "Tritanopia": TRITANOPIA_THEME
        }
        
        style = themes.get(theme, DARK_THEME)
        self.setStyleSheet(style)

    def show_engine_selection(self):
        """Dialog to choose the active translation engine."""
        engines = list_engines()
        if not engines:
            QMessageBox.warning(self, "Erreur", "Aucun moteur de traduction trouvé.")
            return
            
        engine_names = [name for name in engines]
        # Current engine name
        current = self.llm_engine.get_name() if self.llm_engine else ""
        
        choice, ok = QInputDialog.getItem(self, "Moteur de Traduction", "Sélectionnez le moteur par défaut :", engine_names, editable=False)
        if ok and choice:
            new_engine = get_engine_instance(choice)
            if new_engine:
                self.llm_engine = new_engine
                if hasattr(self, 'chat_widget'):
                    self.chat_widget.set_engine(new_engine)
                self.statusBar().showMessage(f"Moteur actif : {choice}", 3000)

    def show_dict_config(self):
        self.show_settings()

    def show_models_config(self):
        self.show_settings()

    def refresh_preview(self):
        """Update the real-time preview with current chapter text."""
        if not hasattr(self, 'preview_panel') or not self.preview_panel:
            return
            
        if not self.project_manager.current_project or not getattr(self, 'current_chapter_id', None):
            return
            
        # Collect all translations for the current chapter
        segments = Segment.select().where(Segment.chapter_id == self.current_chapter_id).order_by(Segment.index)
        chapter = Chapter.get_by_id(self.current_chapter_id)
        
        full_text = ""
        for s in segments:
            # Use space or newline depending on segment type? Chapter text is usually paragraphs.
            text = s.target_text if s.target_text else f"[{s.source_text}]"
            full_text += text + " "
            
        self.preview_panel.update(full_text, chapter.title)



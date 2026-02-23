from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QSplitter, 
                             QListWidget, QTextEdit, QLabel, QFileDialog, QDockWidget, QTabWidget, QMenu,
                             QStatusBar, QToolBar, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidgetItem,
                             QScrollArea, QFrame, QGridLayout, QCheckBox, QProgressDialog)
from src.gui.components import SegmentCard, Sidebar
from src.gui.settings_dialog import SettingsDialog
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QColor, QPixmap
import os
import sys

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.project_manager import ProjectManager
from src.engines import get_engine_instance, list_engines
from src.core.database import Segment, GlossaryTerm, Chapter
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
from src.core.backup_manager import BackupManager
from src.core.shortcut_manager import ShortcutManager
from src.utils.connectivity_manager import ConnectivityManager
from src.gui.fuzzy_match_viewer import FuzzyMatchViewer
from PyQt6.QtCore import Qt, QSize, QTimer

class AutoStructureWorker(QThread):
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, project_manager, llm_engine):
        super().__init__()
        self.project_manager = project_manager
        self.llm_engine = llm_engine

    def run(self):
        try:
            count = self.project_manager.auto_structure_project(
                self.llm_engine,
                progress_callback=self._emit_progress
            )
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))
            
    def _emit_progress(self, val, msg):
        self.progress_update.emit(val, msg)

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
        
        self.init_ui()
        self.setup_shortcuts()

    def auto_snapshot(self):
        """Triggered by timer, creates an automatic backup snaphot."""
        if self.backup_manager:
            path = self.backup_manager.create_snapshot(label="auto")
            if path:
                self.status_bar.showMessage(f"Auto-snapshot created: {os.path.basename(path)}", 5000)
        
    def setup_shortcuts(self):
        """Set up keyboard shortcuts using ShortcutManager."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Mapping of shortcut names to methods
        mappings = [
            ("new_project", self.new_project_dialog),
            ("open_project", self.open_project_dialog),
            ("save_segment", self.save_current_segment),
            ("batch_translate", self.batch_translate),
            ("search_replace", self.show_search_replace),
            ("glossary_scan", self.scan_chapter_glossary),
            ("auto_translate", self.auto_translate_current),
            ("ai_refine", self.editor_ai_refine),
            ("settings", self.show_settings),
            ("statistics", self.show_statistics),
            ("backups", self.show_backup_dialog),
            ("qa_check", self.show_qa_dialog)
        ]
        
        for name, slot in mappings:
            sequence = self.shortcut_manager.get(name)
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)

    def save_current_segment(self):
        """Save current segment (Ctrl+S)."""
        if self.current_segment_index == -1:
            return
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.current_segment_index:
                text = widget.target_edit.toPlainText()
                widget.segment.target_text = text
                if text:
                    widget.segment.set_status(SegmentStatus.VALIDATED)
                    # Add to Translation Memory
                    self.project_manager.add_to_tm(widget.segment.source_text, text)
                widget.segment.save()
                self.status_bar.showMessage(f"Segment {self.current_segment_index} saved.")
                self.update_footer_stats()
                self.update_current_chapter_progress()
                break

    def apply_translation_match(self, match_data):
        """Apply a fuzzy translation match to the active segment."""
        if getattr(self, 'current_segment_index', None) is None:
            return
            
        target_text = match_data.get('target', '')
        if not target_text:
            return
            
        # Find active card and update its text
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.current_segment_index:
                widget.target_edit.setPlainText(target_text)
                self.save_current_segment()
                self.status_bar.showMessage("Traduction de la mémoire sélectionnée et sauvegardée.", 3000)
                break

    def update_current_chapter_progress(self):
        """Update the progress bar for the current chapter in the sidebar."""
        if not hasattr(self, 'current_chapter_id') or not self.current_chapter_id:
            return
            
        chapter = Chapter.get_by_id(self.current_chapter_id)
        total = chapter.segments.count()
        translated = chapter.segments.where(Segment.status != SegmentStatus.UNTRANSLATED.value).count()
        
        progress = int((translated / total) * 100) if total > 0 else 0
        self.sidebar.update_item_progress(self.current_chapter_id, progress)
        
        from src.core.config_manager import ConfigManager
        
        config = ConfigManager()
        theme = config.get("theme", "dark")
        font_size_name = config.get("font_size", "Medium")
        
        # Apply Font Size
        size_map = {
            "Small": 12,
            "Medium": 14,
            "Large": 16
        }
        # Set global font
        if font_size_name == "Large":
            point_size = 16
        elif font_size_name == "Small":
            point_size = 12
        else:
            point_size = 14
            
        # Security: Never less than 1
        point_size = max(1, point_size)
            
        self.setFont(QFont("Inter", point_size))
        
        # Load Stylesheet
        from src.gui.styles import DARK_THEME, LIGHT_THEME
        # Support both 'dark' (ConfigManager) and 'Dark (Default)' (Legacy)
        if hasattr(theme, 'lower') and 'dark' in theme.lower():
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)
        
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
        new_action.triggered.connect(self.new_project_dialog)
        file_menu.addAction(new_action)
        
        open_action = QAction(self.colorize_icon("folder_open", "#e2e8f0"), "&Ouvrir Projet...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)

        save_action = QAction(self.colorize_icon("save", "#e2e8f0"), "&Sauvegarder Segment", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_current_segment)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        import_tmx_action = QAction("Importer Mémoire TMX...", self)
        import_tmx_action.triggered.connect(self.import_tmx_dialog)
        file_menu.addAction(import_tmx_action)
        
        export_tmx_action = QAction("Exporter Mémoire TMX...", self)
        export_tmx_action.triggered.connect(self.export_tmx_dialog)
        file_menu.addAction(export_tmx_action)

        file_menu.addSeparator()
        
        export_action = QAction(self.colorize_icon("file_download", "#e2e8f0"), "&Exporter Traductions...", self)
        export_action.triggered.connect(self.export_project_dialog)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Quitter", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menu_bar.addMenu("&Édition")
        
        # Undo/Redo
        undo_action = QAction("&Annuler", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Rétablir", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction(self.colorize_icon("search", "#e2e8f0"), "&Rechercher et Remplacer", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_search_replace)
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
        translation_menu.addAction(translate_segment_action)
        
        translate_selection_action = QAction("Traduire la &sélection", self)
        translation_menu.addAction(translate_selection_action)
        
        translate_chapter_action = QAction("Traduire le &chapitre", self)
        translate_chapter_action.setShortcut("Ctrl+Shift+T")
        translation_menu.addAction(translate_chapter_action)
        
        translation_menu.addSeparator()
        
        batch_translate_action = QAction(self.colorize_icon("library_books", "#e2e8f0"), "Traduction par &lot (batch)...", self)
        batch_translate_action.triggered.connect(self.batch_translate)
        translation_menu.addAction(batch_translate_action)
        
        translation_menu.addSeparator()
        
        choose_engine_action = QAction("&Choisir le moteur de traduction...", self)
        translation_menu.addAction(choose_engine_action)

        # Dictionary Menu
        dictionary_menu = menu_bar.addMenu("&Dictionnaire")
        
        search_dict_action = QAction(self.colorize_icon("search", "#e2e8f0"), "&Rechercher un mot...", self)
        search_dict_action.setShortcut("Ctrl+D")
        dictionary_menu.addAction(search_dict_action)
        
        dictionary_menu.addSeparator()
        
        configure_dict_action = QAction("&Configurer les dictionnaires...", self)
        dictionary_menu.addAction(configure_dict_action)

        # IA Menu
        ia_menu = menu_bar.addMenu("&IA")
        
        configure_models_action = QAction(self.colorize_icon("settings", "#e2e8f0"), "Configurer les &modèles...", self)
        ia_menu.addAction(configure_models_action)
        
        ia_menu.addSeparator()
        
        editor_ai_action = QAction(self.colorize_icon("auto_fix", "#e2e8f0"), "&Editor AI - Raffiner la traduction", self)
        editor_ai_action.setShortcut("Ctrl+Shift+R")
        editor_ai_action.triggered.connect(self.editor_ai_refine)
        ia_menu.addAction(editor_ai_action)
        
        chat_context_action = QAction(self.colorize_icon("chat", "#e2e8f0"), "Chat &contextuel IA...", self)
        ia_menu.addAction(chat_context_action)
        
        ia_menu.addSeparator()
        
        glossary_ai_action = QAction(self.colorize_icon("auto_awesome", "#e2e8f0"), "Glossary &AI - Générer glossaire...", self)
        ia_menu.addAction(glossary_ai_action)

        # Tools Menu
        tools_menu = menu_bar.addMenu("&Outils")
        
        batch_action = QAction(self.colorize_icon("library_books", "#e2e8f0"), "&Traduction par Lot...", self)
        batch_action.triggered.connect(self.batch_translate)
        tools_menu.addAction(batch_action)
        
        stats_action = QAction(self.colorize_icon("analytics", "#e2e8f0"), "&Statistiques du Projet...", self)
        stats_action.triggered.connect(self.show_statistics_dialog)
        tools_menu.addAction(stats_action)
        
        tools_menu.addSeparator()
        
        glossary_action = QAction(self.colorize_icon("menu_book", "#e2e8f0"), "&Gérer Glossaire...", self)
        glossary_action.triggered.connect(self.open_glossary_manager)
        tools_menu.addAction(glossary_action)
        
        qa_action = QAction(self.colorize_icon("verified", "#e2e8f0"), "&Vérification Qualité (QA)...", self)
        qa_action.triggered.connect(self.show_qa_dialog)
        tools_menu.addAction(qa_action)
        
        tools_menu.addSeparator()
        
        self.grammar_toggle_action = QAction("Vérification Grammaticale &en temps réel", self)
        self.grammar_toggle_action.setCheckable(True)
        self.grammar_toggle_action.setChecked(self.realtime_grammar_enabled)
        self.grammar_toggle_action.triggered.connect(self.toggle_realtime_grammar)
        tools_menu.addAction(self.grammar_toggle_action)
        
        align_action = QAction(self.colorize_icon("compare_arrows", "#e2e8f0"), "&Outil d'Alignement...", self)
        align_action.triggered.connect(self.show_alignment_dialog)
        tools_menu.addAction(align_action)

        backup_action = QAction(self.colorize_icon("history", "#e2e8f0"), "&Historique / Sauvegardes...", self)
        backup_action.triggered.connect(self.show_backup_dialog)
        tools_menu.addAction(backup_action)
        
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
        self.header = QFrame()
        self.header.setObjectName("Header")
        self.header.setFixedHeight(56)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)
        
        # Logo & Premium Badge
        logo_icon = QLabel()
        logo_icon.setFixedSize(32, 32)
        logo_icon.setPixmap(self.colorize_icon("menu_book", "#ffffff").pixmap(24, 24))
        logo_icon.setStyleSheet("background-color: #0d7ff2; border-radius: 4px;")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_container = QVBoxLayout()
        # Logo Title Tweak: Tighter spacing to match logo height
        title_container.setSpacing(0)
        title_container.setContentsMargins(0, 0, 0, 0)
        
        main_title = QLabel("NovelTrad")
        main_title.setStyleSheet("font-size: 15px; font-weight: 800; color: white; line-height: 14px; margin-bottom: 0px;") 
        
        premium_label = QLabel("PREMIUM")
        premium_label.setStyleSheet("color: #0d7ff2; font-size: 8px; font-weight: 700; letter-spacing: 1px; margin-top: 0px; line-height: 8px;")
        
        title_container.addWidget(main_title)
        title_container.addWidget(premium_label)
        
        header_layout.addWidget(logo_icon)
        header_layout.addLayout(title_container)
        
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(24)
        sep1.setStyleSheet("background-color: #333333;")
        header_layout.addWidget(sep1)
        
        header_layout.addWidget(sep1)
        
        # Project Info - Centered
        header_layout.addStretch()
        
        project_info = QHBoxLayout()
        project_info.setSpacing(8)
        project_label = QLabel("Projet :")
        project_label.setObjectName("ProjectTitle")
        self.project_name_label = QLabel("Aucun Projet Chargé")
        self.project_name_label.setObjectName("ProjectName")
        project_info.addWidget(project_label)
        project_info.addWidget(self.project_name_label)
        header_layout.addLayout(project_info)
        
        header_layout.addStretch()
        
        # Header Actions
        def create_header_btn(icon_name, tooltip, callback):
            btn = QPushButton()
            btn.setObjectName("IconButton")
            btn.setIcon(self.colorize_icon(icon_name, "#ffffff"))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            return btn

        self.btn_new = create_header_btn("add_circle", "Nouveau Projet", self.new_project_dialog)
        self.btn_open = create_header_btn("folder_open", "Ouvrir Projet (.ntrad)", self.open_project_dialog)
        self.btn_save = create_header_btn("save", "Sauvegarder (Ctrl+S)", self.save_current_segment)
        # Redundant buttons removed as per user request (moved to Menu Bar)
        
        header_layout.addWidget(self.btn_new)
        header_layout.addWidget(self.btn_open)
        header_layout.addWidget(self.btn_save)
        
        main_layout.addWidget(self.header)
        
        # 2. Main Workspace (Splitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #333333; }")
        
        # Left: Chapters
        self.sidebar_container = QFrame()
        self.sidebar_container.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 8, 0, 0)
        
        chapters_header = QHBoxLayout()
        chapters_header.setContentsMargins(16, 8, 16, 8)
        chapters_header.setContentsMargins(16, 8, 16, 8)
        ch_label = QLabel("CHAPITRES")
        ch_label.setObjectName("SidebarTitle")
        chapters_header.addWidget(ch_label)
        chapters_header.addStretch()
        
        # Add Chapter Button
        add_chapter_btn = QPushButton()
        add_chapter_btn.setObjectName("IconButton")
        add_chapter_btn = QPushButton()
        add_chapter_btn.setObjectName("IconButton")
        add_chapter_btn.setIcon(self.colorize_icon("add", "#cbd5e1")) # Usage of 'add' for plus symbol
        add_chapter_btn.setIconSize(QSize(16, 16))
        add_chapter_btn.setToolTip("Importer un Chapitre")
        add_chapter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_chapter_btn.clicked.connect(self.import_chapter_dialog)
        chapters_header.addWidget(add_chapter_btn)

        # Auto-Structure Button (AI)
        self.auto_struct_btn = QPushButton()
        self.auto_struct_btn.setObjectName("IconButton")
        self.auto_struct_btn.setIcon(self.colorize_icon("auto_fix_high", "#cbd5e1"))
        self.auto_struct_btn.setIconSize(QSize(16, 16))
        self.auto_struct_btn.setToolTip("Structure Auto (IA)")
        self.auto_struct_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_struct_btn.clicked.connect(self.run_structure_ai)
        chapters_header.addWidget(self.auto_struct_btn)
        
        sidebar_layout.addLayout(chapters_header)
        
        self.sidebar = Sidebar()
        self.sidebar.itemClicked.connect(self.on_chapter_selected)
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
        
        # Right: Tools
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)
        
        # Dictionary Support
        dict_box = QVBoxLayout()
        dict_box.setSpacing(8)
        dict_head = QHBoxLayout()
        dict_icon = QLabel()
        dict_icon.setPixmap(self.colorize_icon("search", "#ffffff").pixmap(16, 16))
        dict_title = QLabel("DICTIONNAIRE")
        dict_title.setObjectName("SidebarTitle")
        dict_head.addWidget(dict_icon)
        dict_head.addWidget(dict_title)
        dict_head.addStretch()
        dict_box.addLayout(dict_head)
        
        # Language selection now handled by footer global selectors
        # dict_controls removed as per user request
        
        self.dict_input = QLineEdit()
        self.dict_input.setPlaceholderText("Rechercher un mot...")
        self.dict_input.returnPressed.connect(self.on_dictionary_search)
        dict_box.addWidget(self.dict_input)
        
        self.dict_results = QListWidget()
        self.dict_results.setFixedHeight(120)
        dict_box.addWidget(self.dict_results)
        
        right_layout.addLayout(dict_box)

        # Glossary
        gloss_box = QVBoxLayout()
        gloss_head = QHBoxLayout()
        gloss_icon = QLabel()
        gloss_icon.setPixmap(self.colorize_icon("menu_book", "#ffffff").pixmap(16, 16))
        gloss_title = QLabel("GLOSSAIRE")
        gloss_title.setObjectName("SidebarTitle")
        gloss_head.addWidget(gloss_icon)
        gloss_head.addWidget(gloss_title)
        gloss_head.addStretch()
        
        # AI Scan Button
        self.scan_glossary_btn = QPushButton()
        self.scan_glossary_btn.setIcon(self.colorize_icon("manage_search", "#94a3b8"))
        self.scan_glossary_btn.setFixedSize(24, 24)
        self.scan_glossary_btn.setToolTip("Scanner Chapitre pour Termes (IA)")
        self.scan_glossary_btn.setStyleSheet("border: none;")
        self.scan_glossary_btn.clicked.connect(self.scan_chapter_glossary)
        gloss_head.addWidget(self.scan_glossary_btn)

        self.btn_manage_glossary = QPushButton()
        self.btn_manage_glossary.setIcon(self.colorize_icon("settings", "#94a3b8")) # Using settings icon for management
        self.btn_manage_glossary.setFixedSize(24, 24)
        self.btn_manage_glossary.setToolTip("Gérer Glossaire")
        self.btn_manage_glossary.setStyleSheet("border: none;")
        self.btn_manage_glossary.clicked.connect(self.open_glossary_manager)
        gloss_head.addWidget(self.btn_manage_glossary)
        gloss_box.addLayout(gloss_head)
        
        self.glossary_list = QListWidget()
        self.glossary_list.setObjectName("GlossaryList")
        self.glossary_list.setFixedHeight(150)
        gloss_box.addWidget(self.glossary_list)
        right_layout.addLayout(gloss_box)
        
        # Fuzzy Match Viewer
        self.fuzzy_viewer = FuzzyMatchViewer()
        self.fuzzy_viewer.applyMatch.connect(self.apply_translation_match)
        self.fuzzy_viewer.setFixedHeight(180)
        right_layout.addWidget(self.fuzzy_viewer)
        
        # AI Suggestions
        ai_box = QVBoxLayout()
        ai_head = QHBoxLayout()
        ai_icon = QLabel()
        ai_icon.setPixmap(self.colorize_icon("psychology", "#ffffff").pixmap(16, 16))
        ai_box_title = QLabel("SUGGESTIONS IA")
        ai_box_title.setObjectName("SidebarTitle")
        ai_head.addWidget(ai_icon)
        ai_head.addWidget(ai_box_title)
        ai_head.addStretch()
        ai_box.addLayout(ai_head)
        
        self.ai_card = QFrame()
        self.ai_card.setObjectName("ToolSection")
        self.ai_text = QLabel("Sélectionnez un segment...")
        self.ai_text.setWordWrap(True)
        self.ai_text.setStyleSheet("color: #94a3b8; font-style: italic; min-height: 60px;")
        ai_card_layout = QVBoxLayout(self.ai_card)
        ai_card_layout.addWidget(self.ai_text)
        ai_box.addWidget(self.ai_card)
        
        self.btn_regen = QPushButton("Régénérer Suggestion")
        self.btn_regen.setObjectName("PrimaryButton")
        self.btn_regen.setIcon(self.colorize_icon("bolt", "#ffffff"))
        self.btn_regen.clicked.connect(self.auto_translate_current)
        ai_box.addWidget(self.btn_regen)
        right_layout.addLayout(ai_box)
        
        # Concordancer Search
        conc_box = QVBoxLayout()
        conc_head = QHBoxLayout()
        conc_icon = QLabel()
        conc_icon.setPixmap(self.colorize_icon("search", "#ffffff").pixmap(16, 16))
        conc_title = QLabel("CONCORDANCIER")
        conc_title.setObjectName("SidebarTitle")
        conc_head.addWidget(conc_icon)
        conc_head.addWidget(conc_title)
        conc_head.addStretch()
        conc_box.addLayout(conc_head)
        
        self.conc_input = QLineEdit()
        self.conc_input.setPlaceholderText("Rechercher dans TM & projet...")
        self.conc_input.returnPressed.connect(self.search_concordancer)
        conc_box.addWidget(self.conc_input)
        
        self.conc_results = QListWidget()
        self.conc_results.setFixedHeight(100)
        conc_box.addWidget(self.conc_results)
        right_layout.addLayout(conc_box)
        
        # AI Chat Widget (collapsible)
        chat_head = QHBoxLayout()
        chat_icon = QLabel()
        chat_icon.setPixmap(self.colorize_icon("psychology", "#ffffff").pixmap(16, 16))
        chat_title = QLabel("CHAT IA")
        chat_title.setObjectName("SidebarTitle")
        chat_head.addWidget(chat_icon)
        chat_head.addWidget(chat_title)
        chat_head.addStretch()
        right_layout.addLayout(chat_head)
        
        self.chat_widget = ChatWidget()
        self.chat_widget.set_engine(self.llm_engine)
        self.chat_widget.setMaximumHeight(250)
        right_layout.addWidget(self.chat_widget)
        
        right_layout.addStretch()
        
        self.splitter.addWidget(self.sidebar_container)
        self.splitter.addWidget(editor_container)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
        
        # 3. Footer Area
        self.footer = QFrame()
        self.footer.setObjectName("Footer")
        self.footer.setFixedHeight(32)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)
        footer_layout.setSpacing(16)
        
        # Status
        self.connectivity_point = QWidget()
        self.connectivity_point.setFixedSize(8, 8)
        self.connectivity_point.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
        self.connectivity_label = QLabel("EN LIGNE")
        self.connectivity_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        footer_layout.addWidget(self.connectivity_point)
        footer_layout.addWidget(self.connectivity_label)
        
        footer_layout.addWidget(self.create_separator())
        
        # Language Selectors
        # Language Selectors
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setMinimumWidth(120)
        self.source_lang_combo.currentIndexChanged.connect(lambda: self.on_language_changed('source'))
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setMinimumWidth(120)
        self.target_lang_combo.currentIndexChanged.connect(lambda: self.on_language_changed('target'))
        
        footer_layout.addWidget(QLabel("Source :"))
        footer_layout.addWidget(self.source_lang_combo)
        footer_layout.addWidget(QLabel("Cible :"))
        footer_layout.addWidget(self.target_lang_combo)
        
        self.load_languages_into_footer()
        
        footer_layout.addStretch()
        
        # Progress
        progress_info = QVBoxLayout()
        progress_info.setSpacing(2)
        progress_head = QHBoxLayout()
        progress_head.addWidget(QLabel("PROGRESSION"))
        self.progress_pct = QLabel("0%")
        progress_head.addWidget(self.progress_pct)
        progress_head.itemAt(0).widget().setStyleSheet("font-size: 8px; font-weight: 800; color: #64748b;")
        self.progress_pct.setStyleSheet("font-size: 8px; font-weight: 800; color: #64748b;")
        
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setStyleSheet("background-color: #333333; border-radius: 2px;")
        self.progress_fill = QFrame(self.progress_bar)
        self.progress_fill.setFixedHeight(4)
        self.progress_fill.setStyleSheet("background-color: #0d7ff2; border-radius: 2px;")
        self.progress_fill.setFixedWidth(0)
        
        progress_info.addLayout(progress_head)
        progress_info.addWidget(self.progress_bar)
        footer_layout.addLayout(progress_info)
        
        footer_layout.addStretch()
        
        # Stats
        self.segments_count = QLabel("Segments: 0 / 0")
        self.words_count = QLabel("Words: 0 / 0")
        self.segments_count.setStyleSheet("font-size: 10px; color: #94a3b8;")
        self.words_count.setStyleSheet("font-size: 10px; color: #94a3b8;")
        footer_layout.addWidget(self.segments_count)
        footer_layout.addWidget(self.words_count)
        
        footer_layout.addWidget(self.create_separator())
        
        # Auto-saved
        save_icon = QLabel()
        save_icon.setPixmap(self.colorize_icon("cloud_done", "#64748b").pixmap(12, 12))
        save_label = QLabel("AUTO-SAUVEGARDÉ")
        save_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b;")
        footer_layout.addWidget(save_icon)
        footer_layout.addWidget(save_label)
        
        main_layout.addWidget(self.footer)

    def create_separator(self):
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(12)
        sep.setStyleSheet("background-color: #333333;")
        return sep

    def load_chapters(self):
        self.sidebar.clear()
        if not self.project_manager.current_project:
            return

        chapters = self.project_manager.get_chapters()
        for chapter in chapters:
            # Calculate progress? For now 0
            # Ideally: count(segments where status='translated') / count(segments)
            total = chapter.segments.count()
            translated = chapter.segments.where(Segment.status != SegmentStatus.UNTRANSLATED.value).count()
            progress = int((translated / total) * 100) if total > 0 else 0
            
            self.sidebar.add_item(chapter.id, chapter.title, progress)
        
        if self.project_manager.current_project:
            self.project_name_label.setText(self.project_manager.current_project.name)
            self.update_footer_stats()

    def on_chapter_selected(self, chapter_id):
        self.load_segments(chapter_id)

    def load_segments(self, chapter_id=None):
        # Clear existing cards
        while self.cards_layout.count() > 1: # Keep the stretch item at end? No, keep the stretch item which is added last
             # My layout logic: spaced items + stretch at end. 
             # I should clear all widgets.
             item = self.cards_layout.itemAt(0)
             if item.widget():
                 item.widget().deleteLater()
             self.cards_layout.removeItem(item)

        # Re-add stretch if needed? Or simply use insertWidget at count-1?
        # My init_ui adds stretch. So count is 1 (the stretch).
        # But loop above removes everything including stretch if I'm not careful.
        # Let's just clear safely.
        
        # Safer clear:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add stretch back at the end after adding items? Or add items then add stretch.
        
        if not self.project_manager.current_project:
             self.project_name_label.setText("Aucun Projet Chargé")
             return
             
        self.project_name_label.setText(self.project_manager.current_project.name)
        
        # If no chapter_id, pick first chapter
        if not chapter_id:
            chapters = self.project_manager.get_chapters()
            if chapters:
                chapter_id = chapters[0].id
                # Set active in sidebar
                self.sidebar.on_item_clicked(chapter_id)
        
        self.current_chapter_id = chapter_id

        if chapter_id:
             segments = self.project_manager.get_segments(chapter_id)
             for seg in segments: 
                card = SegmentCard(seg)
                card.set_layout_mode(self.current_layout_mode)
                card.set_grammar_enabled(self.realtime_grammar_enabled)
                card.clicked.connect(self.on_segment_card_clicked)
                card.textChanged.connect(self.on_segment_text_changed)
                card.lookupWord.connect(self.on_word_lookup)
                self.cards_layout.addWidget(card)
        
        self.cards_layout.addStretch()
            
        self.load_glossary()
        self.update_footer_stats()

    def on_segment_text_changed(self, segment_id, new_text):
        """Auto-save segment text changes."""
        try:
            segment = Segment.get_by_id(segment_id)
            segment.target_text = new_text
            # Simple status update logic
            if not segment.status or segment.status == SegmentStatus.UNTRANSLATED.value:
                 if new_text.strip():
                     segment.set_status(SegmentStatus.VALIDATED)
            
            segment.save()
        except:
            pass

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
        
        self.segments_count.setText(f"Segments : {translated} / {total}")
        self.words_count.setText(f"Mots : {target_words} / {source_words}")
        
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


    def on_segment_card_clicked(self, segment_id):
        self.current_segment_index = segment_id
        
        active_card = None
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard):
                is_active = (widget.segment_id == segment_id)
                widget.set_active(is_active)
                if is_active:
                    active_card = widget
                    
        if active_card:
            self.status_bar.showMessage(f"Segment {segment_id} sélectionné")
            self.ai_text.setText("Cliquez sur 'Régénérer Suggestion' pour obtenir une traduction IA.")
            
            # Auto-Glossary detection for current segment
            self.update_glossary_for_segment(active_card.segment.source_text)
            
            # Fetch and display TM matches
            matches = self.project_manager.search_translation_memory(active_card.segment.source_text)
            self.fuzzy_viewer.set_matches(matches)

    def update_glossary_for_segment(self, text):
        """Find and highlight glossary terms in the given text."""
        self.glossary_list.clear()
        if not self.project_manager.current_project:
            return
            
        project = self.project_manager.current_project
        terms = GlossaryTerm.select().where(GlossaryTerm.project == project)
        
        found = 0
        for term in terms:
            if term.source_term.lower() in text.lower():
                item = QListWidgetItem(f"{term.source_term} → {term.target_term}")
                # Color coding based on category/auto-gen?
                if term.is_auto_generated:
                    item.setForeground(Qt.GlobalColor.gray)
                self.glossary_list.addItem(item)
                found += 1
                
        if found == 0:
            self.glossary_list.addItem("Aucune correspondance pour ce segment.")

    def auto_translate_current(self):
        if self.current_segment_index == -1: return
        
        active_card = None
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.current_segment_index:
                active_card = widget
                break
                
        if not active_card: return
        
        try:
            self.status_bar.showMessage("Génération de la suggestion IA...")
            QApplication.processEvents()
            
            p = self.project_manager.current_project
            src = active_card.segment.source_text
            
            # Get glossary terms
            glossary_terms = {}
            for term in GlossaryTerm.select().where(GlossaryTerm.project == p):
                glossary_terms[term.source_term] = term.target_term
            
            engine = self.get_current_translation_engine()
            # Pass extra params if the engine supports them (LLMEngine does, others might ignore or need update)
            # We updated signatures in argos/nllb but let's be safe or just pass kwargs
            trans = engine.translate(
                src, p.source_language, p.target_language,
                glossary_terms=glossary_terms,
                genre=p.genre,
                custom_instructions=p.custom_instructions
            )
            
            active_card.target_edit.setPlainText(trans)
            self.ai_text.setText(trans)
            
            active_card.segment.target_text = trans
            active_card.segment.set_status(SegmentStatus.VALIDATED)
            active_card.segment.save()
            
            self.status_bar.showMessage("Traduit et Sauvegardé.")
        except Exception as e:
            self.ai_text.setText(f"Erreur : {e}")

    def on_word_lookup(self, word):
        """Handle word lookup from hover tooltip."""
        from src.core.dictionary_manager import DictionaryManager
        
        src_lang = self.source_lang_combo.currentText()
        tgt_lang = self.target_lang_combo.currentText()
        
        dm = DictionaryManager()
        results = dm.search(src_lang, tgt_lang, word)
        
        if results:
            result = results[0]
            tooltip_text = f"{result.source_term} → {result.target_term}"
            if result.context:
                tooltip_text += f"\n[{result.context}]"
            
            for i in range(self.cards_layout.count() - 1):
                widget = self.cards_layout.itemAt(i).widget()
                if isinstance(widget, SegmentCard):
                    widget.source_edit.setToolTip(tooltip_text)
        else:
            for i in range(self.cards_layout.count() - 1):
                widget = self.cards_layout.itemAt(i).widget()
                if isinstance(widget, SegmentCard):
                    widget.source_edit.setToolTip("")
    
    def editor_ai_refine(self):
        """Refine/Edit AI - improve machine translation."""
        if self.current_segment_index == -1:
            QMessageBox.warning(self, "Erreur", "Aucun segment sélectionné.")
            return
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Erreur", "Moteur IA non disponible.")
            return
        
        active_card = None
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard) and widget.segment_id == self.current_segment_index:
                active_card = widget
                break
                
        if not active_card: return
        
        source_text = active_card.segment.source_text
        translated_text = active_card.target_edit.toPlainText()
        
        if not translated_text:
            QMessageBox.warning(self, "Erreur", "Aucune traduction à affiner. Traduisez d'abord.")
            return
        
        try:
            self.status_bar.showMessage("Affinement de la traduction avec l'IA...")
            QApplication.processEvents()
            
            p = self.project_manager.current_project
            
            glossary_terms = {}
            for term in GlossaryTerm.select().where(GlossaryTerm.project == p):
                glossary_terms[term.source_term] = term.target_term
            
            refined = self.llm_engine.refine_translation(
                source_text,
                translated_text,
                src_lang=p.source_language,
                tgt_lang=p.target_language,
                glossary_terms=glossary_terms,
                genre=p.genre,
                custom_instructions=p.custom_instructions
            )
            
            active_card.target_edit.setPlainText(refined)
            self.ai_text.setText(refined)
            
            active_card.segment.target_text = refined
            active_card.segment.status = 'ai_refined'
            active_card.segment.save()
            
            self.status_bar.showMessage("Traduction affinée et sauvegardée.")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"L'affinement a échoué : {e}")

    def add_glossary_term(self):
        if not self.project_manager.current_project: return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter un Terme")
        layout = QFormLayout(dialog)
        
        src_input = QLineEdit()
        tgt_input = QLineEdit()
        layout.addRow("Source :", src_input)
        layout.addRow("Cible :", tgt_input)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("Ajouter")
        ok_btn.clicked.connect(dialog.accept)
        btns.addWidget(ok_btn)
        layout.addRow(btns)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            src = src_input.text().strip()
            tgt = tgt_input.text().strip()
            if src and tgt:
                GlossaryTerm.create(
                    project=self.project_manager.current_project,
                    source_term=src,
                    target_term=tgt,
                    is_auto_generated=False
                )
                self.load_glossary()

    def load_glossary(self):
        self.glossary_list.clear() # This works on QListWidget
        if not self.project_manager.current_project: return
        
        terms = GlossaryTerm.select().where(GlossaryTerm.project == self.project_manager.current_project)
        for term in terms:
           item = QListWidgetItem(f"{term.source_term} -> {term.target_term}")
           self.glossary_list.addItem(item)
           
    def scan_chapter_glossary(self):
        """Scans the current chapter for glossary terms using AI."""
        if not self.project_manager.current_project or not getattr(self, 'current_chapter_id', None):
            QMessageBox.warning(self, "Erreur", "Aucun chapitre actif à scanner.")
            return
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Erreur", "Moteur IA non disponible. Veuillez le configurer dans les paramètres.")
            return
            
        try:
            self.status_bar.showMessage("L'IA scanne le chapitre pour trouver des termes...")
            QApplication.processEvents()
            
            project = self.project_manager.current_project
            # Get segments specifically for the current chapter
            segments = Segment.select().where(Segment.chapter == self.current_chapter_id)
            
            if not segments.exists():
                QMessageBox.warning(self, "Erreur", "Aucun segment dans ce chapitre.")
                return
            
            # Combine text from first 200 segments
            combined_text = " ".join([s.source_text for s in segments[:200]])[:10000]
            
            existing_terms = list(GlossaryTerm.select().where(GlossaryTerm.project == project))
            existing_sources = {t.source_term for t in existing_terms}
            
            result_json = self.llm_engine.generate_glossary_incremental(
                combined_text,
                existing_terms,
                src_lang=project.source_language,
                tgt_lang=project.target_language,
                genre=project.genre or "general"
            )
            
            import json
            try:
                new_terms = json.loads(result_json) if result_json else []
            except:
                new_terms = []
            
            added_count = 0
            if new_terms:
                for term in new_terms:
                    source = term.get("source", "")
                    target = term.get("target", "")
                    category = term.get("category", "general")
                    
                    if source and target and source not in existing_sources:
                        GlossaryTerm.create(
                            project=project,
                            source_term=source,
                            target_term=target,
                            category=category,
                            is_auto_generated=True
                        )
                        added_count += 1
                        existing_sources.add(source) # Avoid duplicates in same batch
            
            self.load_glossary()
            self.status_bar.showMessage(f"Scan IA : {added_count} nouveaux termes ajoutés.")
            QMessageBox.information(self, "Résultat Scan IA", f"L'IA a détecté et ajouté {added_count} nouveaux termes au glossaire.")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec du scan du glossaire : {str(e)}")
            self.status_bar.showMessage("Échec du scan glossaire.")
            
    def run_structure_ai(self):
        """Run Structure AI to auto-detect chapters using a background worker."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet chargé.")
            return

        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Erreur", "Moteur IA non disponible pour la Structure Auto.\nVeuillez le configurer dans les paramètres.")
            return

        reply = QMessageBox.question(
            self, "Structure Auto du Projet",
            "Ceci va analyser le texte complet du projet pour détecter les limites de chapitres via l'IA.\n"
            "Cette opération peut prendre plusieurs minutes selon la taille du livre.\n\n"
            "Les chapitres existants seront écrasés. Voulez-vous continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.progress_dialog = QProgressDialog("Analyse de la structure...", "Annuler", 0, 100, self)
        self.progress_dialog.setWindowTitle("Structure AI")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None) # Can't safely cancel database atomic block yet
        
        self.structure_worker = AutoStructureWorker(self.project_manager, self.llm_engine)
        self.structure_worker.progress_update.connect(self._on_structure_progress)
        self.structure_worker.finished.connect(self._on_structure_finished)
        self.structure_worker.error.connect(self._on_structure_error)
        
        self.structure_worker.start()
        
    def _on_structure_progress(self, val, msg):
        self.progress_dialog.setValue(val)
        self.progress_dialog.setLabelText(msg)
        
    def _on_structure_finished(self, count):
        self.progress_dialog.close()
        
        if count > 0:
            self.load_chapters()
            self.load_segments()
            self.status_bar.showMessage(f"Structure AI : {count} chapitres créés.")
            QMessageBox.information(self, "Succès", f"Structure AI a détecté et créé {count} chapitres.\nVous pouvez maintenant utiliser la traduction par lot.")
        else:
            self.status_bar.showMessage("Structure AI : Aucun nouveau chapitre détecté.")
            QMessageBox.information(self, "Résultat", "Structure AI n'a pas pu détecter de nouvelles limites de chapitres claires.")
            
    def _on_structure_error(self, err_msg):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Erreur", f"Échec de Structure AI : {err_msg}")
        self.status_bar.showMessage("Structure AI a échoué.")

    def glossary_context_menu(self, pos):
        pass

    def on_dictionary_search(self):
        """Search the dictionary for the entered query"""
        from src.core.dictionary_manager import DictionaryManager
        
        query = self.dict_input.text().strip()
        if not query:
            return
            
        src_lang = self.source_lang_combo.currentText()
        tgt_lang = self.target_lang_combo.currentText()
        
        self.dict_results.clear()
        results = DictionaryManager.search_term(query, src_lang, tgt_lang)
        
        if not results:
            self.dict_results.addItem("Aucun résultat.")
            return
            
        for r in results:
            text = f"[{r['source_lang']}->{r['target_lang']}] {r['source_term']} ➔ {r['target_term']}"
            if r.get('context'):
                text += f"\n   [{r['context']}]"
            item = QListWidgetItem(text)
            self.dict_results.addItem(item)
            
        self.status_bar.showMessage(f"Found {len(results)} dictionary entries.")
        
    def import_dictionary(self):
        """Import dictionary from JSON file"""
        from src.core.dictionary_manager import DictionaryManager
        
        fname, _ = QFileDialog.getOpenFileName(
            self, "Importer Dictionnaire", "", 
            "Fichiers Dictionnaire (*.json);;Tous les fichiers (*)"
        )
        
        if not fname:
            return
            
        src_lang = self.source_lang_combo.currentText()
        tgt_lang = self.target_lang_combo.currentText()
        
        count = DictionaryManager.import_from_json(fname, src_lang, tgt_lang)
        
        QMessageBox.information(
            self, "Import Terminé", 
            f"Importé {count} termes."
        )
        self.status_bar.showMessage(f"Import du dictionnaire terminé : {count} termes.")

    def search_concordancer(self):
        """Search the active project segments and translation memory."""
        query = self.conc_input.text().strip()
        self.conc_results.clear()
        
        if not query:
            return
            
        concordancer = Concordancer()
        segments = self.project_manager.get_segments() if self.project_manager.current_project else []
        
        from src.core.database import TranslationMemory
        tm_entries = []
        if self.project_manager.current_project:
            # We fetch all TM entries for this project
            tm_entries = list(TranslationMemory.select().where(TranslationMemory.project == self.project_manager.current_project))
            
        results = concordancer.search(query, segments=segments, tm_entries=tm_entries, max_results=30)
        
        if not results:
            self.conc_results.addItem("Aucun résultat.")
            return
            
        for r in results:
            text = f"[{r.origin.upper()}] {r.source_text} ➔ {r.target_text}\n   Score: {r.score:.2f} ({r.match_type})"
            item = QListWidgetItem(text)
            self.conc_results.addItem(item)
            
        self.status_bar.showMessage(f"Concordancier : {len(results)} résultats trouvés.")

    def open_glossary_manager(self):
        """Open the comprehensive glossary editor."""
        if not self.project_manager.current_project: return
        
        dialog = GlossaryEditorDialog(self, self.project_manager.current_project)
        dialog.exec()
        # Refresh glossary list in main window
        self.load_glossary()

    def show_statistics_dialog(self):
        """Show project statistics and cost estimation."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Infos", "Aucun projet ouvert.")
            return
            
        dialog = StatisticsDialog(self.project_manager.current_project, self)
        dialog.exec()

    def batch_translate(self):
        """Translate all untranslated segments in the current chapter"""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet actif.")
            return
            
        engine = self.get_current_translation_engine()
        if not engine or not engine.is_available():
            QMessageBox.warning(self, "Error", "Selected translation engine not available. Please check Settings.")
            return
            
        # Get current chapter or all segments
        chapters = self.project_manager.get_chapters()
        if not chapters:
            QMessageBox.warning(self, "Erreur", "Aucun chapitre trouvé.")
            return
            
        # Ask user which chapter to translate
        chapter_names = [ch.title for ch in chapters]
        
        reply = QMessageBox.question(
            self, "Traduction par Lot",
            f"Traduire tous les segments non traduits ?\n\nCeci utilisera le moteur configuré.\n\nChapitre : {chapter_names[0]} (ou actif)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Get segments without translation
            segments = self.project_manager.get_segments()
            untranslated = [s for s in segments if not s.target_text or s.status == SegmentStatus.UNTRANSLATED.value]
            
            if not untranslated:
                QMessageBox.information(self, "Info", "Tous les segments sont déjà traduits !")
                return
                
            total = len(untranslated)
            self.status_bar.showMessage(f"Traduction de {total} segments en cours...")
            
            # Get glossary terms for this project
            project = self.project_manager.current_project
            glossary_terms = {}
            for term in GlossaryTerm.select().where(GlossaryTerm.project == project):
                glossary_terms[term.source_term] = term.target_term
            
            # Prepare texts for batch translation
            texts_to_translate = [s.source_text for s in untranslated]
            
            # Translate batch
            translations = engine.translate_batch(
                texts_to_translate,
                project.source_language,
                project.target_language,
                glossary_terms=glossary_terms,
                genre=project.genre,
                custom_instructions=project.custom_instructions
            )
            
            translated_count = 0
            
            # Apply translations
            with self.project_manager.db.atomic():
                for i, translation in enumerate(translations):
                    if i < len(untranslated):
                        seg = untranslated[i]
                        seg.target_text = translation
                        seg.status = 'translated'
                        seg.save()
                        translated_count += 1
                    
            # Refresh display
            self.load_segments()
            self.status_bar.showMessage(f"Traduction terminée : {translated_count} segments traduits.")
            QMessageBox.information(
                self, "Traduction par Lot Terminée",
                f"Traduit {translated_count} segments."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"La traduction par lot a échoué : {str(e)}")
            self.status_bar.showMessage("Échec de la traduction par lot.")

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
            self.status_bar.showMessage("Paramètres sauvegardés.", 3000)

    def toggle_realtime_grammar(self, checked):
        """Toggle grammar checking via menu."""
        from src.core.config_manager import ConfigManager
        self.realtime_grammar_enabled = checked
        ConfigManager().set("grammar_enabled", checked)
        self.update_all_cards_grammar()
        self.status_bar.showMessage(f"Vérification grammaire : {'Activée' if checked else 'Désactivée'}", 3000)

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

    def export_project_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet actif à exporter.")
            return
            
        source_path = self.project_manager.current_project.file_path
        _, ext = os.path.splitext(source_path)
        
        filters = f"Format Original (*{ext});;Fichier PDF (*.pdf)"
        if ext.lower() == ".pdf":
            filters = "Fichier PDF (*.pdf)"
            
        fname, selected_filter = QFileDialog.getSaveFileName(self, "Exporter Fichier Traduit", f"translated_output{ext}", filters)
        
        # Ensure the extension matches the selected filter if the user didn't type it
        if fname:
            if "PDF" in selected_filter and not fname.lower().endswith(".pdf"):
                fname = os.path.splitext(fname)[0] + ".pdf"
            elif "Original" in selected_filter and not fname.lower().endswith(ext.lower()):
                fname = os.path.splitext(fname)[0] + ext
        if fname:
            try:
                self.status_bar.showMessage(f"Export vers {fname}...")
                QApplication.processEvents()
                self.project_manager.export_project(fname)
                self.status_bar.showMessage("Export terminé.")
                QMessageBox.information(self, "Succès", "Fichier exporté avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de l'export : {str(e)}")

    def export_tmx_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet actif.")
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, "Exporter Mémoire TMX", "project_memory.tmx", "Fichiers TMX (*.tmx)")
        if fname:
            try:
                if self.project_manager.export_project_tmx(fname):
                    self.status_bar.showMessage(f"TMX exporté vers {fname}")
                    QMessageBox.information(self, "Succès", "TMX exporté avec succès.")
                else:
                    QMessageBox.critical(self, "Erreur", "Échec de l'export TMX.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec Export TMX : {e}")

    def import_tmx_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet actif.")
            return
            
        fname, _ = QFileDialog.getOpenFileName(self, "Importer Mémoire TMX", "", "Fichiers TMX (*.tmx)")
        if fname:
            try:
                count = self.project_manager.import_project_tmx(fname)
                self.load_segments()
                self.status_bar.showMessage(f"TMX importé : {count} segments mis à jour.")
                QMessageBox.information(self, "Succès", f"TMX importé avec succès. {count} segments mis à jour.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec Import TMX : {e}")

    # NOTE: Using new_project_dialog from new_project_dialog.py below
    def _old_new_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Nouveau Projet")
        dialog.setMinimumWidth(500)
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Nom du projet...")
        
        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_btn = QPushButton("Sélectionner Fichier...")
        folder_btn = QPushButton("Sélectionner Dossier...")
        file_layout.addWidget(file_btn)
        file_layout.addWidget(folder_btn)
        
        self.selected_path = None
        path_label = QLabel("Aucun fichier ou dossier sélectionné")
        path_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        
        # Languages
        langs = ['fr', 'en', 'zh', 'ja', 'ko', 'de', 'es', 'it', 'ru', 'pt', 'vi', 'th', 'ar']
        src_lang_combo = QComboBox()
        src_lang_combo.addItems(langs)
        src_lang_combo.setCurrentText('en')
        
        tgt_lang_combo = QComboBox()
        tgt_lang_combo.addItems(langs)
        tgt_lang_combo.setCurrentText('fr')
        
        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(30, 30)
        swap_btn.setToolTip("Échanger langues")
        
        def swap_langs():
            src = src_lang_combo.currentText()
            tgt = tgt_lang_combo.currentText()
            src_lang_combo.setCurrentText(tgt)
            tgt_lang_combo.setCurrentText(src)
            
        swap_btn.clicked.connect(swap_langs)
        
        lang_container = QWidget()
        lang_layout = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.addWidget(src_lang_combo)
        lang_layout.addWidget(swap_btn)
        lang_layout.addWidget(tgt_lang_combo)
        
        genre_combo = QComboBox()
        genre_combo.addItems(['general', 'xianxia', 'wuxia', 'scifi', 'fantasy', 'romance', 'mystery', 'horror'])
        genre_combo.setCurrentText('general')
        
        instructions_input = QTextEdit()
        instructions_input.setPlaceholderText("Optionnel : Instructions personnalisées pour la traduction (ton, style, etc.)")
        instructions_input.setMinimumHeight(80)
        
        def select_file():
            fname, _ = QFileDialog.getOpenFileName(self, "Ouvrir Fichier", "", "Fichiers Supportés (*.epub *.docx *.txt);;Tous les fichiers (*)")
            if fname:
                self.selected_path = fname
                path_label.setText(f"Fichier : {os.path.basename(fname)}")
                if not name_input.text():
                    name_input.setText(os.path.splitext(os.path.basename(fname))[0])
        
        def select_folder():
            dir_path = QFileDialog.getExistingDirectory(self, "Sélectionner Dossier de Chapitres (.txt)")
            if dir_path:
                self.selected_path = dir_path
                path_label.setText(f"Dossier : {os.path.basename(dir_path)}")
                if not name_input.text():
                    name_input.setText(os.path.basename(dir_path))
        
        file_btn.clicked.connect(select_file)
        folder_btn.clicked.connect(select_folder)
        
        layout.addRow("Nom du Projet :", name_input)
        layout.addRow("Source :", file_container)
        layout.addRow("", path_label)
        layout.addRow("Langues :", lang_container)
        layout.addRow("Genre :", genre_combo)
        layout.addRow("Instructions :", instructions_input)
        
        buttons = QHBoxLayout()
        create_btn = QPushButton("Créer Projet")
        create_btn.setProperty("primary", True)
        create_btn.clicked.connect(dialog.accept)
        create_btn.setMinimumHeight(40)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setMinimumHeight(40)
        
        buttons.addWidget(cancel_btn)
        buttons.addWidget(create_btn)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not name_input.text() or not self.selected_path:
                QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs")
                return
            self.create_project(
                name_input.text(), 
                self.selected_path,
                src_lang=src_lang_combo.currentText(),
                tgt_lang=tgt_lang_combo.currentText(),
                genre=genre_combo.currentText(),
                custom_instructions=instructions_input.toPlainText().strip() or None
            )

    def create_project(self, name, source_file, src_lang='en', tgt_lang='fr', genre='general', custom_instructions=None):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            projects_dir = os.path.join(base_dir, "projects")
            os.makedirs(projects_dir, exist_ok=True)
            db_path = os.path.join(projects_dir, f"{name}.ntrad")
            
            if os.path.exists(db_path):
                reply = QMessageBox.question(
                    self, "Project Exists", 
                    f"A project named '{name}' already exists. Overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        # Close current if it's the same
                        if self.project_manager.current_project and self.project_manager.current_project.name == name:
                            self.project_manager.close_project()
                        os.remove(db_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Could not remove existing project: {e}")
                        return
                else:
                    return

            self.project_manager.create_project(name, db_path, source_file, src_lang, tgt_lang, genre, custom_instructions)
            self.backup_manager = BackupManager(db_path)
            self.backup_manager.create_snapshot(label="init") # Initial snapshot
            
            self.load_chapters()
            self.load_segments()
            self.status_bar.showMessage(f"Project '{name}' created successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def new_project_dialog(self):
        from src.gui.new_project_dialog import NewProjectDialog
        
        dialog = NewProjectDialog(self, self.language_manager)
        if dialog.exec():
            data = dialog.get_data()
            
            # Ask where to save the project file (.ntrad)
            db_path, _ = QFileDialog.getSaveFileName(
                self, "Save Project File", 
                os.path.join(os.getcwd(), f"{data['name']}.ntrad"),
                "NovelTrad Project (*.ntrad)"
            )
            
            if db_path:
                try:
                    self.status_bar.showMessage("Creating project...")
                    QApplication.processEvents()
                    
                    self.project_manager.create_project(
                        name=data['name'],
                        db_path=db_path,
                        source_file=data['source_path'],
                        source_lang=data['source_lang'],
                        target_lang=data['target_lang']
                    )
                    
                    self.load_project(fname=db_path)
                    
                    # Force update of language selectors
                    self.load_languages_into_footer()
                    # Set combos
                    idx_src = self.source_lang_combo.findData(data['source_lang'])
                    if idx_src >= 0: self.source_lang_combo.setCurrentIndex(idx_src)
                    
                    idx_tgt = self.target_lang_combo.findData(data['target_lang'])
                    if idx_tgt >= 0: self.target_lang_combo.setCurrentIndex(idx_tgt)

                    QMessageBox.information(self, "Success", "Project created successfully!")
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create project: {e}")

    def import_chapter_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No project loaded.")
            return

        fname, _ = QFileDialog.getOpenFileName(
            self, "Import Chapter", "", 
            "Documents (*.txt *.docx *.epub *.pdf);;All Files (*)"
        )
        
        if fname:
            try:
                self.project_manager.import_file(fname)
                self.load_chapters()
                self.status_bar.showMessage(f"Imported chapter: {os.path.basename(fname)}")
            except Exception as e:
                 QMessageBox.critical(self, "Error", f"Failed to import chapter: {str(e)}")

    def open_project_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "NovelTrad Projects (*.ntrad)")
        if fname:
            self.load_project(fname)

    def load_project(self, fname):
        try:
            self.project_manager.load_project(fname)
            self.backup_manager = BackupManager(fname)
            self.backup_manager.create_snapshot(label="load") # Snapshot on load
            
            # Update Header
            if self.project_manager.current_project:
                self.project_name_label.setText(self.project_manager.current_project.name)
            
            self.load_chapters()
            self.load_segments()
            self.status_bar.showMessage(f"Loaded project: {fname}")
            
            # Update Footer languages
            p = self.project_manager.current_project
            if p:
                idx_src = self.source_lang_combo.findData(p.source_language)
                if idx_src >= 0: self.source_lang_combo.setCurrentIndex(idx_src)
                
                idx_tgt = self.target_lang_combo.findData(p.target_language)
                if idx_tgt >= 0: self.target_lang_combo.setCurrentIndex(idx_tgt)
                
        except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")

    def show_search_replace(self):
        """Show Search & Replace dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        from src.gui.search_replace_dialog import SearchReplaceDialog
        dialog = SearchReplaceDialog(self, self.project_manager)
        dialog.show()

    def show_statistics(self):
        """Show project statistics."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        project = self.project_manager.current_project
        segments = self.project_manager.get_segments()
        
        total_segments = len(segments)
        untranslated = sum(1 for s in segments if not s.target_text or s.status == SegmentStatus.UNTRANSLATED.value)
        machine = sum(1 for s in segments if s.status == SegmentStatus.MACHINE.value)
        ai_refined = sum(1 for s in segments if s.status == SegmentStatus.AI_REFINED.value)
        validated = sum(1 for s in segments if s.status == SegmentStatus.VALIDATED.value)
        
        source_words = sum(len(s.source_text.split()) for s in segments)
        target_words = sum(len(s.target_text.split()) if s.target_text else 0 for s in segments)
        
        progress = int(((total_segments - untranslated) / total_segments * 100)) if total_segments > 0 else 0
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Statistics - {project.name}")
        dialog.resize(400, 350)
        layout = QVBoxLayout(dialog)
        
        title = QLabel(f"<h2>{project.name}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel(f"""
<b>Languages:</b> {project.source_language} → {project.target_language}<br>
<b>Genre:</b> {project.genre or 'general'}<br><br>

<b>Segments:</b> {total_segments}<br>
<b>Progress:</b> {progress}%<br><br>

<b>Status Breakdown:</b><br>
• Untranslated: {untranslated}<br>
• Machine Translated: {machine}<br>
• AI Refined: {ai_refined}<br>
• Validated: {validated}<br><br>

<b>Word Count:</b><br>
• Source: {source_words:,} words<br>
• Target: {target_words:,} words
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()

    def auto_structure_chapters(self):
        """Invoke Structure AI via ProjectManager."""
        if not self.project_manager.current_project:
            return
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Error", "LLM engine not available for Structure AI.")
            return

        reply = QMessageBox.question(
            self, "Structure AI",
            "This will use AI to detect chapters in your project and re-organize segments. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.status_bar.showMessage("AI is detecting chapters...")
                QApplication.processEvents()
                
                count = self.project_manager.auto_structure_project(self.llm_engine)
                
                if count > 0:
                    QMessageBox.information(self, "Success", f"Detected and created {count} new chapters.")
                    self.load_chapters()
                    self.load_segments() # Reload view
                else:
                    QMessageBox.warning(self, "Structure AI", "No new chapters detected or an error occurred.")
                    
                self.status_bar.showMessage("Structure AI complete.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Structure AI failed: {str(e)}")
                self.status_bar.showMessage("Structure AI error.")

    def load_languages_into_footer(self):
        languages = self.language_manager.get_supported_languages()
        
        self.source_lang_combo.blockSignals(True)
        self.target_lang_combo.blockSignals(True)
        
        self.source_lang_combo.clear()
        self.target_lang_combo.clear()
        
        icon_path_check = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icons", "check_circle.svg")
        
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
        self.status_bar.showMessage(f"Project languages updated: {self.source_lang_combo.currentText()} -> {self.target_lang_combo.currentText()}", 3000)

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
            self.status_bar.showMessage("Connexion perdue. Passage en mode secours (moteurs locaux).", 5000)

    def show_alignment_dialog(self):
        """Open the alignment tool dialog."""
        dialog = AlignmentDialog(self, project_manager=self.project_manager)
        dialog.exec()

    def show_backup_dialog(self):
        """Open the snapshot management dialog."""
        if not self.backup_manager:
            QMessageBox.warning(self, "Snapshots", "Veuillez d'abord ouvrir un projet.")
            return
            
        from src.gui.backup_dialog import BackupDialog
        dialog = BackupDialog(self.backup_manager, self)
        if dialog.exec():
            # If restoration succeeded
            self.load_chapters()
            self.load_segments()
            self.status_bar.showMessage("Version du projet restaurée.")

    def show_qa_dialog(self):
        """Open the QA Check dialog for current project segments."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet ouvert.")
            return

        segments = list(self.project_manager.get_segments())
        glossary_terms = list(
            GlossaryTerm.select().where(
                GlossaryTerm.project == self.project_manager.current_project
            )
        )

        dialog = QADialog(self, segments=segments, glossary_terms=glossary_terms)
        dialog.navigate_to_segment.connect(self.on_segment_card_clicked)
        dialog.exec()

    def search_concordancer(self):
        """Search the concordancer for the entered query."""
        query = self.conc_input.text().strip()
        if not query:
            return

        self.conc_results.clear()

        concordancer = Concordancer()
        segments = []
        tm_entries = []

        if self.project_manager.current_project:
            segments = list(self.project_manager.get_segments())

        results = concordancer.search(query, segments=segments, tm_entries=tm_entries)

        if results:
            for r in results:
                text = f"[{r.match_type}] {r.source_text[:60]}…"
                if r.target_text:
                    text += f"\n→ {r.target_text[:60]}…"
                item = QListWidgetItem(text)
                self.conc_results.addItem(item)
        else:
            self.conc_results.addItem("Aucun résultat trouvé.")

    def show_custom_instructions_dialog(self):
        """Open dialog to edit custom AI instructions."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Erreur", "Aucun projet ouvert.")
            return

        current_instructions = self.project_manager.current_project.custom_instructions
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

    def batch_translate(self):
        """Open Batch Translation Dialog."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return

        # Prepare engines
        # We might have LLM, NLLB, etc.
        # For now, list available ones.
        engines = []
        if self.llm_engine: engines.append(self.llm_engine)
        
        # Check other engines if lazy loaded or instantiated
        # self.nllb_engine?
        nllb = get_engine_instance('NLLB')
        if nllb and nllb.is_available(): engines.append(nllb)
        
        argos = get_engine_instance('Argos')
        if argos and argos.is_available(): engines.append(argos)

        dialog = BatchTranslationDialog(self.project_manager, engines, self)
        if hasattr(self, 'current_chapter_id') and self.current_chapter_id:
            dialog.set_current_chapter(self.current_chapter_id)
            
        dialog.exec()
        
        # Reload after batch
        if hasattr(self, 'current_chapter_id') and self.current_chapter_id:
            self.load_segments(self.current_chapter_id)
        self.update_footer_stats()

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


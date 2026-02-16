from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QSplitter, 
                             QListWidget, QTextEdit, QLabel, QFileDialog, QDockWidget, QTabWidget, QMenu,
                             QStatusBar, QToolBar, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidgetItem,
                             QScrollArea, QFrame, QGridLayout, QCheckBox)
from src.gui.components import SegmentCard, Sidebar
from src.gui.settings_dialog import SettingsDialog
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QColor, QPixmap
import os
import sys

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.project_manager import ProjectManager
from src.engines import get_engine_instance, list_engines
from src.core.database import Segment, GlossaryTerm, Chapter
from src.core.language_manager import LanguageManager

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
        
        # Apply Styles (load from config)
        self.apply_theme()
        
        self.init_ui()
        self.setup_shortcuts()
        
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        from PyQt6.QtCore import Qt
        
        shortcuts = [
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_N, self.new_project_dialog),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_O, self.open_project_dialog),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_S, self.save_current_segment),
            (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier | Qt.Key.Key_C, self.batch_translate),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_F, self.show_search_replace),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_G, self.scan_chapter_glossary),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_R, self.auto_translate_current),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_E, self.editor_ai_refine),
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Comma, self.show_settings),
            (Qt.Key.Key_F5, self.show_statistics),
        ]
        
        for key, slot in shortcuts:
            shortcut = QShortcut(self)
            shortcut.setKey(QKeySequence(key))
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
                    widget.segment.status = 'translated'
                    # Add to Translation Memory
                    self.project_manager.add_to_tm(widget.segment.source_text, text)
                widget.segment.save()
                self.status_bar.showMessage(f"Segment {self.current_segment_index} saved.")
                self.update_footer_stats()
                self.update_current_chapter_progress()
                break

    def update_current_chapter_progress(self):
        """Update the progress bar for the current chapter in the sidebar."""
        if not hasattr(self, 'current_chapter_id') or not self.current_chapter_id:
            return
            
        chapter = Chapter.get_by_id(self.current_chapter_id)
        total = chapter.segments.count()
        translated = chapter.segments.where(Segment.status != 'untranslated').count()
        
        progress = int((translated / total) * 100) if total > 0 else 0
        self.sidebar.update_item_progress(self.current_chapter_id, progress)
        
    def apply_theme(self):
        import json
        import os
        from PyQt6.QtGui import QFont
        
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        theme = "Dark (Default)"
        font_size_name = "Medium"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                theme = config.get('theme', 'Dark (Default)')
                font_size_name = config.get('font_size', 'Medium')
            except:
                pass
        
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
        if "Dark" in theme:
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
        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        


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
        title_container.setSpacing(0)
        title_container.setContentsMargins(0, 4, 0, 4)
        
        main_title = QLabel("NovelTrad")
        main_title.setStyleSheet("font-size: 18px; font-weight: 800; color: white;")
        
        premium_label = QLabel("PREMIUM")
        premium_label.setStyleSheet("color: #0d7ff2; font-size: 9px; font-weight: 700; letter-spacing: 2px;")
        
        title_container.addWidget(main_title)
        title_container.addWidget(premium_label)
        
        header_layout.addWidget(logo_icon)
        header_layout.addLayout(title_container)
        
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(24)
        sep1.setStyleSheet("background-color: #333333;")
        header_layout.addWidget(sep1)
        
        # Project Info
        project_info = QHBoxLayout()
        project_info.setSpacing(8)
        project_label = QLabel("Project:")
        project_label.setObjectName("ProjectTitle")
        self.project_name_label = QLabel("No Project Loaded")
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

        self.btn_new = create_header_btn("add_circle", "New Project", self.new_project_dialog)
        self.btn_open = create_header_btn("folder_open", "Open Existing Project (.ntrad)", self.open_project_dialog)
        self.btn_save = create_header_btn("save", "Save (Ctrl+S)", self.save_current_segment)
        self.btn_export = create_header_btn("file_download", "Export", self.export_project_dialog)
        
        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(24)
        sep2.setStyleSheet("background-color: #333333;")
        
        self.btn_settings = create_header_btn("settings", "Settings (Ctrl+,)", self.show_settings)
        
        header_layout.addWidget(self.btn_new)
        header_layout.addWidget(self.btn_open)
        header_layout.addWidget(self.btn_save)
        header_layout.addWidget(self.btn_export)
        header_layout.addWidget(sep2)
        header_layout.addWidget(self.btn_settings)
        
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
        ch_label = QLabel("CHAPTERS")
        ch_label.setObjectName("SidebarTitle")
        chapters_header.addWidget(ch_label)
        chapters_header.addStretch()
        
        # Add Chapter Button
        add_chapter_btn = QPushButton()
        add_chapter_btn.setObjectName("IconButton")
        add_chapter_btn.setIcon(self.colorize_icon("add_circle", "#cbd5e1"))
        add_chapter_btn.setIconSize(QSize(16, 16))
        add_chapter_btn.setToolTip("Import Chapter from File")
        add_chapter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_chapter_btn.clicked.connect(self.import_chapter_dialog)
        chapters_header.addWidget(add_chapter_btn)
        
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
        dict_title = QLabel("DICTIONARY")
        dict_title.setObjectName("SidebarTitle")
        dict_head.addWidget(dict_icon)
        dict_head.addWidget(dict_title)
        dict_head.addStretch()
        dict_box.addLayout(dict_head)
        
        dict_controls = QHBoxLayout()
        self.dict_src_lang = QComboBox()
        self.dict_tgt_lang = QComboBox()
        # Populate with some defaults
        for lang in ["Chinese", "English", "French", "Japanese"]:
            self.dict_src_lang.addItem(lang)
            self.dict_tgt_lang.addItem(lang)
        self.dict_src_lang.setCurrentText("Chinese")
        self.dict_tgt_lang.setCurrentText("French")
        
        dict_controls.addWidget(self.dict_src_lang)
        dict_controls.addWidget(self.dict_tgt_lang)
        dict_box.addLayout(dict_controls)
        
        self.dict_input = QLineEdit()
        self.dict_input.setPlaceholderText("Search word...")
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
        gloss_title = QLabel("GLOSSARY MATCHES")
        gloss_title.setObjectName("SidebarTitle")
        gloss_head.addWidget(gloss_icon)
        gloss_head.addWidget(gloss_title)
        gloss_head.addStretch()
        gloss_box.addLayout(gloss_head)
        
        self.glossary_list = QListWidget()
        self.glossary_list.setObjectName("GlossaryList")
        self.glossary_list.setFixedHeight(150)
        gloss_box.addWidget(self.glossary_list)
        right_layout.addLayout(gloss_box)
        
        # AI Suggestions
        ai_box = QVBoxLayout()
        ai_head = QHBoxLayout()
        ai_icon = QLabel()
        ai_icon.setPixmap(self.colorize_icon("psychology", "#ffffff").pixmap(16, 16))
        ai_box_title = QLabel("AI SUGGESTIONS")
        ai_box_title.setObjectName("SidebarTitle")
        ai_head.addWidget(ai_icon)
        ai_head.addWidget(ai_box_title)
        ai_head.addStretch()
        ai_box.addLayout(ai_head)
        
        self.ai_card = QFrame()
        self.ai_card.setObjectName("ToolSection")
        self.ai_text = QLabel("Select a segment...")
        self.ai_text.setWordWrap(True)
        self.ai_text.setStyleSheet("color: #94a3b8; font-style: italic; min-height: 60px;")
        ai_card_layout = QVBoxLayout(self.ai_card)
        ai_card_layout.addWidget(self.ai_text)
        ai_box.addWidget(self.ai_card)
        
        self.btn_regen = QPushButton("Regenerate Suggestion")
        self.btn_regen.setObjectName("PrimaryButton")
        self.btn_regen.setIcon(self.colorize_icon("bolt", "#ffffff"))
        self.btn_regen.clicked.connect(self.auto_translate_current)
        ai_box.addWidget(self.btn_regen)
        right_layout.addLayout(ai_box)
        
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
        status_point = QWidget()
        status_point.setFixedSize(8, 8)
        status_point.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
        status_label = QLabel("SYSTEM READY")
        status_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        footer_layout.addWidget(status_point)
        footer_layout.addWidget(status_label)
        
        footer_layout.addWidget(self.create_separator())
        
        # Language Selectors
        # Language Selectors
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setMinimumWidth(120)
        self.source_lang_combo.currentIndexChanged.connect(lambda: self.on_language_changed('source'))
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setMinimumWidth(120)
        self.target_lang_combo.currentIndexChanged.connect(lambda: self.on_language_changed('target'))
        
        footer_layout.addWidget(QLabel("Source:"))
        footer_layout.addWidget(self.source_lang_combo)
        footer_layout.addWidget(QLabel("Target:"))
        footer_layout.addWidget(self.target_lang_combo)
        
        self.load_languages_into_footer()
        
        footer_layout.addStretch()
        
        # Progress
        progress_info = QVBoxLayout()
        progress_info.setSpacing(2)
        progress_head = QHBoxLayout()
        progress_head.addWidget(QLabel("OVERALL PROGRESS"))
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
        save_label = QLabel("AUTO-SAVED")
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
            translated = chapter.segments.where(Segment.status == 'translated').count()
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
             self.project_name_label.setText("No Project Loaded")
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
                card.clicked.connect(self.on_segment_card_clicked)
                card.lookupWord.connect(self.on_word_lookup)
                self.cards_layout.addWidget(card)
        
        self.cards_layout.addStretch()
            
        self.load_glossary()
        self.update_footer_stats()

    def update_footer_stats(self):
        """Update Footer with project statistics and progress."""
        if not self.project_manager.current_project:
            return
            
        project = self.project_manager.current_project
        segments = list(self.project_manager.get_segments())
        
        total = len(segments)
        translated = sum(1 for s in segments if s.status and s.status != 'untranslated')
        
        # Word counts
        source_words = sum(len(s.source_text.split()) for s in segments)
        target_words = sum(len(s.target_text.split()) if s.target_text else 0 for s in segments)
        
        self.segments_count.setText(f"Segments: {translated} / {total}")
        self.words_count.setText(f"Words: {target_words} / {source_words}")
        
        progress = int((translated / total) * 100) if total > 0 else 0
        
        # Update UI
        self.source_lang_label.setText(f"Source: {project.source_language.upper()}")
        self.target_lang_label.setText(f"Target: {project.target_language.upper()}")
        
        self.progress_pct.setText(f"{progress}%")
        
        # Progress Bar fill (max width 200 as defined in UI)
        fill_width = int((progress / 100.0) * 200)
        self.progress_fill.setFixedWidth(fill_width)
        
        self.segments_count.setText(f"Segments: {translated} / {total}")
        self.words_count.setText(f"Words: {target_words:,} / {source_words:,}")


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
            self.status_bar.showMessage(f"Selected Segment {segment_id}")
            self.ai_text.setText("Click 'Regenerate' to get AI suggestion for this segment.")
            
            # Auto-Glossary detection for current segment
            self.update_glossary_for_segment(active_card.segment.source_text)

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
            self.glossary_list.addItem("No matches for this segment.")

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
            self.status_bar.showMessage("Generating AI suggestion...")
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
            active_card.segment.status = 'translated'
            active_card.segment.save()
            
            self.status_bar.showMessage("Translated and Saved.")
        except Exception as e:
            self.ai_text.setText(f"Error: {e}")

    def on_word_lookup(self, word):
        """Handle word lookup from hover tooltip."""
        from src.core.dictionary_manager import DictionaryManager
        
        src_lang = self.dict_src_lang.currentText()
        tgt_lang = self.dict_tgt_lang.currentText()
        
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
            QMessageBox.warning(self, "Error", "No segment selected.")
            return
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Error", "LLM engine not available.")
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
            QMessageBox.warning(self, "Error", "No translation to refine. Translate first.")
            return
        
        try:
            self.status_bar.showMessage("Refining translation with AI...")
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
            
            self.status_bar.showMessage("Translation refined and saved.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Refinement failed: {e}")

    def add_glossary_term(self):
        if not self.project_manager.current_project: return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Term")
        layout = QFormLayout(dialog)
        
        src_input = QLineEdit()
        tgt_input = QLineEdit()
        layout.addRow("Source:", src_input)
        layout.addRow("Target:", tgt_input)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("Add")
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
            QMessageBox.warning(self, "Error", "No active chapter to scan.")
            return
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Error", "LLM engine not available. Please configure in Settings.")
            return
            
        try:
            self.status_bar.showMessage("AI scanning chapter for terms...")
            QApplication.processEvents()
            
            project = self.project_manager.current_project
            # Get segments specifically for the current chapter
            segments = Segment.select().where(Segment.chapter == self.current_chapter_id)
            
            if not segments.exists():
                QMessageBox.warning(self, "Error", "No segments in this chapter.")
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
            self.status_bar.showMessage(f"AI Scan: {added_count} new terms added.")
            QMessageBox.information(self, "AI Scan Result", f"AI detected and added {added_count} new terms to the glossary.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan glossary: {str(e)}")
            self.status_bar.showMessage("Glossary scan failed.")
            
    def glossary_context_menu(self, pos):
        pass

    def on_dictionary_search(self):
        """Search the dictionary for the entered query"""
        from src.core.dictionary_manager import DictionaryManager
        
        query = self.dict_input.text().strip()
        if not query:
            return
            
        src_lang = self.dict_src_lang.currentText()
        tgt_lang = self.dict_tgt_lang.currentText()
        
        dm = DictionaryManager()
        results = dm.search_bidirectional(query, src_lang, tgt_lang)
        
        self.dict_results.clear()
        for r in results:
            text = f"{r.source_term} → {r.target_term}"
            if r.context:
                text += f"\n   [{r.context}]"
            item = QListWidgetItem(text)
            self.dict_results.addItem(item)
            
        self.status_bar.showMessage(f"Found {len(results)} dictionary entries.")
        
    def import_dictionary(self):
        """Import dictionary from CSV file"""
        from src.core.dictionary_manager import DictionaryManager
        
        fname, _ = QFileDialog.getOpenFileName(
            self, "Import Dictionary", "", 
            "Dictionary Files (*.csv *.txt);;All Files (*)"
        )
        
        if not fname:
            return
            
        src_lang = self.dict_src_lang.currentText()
        tgt_lang = self.dict_tgt_lang.currentText()
        
        dm = DictionaryManager()
        count, errors = dm.import_csv(fname, src_lang, tgt_lang)
        
        QMessageBox.information(
            self, "Import Complete", 
            f"Imported {count} terms.\nErrors: {errors}"
        )
        self.status_bar.showMessage(f"Dictionary import complete: {count} terms.")

    def batch_translate(self):
        """Translate all untranslated segments in the current chapter"""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        engine = self.get_current_translation_engine()
        if not engine or not engine.is_available():
            QMessageBox.warning(self, "Error", "Selected translation engine not available. Please check Settings.")
            return
            
        # Get current chapter or all segments
        chapters = self.project_manager.get_chapters()
        if not chapters:
            QMessageBox.warning(self, "Error", "No chapters found.")
            return
            
        # Ask user which chapter to translate
        chapter_names = [ch.title for ch in chapters]
        
        reply = QMessageBox.question(
            self, "Batch Translate",
            f"Translate all untranslated segments?\n\nThis will translate using the LLM engine.\n\nChapter: {chapter_names[0]} (or current)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Get segments without translation
            segments = self.project_manager.get_segments()
            untranslated = [s for s in segments if not s.target_text or s.status == 'untranslated']
            
            if not untranslated:
                QMessageBox.information(self, "Info", "All segments already translated!")
                return
                
            total = len(untranslated)
            self.status_bar.showMessage(f"Translating {total} segments...")
            
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
            self.status_bar.showMessage(f"Translation complete: {translated_count} segments translated.")
            QMessageBox.information(
                self, "Batch Translate Complete",
                f"Translated {translated_count} segments."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Batch translation failed: {str(e)}")
            self.status_bar.showMessage("Batch translation failed.")

    def show_settings(self):
        from src.gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.apply_theme()
            self.status_bar.showMessage("Settings saved and theme applied.", 3000)

    def show_language_store(self):
        from src.gui.language_store import LanguageStore
        dialog = LanguageStore(self)
        dialog.exec()

    def export_project_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project to export.")
            return
            
        source_path = self.project_manager.current_project.file_path
        _, ext = os.path.splitext(source_path)
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export Translated File", f"translated_output{ext}", f"Supported Files (*{ext})")
        if fname:
            try:
                self.status_bar.showMessage(f"Exporting to {fname}...")
                QApplication.processEvents()
                self.project_manager.export_project(fname)
                self.status_bar.showMessage("Export complete.")
                QMessageBox.information(self, "Success", "File exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def export_tmx_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, "Export TMX Memory", "project_memory.tmx", "TMX Files (*.tmx)")
        if fname:
            try:
                if self.project_manager.export_project_tmx(fname):
                    self.status_bar.showMessage(f"TMX exported to {fname}")
                    QMessageBox.information(self, "Success", "TMX exported successfully.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to export TMX.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"TMX Export failed: {e}")

    def import_tmx_dialog(self):
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        fname, _ = QFileDialog.getOpenFileName(self, "Import TMX Memory", "", "TMX Files (*.tmx)")
        if fname:
            try:
                count = self.project_manager.import_project_tmx(fname)
                self.load_segments()
                self.status_bar.showMessage(f"TMX imported: {count} segments updated.")
                QMessageBox.information(self, "Success", f"TMX imported successfully. {count} segments were updated.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"TMX Import failed: {e}")

    def new_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        dialog.setMinimumWidth(500)
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter project name...")
        
        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_btn = QPushButton("Select File...")
        folder_btn = QPushButton("Select Folder...")
        file_layout.addWidget(file_btn)
        file_layout.addWidget(folder_btn)
        
        self.selected_path = None
        path_label = QLabel("No file or folder selected")
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
        swap_btn.setToolTip("Swap languages")
        
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
        instructions_input.setPlaceholderText("Optional: Custom translation instructions (tone, style, etc.)")
        instructions_input.setMinimumHeight(80)
        
        def select_file():
            fname, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Supported Files (*.epub *.docx *.txt);;All Files (*)")
            if fname:
                self.selected_path = fname
                path_label.setText(f"File: {os.path.basename(fname)}")
                if not name_input.text():
                    name_input.setText(os.path.splitext(os.path.basename(fname))[0])
        
        def select_folder():
            dir_path = QFileDialog.getExistingDirectory(self, "Select Folder Containing Chapters (.txt)")
            if dir_path:
                self.selected_path = dir_path
                path_label.setText(f"Folder: {os.path.basename(dir_path)}")
                if not name_input.text():
                    name_input.setText(os.path.basename(dir_path))
        
        file_btn.clicked.connect(select_file)
        folder_btn.clicked.connect(select_folder)
        
        layout.addRow("Project Name:", name_input)
        layout.addRow("Source:", file_container)
        layout.addRow("", path_label)
        layout.addRow("Languages:", lang_container)
        layout.addRow("Genre:", genre_combo)
        layout.addRow("Instructions:", instructions_input)
        
        buttons = QHBoxLayout()
        create_btn = QPushButton("Create Project")
        create_btn.setProperty("primary", True)
        create_btn.clicked.connect(dialog.accept)
        create_btn.setMinimumHeight(40)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setMinimumHeight(40)
        
        buttons.addWidget(cancel_btn)
        buttons.addWidget(create_btn)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not name_input.text() or not self.selected_path:
                QMessageBox.warning(self, "Error", "Please fill all fields")
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
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Search & Replace")
        dialog.resize(500, 200)
        layout = QFormLayout(dialog)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Text to find...")
        
        replace_input = QLineEdit()
        replace_input.setPlaceholderText("Replace with...")
        
        use_regex = QCheckBox("Use Regular Expressions")
        case_sensitive = QCheckBox("Case Sensitive")
        case_sensitive.setChecked(True)
        
        layout.addRow("Search:", search_input)
        layout.addRow("Replace:", replace_input)
        layout.addRow(use_regex)
        layout.addRow(case_sensitive)
        
        result_label = QLabel("Will search in all segments")
        layout.addRow(result_label)
        
        buttons = QHBoxLayout()
        
        find_btn = QPushButton("Find Next")
        find_btn.clicked.connect(lambda: self._find_text(search_input, use_regex.isChecked(), case_sensitive.isChecked()))
        
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(lambda: self._replace_text(search_input, replace_input, use_regex.isChecked(), case_sensitive.isChecked()))
        
        replace_all_btn = QPushButton("Replace All")
        replace_all_btn.clicked.connect(lambda: self._replace_all_text(search_input, replace_input, use_regex.isChecked(), case_sensitive.isChecked()))
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        
        buttons.addWidget(find_btn)
        buttons.addWidget(replace_btn)
        buttons.addWidget(replace_all_btn)
        buttons.addWidget(close_btn)
        
        layout.addRow(buttons)
        dialog.exec()

    def _find_text(self, search_input, use_regex, case_sensitive):
        """Find text in segments."""
        import re
        
        search_text = search_input.text()
        if not search_text:
            return
            
        segments = self.project_manager.get_segments()
        pattern_flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            if use_regex:
                pattern = re.compile(search_text, pattern_flags)
            else:
                pattern = re.compile(re.escape(search_text), pattern_flags)
        except re.error as e:
            QMessageBox.warning(self, "Invalid Regex", str(e))
            return
            
        for seg in segments:
            if seg.target_text and pattern.search(seg.target_text):
                self.load_segments(seg.chapter_id)
                self.current_segment_index = seg.index
                for i in range(self.cards_layout.count() - 1):
                    widget = self.cards_layout.itemAt(i).widget()
                    if isinstance(widget, SegmentCard) and widget.segment_id == seg.index:
                        widget.set_active(True)
                        widget.target_edit.setFocus()
                        break
                self.status_bar.showMessage(f"Found at segment {seg.index}")
                return
                
        QMessageBox.information(self, "Not Found", "Text not found in any segment.")

    def _replace_text(self, search_input, replace_input, use_regex, case_sensitive):
        """Replace first occurrence."""
        import re
        
        search_text = search_input.text()
        replace_text = replace_input.text()
        
        if not search_text:
            return
            
        segments = self.project_manager.get_segments()
        pattern_flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            if use_regex:
                pattern = re.compile(search_text, pattern_flags)
            else:
                pattern = re.compile(re.escape(search_text), pattern_flags)
        except re.error as e:
            QMessageBox.warning(self, "Invalid Regex", str(e))
            return
            
        for seg in segments:
            if seg.target_text:
                new_text = pattern.sub(replace_text, seg.target_text)
                if new_text != seg.target_text:
                    seg.target_text = new_text
                    seg.save()
                    self.status_bar.showMessage(f"Replaced in segment {seg.index}")
                    self.load_segments(seg.chapter_id)
                    return
                    
        QMessageBox.information(self, "Not Found", "Text not found.")

    def _replace_all_text(self, search_input, replace_input, use_regex, case_sensitive):
        """Replace all occurrences."""
        import re
        
        search_text = search_input.text()
        replace_text = replace_input.text()
        
        if not search_text:
            return
            
        segments = self.project_manager.get_segments()
        pattern_flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            if use_regex:
                pattern = re.compile(search_text, pattern_flags)
            else:
                pattern = re.compile(re.escape(search_text), pattern_flags)
        except re.error as e:
            QMessageBox.warning(self, "Invalid Regex", str(e))
            return
        
        count = 0
        for seg in segments:
            if seg.target_text:
                new_text = pattern.sub(replace_text, seg.target_text)
                if new_text != seg.target_text:
                    seg.target_text = new_text
                    seg.save()
                    count += 1
        
        self.load_segments()
        QMessageBox.information(self, "Replace Complete", f"Replaced in {count} segments.")

    def show_statistics(self):
        """Show project statistics."""
        if not self.project_manager.current_project:
            QMessageBox.warning(self, "Error", "No active project.")
            return
            
        project = self.project_manager.current_project
        segments = self.project_manager.get_segments()
        
        total_segments = len(segments)
        untranslated = sum(1 for s in segments if not s.target_text or s.status == 'untranslated')
        machine = sum(1 for s in segments if s.status == 'translated')
        ai_refined = sum(1 for s in segments if s.status == 'ai_refined')
        validated = sum(1 for s in segments if s.status == 'validated')
        
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
        
        # Fallback to LLM
        return self.llm_engine



from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QSplitter, 
                             QListWidget, QTextEdit, QLabel, QFileDialog, QDockWidget, QTabWidget, QMenu,
                             QStatusBar, QToolBar, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidgetItem,
                             QScrollArea, QFrame, QGridLayout, QCheckBox)
from src.gui.components import SegmentCard, Sidebar
from src.gui.settings_dialog import SettingsDialog
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
import os
import sys

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.project_manager import ProjectManager
from src.engines import get_engine_instance, list_engines
from src.core.database import Segment, GlossaryTerm

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad - Desktop")
        self.setGeometry(100, 100, 1280, 800)
        
        self.project_manager = ProjectManager()
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
            (Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_G, self.generate_glossary_ai),
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
                break
        
    def apply_theme(self):
        import json
        import os
        
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        theme = "Dark (Default)"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                theme = config.get('theme', 'Dark (Default)')
            except:
                pass
                
        if theme == "Light":
            from src.gui.styles import LIGHT_THEME
            self.setStyleSheet(LIGHT_THEME)
        else:
            from src.gui.styles import DARK_THEME
            self.setStyleSheet(DARK_THEME)
        
    def init_ui(self):
        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Area
        header = QFrame()
        header.setStyleSheet("background-color: #0b0f19; border-bottom: 1px solid #1e293b;")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        # Logo/Title
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(8)
        
        title_label = QLabel("NovelTrad")
        title_label.setObjectName("HeaderLabel")
        
        premium_badge = QLabel("PREMIUM")
        premium_badge.setObjectName("PremiumBadge")
        premium_badge.setFixedSize(65, 20)
        premium_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_layout.addWidget(title_label)
        logo_layout.addWidget(premium_badge)
        header_layout.addWidget(logo_container)
        
        # Project Title
        self.project_label = QLabel()
        self.project_label.setStyleSheet("color: #94a3b8; font-size: 13px; margin-left: 20px;")
        header_layout.addWidget(self.project_label)
            
        header_layout.addStretch()
        
        # Header Actions
        btn_new = QPushButton("+ New Project")
        btn_new.setProperty("primary", True)
        btn_new.clicked.connect(self.new_project_dialog)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_open = QPushButton("Open")
        btn_open.clicked.connect(self.open_project_dialog)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self.show_settings)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_export = QPushButton("Export")
        btn_export.setProperty("primary", True)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        
        export_menu = QMenu(self)
        export_menu.addAction("Export Translated File", self.export_project_dialog)
        export_menu.addSeparator()
        export_menu.addAction("Export TMX Memory", self.export_tmx_dialog)
        export_menu.addAction("Import TMX Memory", self.import_tmx_dialog)
        btn_export.setMenu(export_menu)
        
        btn_batch = QPushButton("Batch Translate")
        btn_batch.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
        btn_batch.clicked.connect(self.batch_translate)
        btn_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_search = QPushButton("Search & Replace")
        btn_search.setStyleSheet("background-color: #1e293b; color: #e2e8f0; border-radius: 4px; padding: 6px 12px;")
        btn_search.clicked.connect(self.show_search_replace)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        
        header_layout.addWidget(btn_new)
        header_layout.addWidget(btn_open)
        header_layout.addWidget(btn_batch)
        header_layout.addWidget(btn_search)
        header_layout.addWidget(btn_settings)
        header_layout.addWidget(btn_export)
        main_layout.addWidget(header)
        
        # 2. Workspace Splitter (Sidebar | Center | Right)
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        
        # A. Left Sidebar (Chapters)
        self.sidebar_container = QFrame()
        self.sidebar_container.setObjectName("SidebarContainer")
        self.sidebar_container.setFixedWidth(260)
        
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.sidebar = Sidebar()
        # Connect signal
        self.sidebar.itemClicked.connect(self.on_chapter_selected)
        sidebar_layout.addWidget(self.sidebar)
        
        # Structure AI Button at the bottom of sidebar
        self.btn_structure = QPushButton("Structure AI")
        self.btn_structure.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_structure.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                margin: 10px 20px;
                padding: 10px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #3b82f6;
            }
        """)
        self.btn_structure.clicked.connect(self.auto_structure_chapters)
        sidebar_layout.addWidget(self.btn_structure)
        
        workspace_layout.addWidget(self.sidebar_container)
        
        # B. Center Content (Scrollable List of Cards)
        center_area = QWidget()
        center_layout = QVBoxLayout(center_area)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(30, 30, 30, 30)
        self.cards_layout.setSpacing(20)
        self.cards_layout.addStretch() # Push items up
        
        self.scroll_area.setWidget(self.cards_container)
        center_layout.addWidget(self.scroll_area)
        
        workspace_layout.addWidget(center_area, stretch=1)
        
        # C. Right Panel (AI / Glossary)
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        right_panel.setFixedWidth(340)
        right_panel.setStyleSheet("background-color: #0f121a; border-left: 1px solid #1e293b;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(20)
        
        # AI Suggestions Box
        ai_box = QFrame()
        ai_box_layout = QVBoxLayout(ai_box)
        ai_box_layout.setContentsMargins(0,0,0,0)
        
        ai_label = QLabel("AI SUGGESTIONS")
        ai_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; letter-spacing: 1px;")
        ai_box_layout.addWidget(ai_label)
        
        self.ai_card = QFrame()
        self.ai_card.setStyleSheet("background-color: #111625; border-radius: 8px; border: 1px solid #1e293b; padding: 15px;")
        self.ai_text = QLabel("Select a segment to see suggestions.")
        self.ai_text.setWordWrap(True)
        self.ai_text.setStyleSheet("color: #e2e8f0; font-family: 'Segoe UI'; font-size: 14px; line-height: 1.4;")
        
        ai_card_layout = QVBoxLayout(self.ai_card)
        ai_card_layout.setContentsMargins(0,0,0,0)
        ai_card_layout.addWidget(self.ai_text)
        
        ai_box_layout.addWidget(self.ai_card)
        
        btn_regen = QPushButton("Regenerate Suggestion")
        btn_regen.setObjectName("RegenButton")
        btn_regen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_regen.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 6px; padding: 10px; font-weight: bold;")
        btn_regen.clicked.connect(self.auto_translate_current)
        ai_box_layout.addWidget(btn_regen)
        
        btn_refine = QPushButton("Editor AI - Refine Translation")
        btn_refine.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refine.setStyleSheet("background-color: #8b5cf6; color: white; border-radius: 6px; padding: 8px; font-weight: bold; margin-top: 5px;")
        btn_refine.clicked.connect(self.editor_ai_refine)
        ai_box_layout.addWidget(btn_refine)
        
        right_layout.addWidget(ai_box)
        
        # Translation Memory Box
        tm_box = QFrame()
        tm_box_layout = QVBoxLayout(tm_box)
        tm_box_layout.setContentsMargins(0,20,0,10)
        
        tm_label = QLabel("TRANSLATION MEMORY")
        tm_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; letter-spacing: 1px;")
        tm_box_layout.addWidget(tm_label)
        
        self.tm_list = QListWidget()
        self.tm_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { background: #111625; border: 1px solid #1e293b; border-radius: 6px; margin-bottom: 6px; padding: 10px; font-size: 11px; color: #cbd5e1; }
            QListWidget::item:hover { border: 1px solid #3b82f6; }
        """)
        tm_box_layout.addWidget(self.tm_list)
        right_layout.addWidget(tm_box)
        
        # Dictionary Search Box
        dict_box = QFrame()
        dict_box_layout = QVBoxLayout(dict_box)
        dict_box_layout.setContentsMargins(0,0,0,0)
        
        dict_header = QHBoxLayout()
        dict_label = QLabel("DICTIONARY")
        dict_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; letter-spacing: 1px;")
        dict_header.addWidget(dict_label)
        dict_header.addStretch()
        
        dict_box_layout.addLayout(dict_header)
        
        # Search input
        self.dict_search = QLineEdit()
        self.dict_search.setPlaceholderText("Search dictionary...")
        self.dict_search.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 8px;
                color: #e2e8f0;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.dict_search.returnPressed.connect(self.search_dictionary)
        dict_box_layout.addWidget(self.dict_search)
        
        # Language selector
        lang_container = QWidget()
        lang_layout = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        
        self.dict_src_lang = QComboBox()
        self.dict_src_lang.addItems(['en', 'fr', 'zh', 'ja', 'de', 'ko', 'es', 'it', 'pt', 'ru', 'vi', 'th', 'ar'])
        self.dict_src_lang.setCurrentText('en')
        self.dict_src_lang.setStyleSheet("background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 4px;")
        
        swap_dict_btn = QPushButton("⇄")
        swap_dict_btn.setFixedSize(24, 24)
        swap_dict_btn.setStyleSheet("background: transparent; color: #3b82f6; font-weight: bold;")
        def swap_dict_langs():
            src = self.dict_src_lang.currentText()
            tgt = self.dict_tgt_lang.currentText()
            self.dict_src_lang.setCurrentText(tgt)
            self.dict_tgt_lang.setCurrentText(src)
        swap_dict_btn.clicked.connect(swap_dict_langs)

        self.dict_tgt_lang = QComboBox()
        self.dict_tgt_lang.addItems(['fr', 'en', 'zh', 'ja', 'de', 'es', 'it', 'pt', 'ru', 'vi', 'th', 'ar'])
        self.dict_tgt_lang.setCurrentText('fr')
        self.dict_tgt_lang.setStyleSheet("background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 4px;")
        
        lang_layout.addWidget(self.dict_src_lang)
        lang_layout.addWidget(swap_dict_btn)
        lang_layout.addWidget(self.dict_tgt_lang)
        lang_layout.addStretch()
        dict_box_layout.addWidget(lang_container)
        
        # Results list
        self.dict_results = QListWidget()
        self.dict_results.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { background: #111625; border: 1px solid #1e293b; border-radius: 6px; margin-bottom: 6px; padding: 8px; }
        """)
        dict_box_layout.addWidget(self.dict_results)
        
        # Import dictionary button
        btn_import_dict = QPushButton("Import Dictionary")
        btn_import_dict.setStyleSheet("background-color: #1e293b; color: #94a3b8; border-radius: 4px; padding: 6px;")
        btn_import_dict.clicked.connect(self.import_dictionary)
        dict_box_layout.addWidget(btn_import_dict)
        
        right_layout.addWidget(dict_box)
        
        # Glossary Box
        gloss_box = QFrame()
        gloss_box_layout = QVBoxLayout(gloss_box)
        gloss_box_layout.setContentsMargins(0,0,0,0)
        
        gloss_header = QHBoxLayout()
        gloss_label = QLabel("GLOSSARY MATCHES")
        gloss_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; letter-spacing: 1px;")
        gloss_header.addWidget(gloss_label)
        gloss_header.addStretch()
        
        btn_add_term = QPushButton("+")
        btn_add_term.setFixedSize(24, 24)
        btn_add_term.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_term.setStyleSheet("background: #1e293b; color: #3b82f6; border-radius: 4px;")
        btn_add_term.clicked.connect(self.add_glossary_term)
        gloss_header.addWidget(btn_add_term)
        
        gloss_box_layout.addLayout(gloss_header)
        
        self.glossary_list = QListWidget()
        self.glossary_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { background: #111625; border: 1px solid #1e293b; border-radius: 6px; margin-bottom: 8px; padding: 10px; }
            QListWidget::item:hover { border: 1px solid #3b82f6; }
        """)
        gloss_box_layout.addWidget(self.glossary_list)
        
        # Glossary AI Button
        btn_glossary_scan = QPushButton("Scan Chapter for Terms")
        btn_glossary_scan.setObjectName("RegenButton")
        btn_glossary_scan.setToolTip("Use AI to detect character names, items and locations in this chapter")
        btn_glossary_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_glossary_scan.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 6px; padding: 8px; font-weight: bold; margin-top: 10px;")
        btn_glossary_scan.clicked.connect(self.scan_chapter_glossary)
        gloss_box_layout.addWidget(btn_glossary_scan)
        
        right_layout.addWidget(gloss_box)
        right_layout.addStretch()
        
        workspace_layout.addWidget(right_panel)
        main_layout.addLayout(workspace_layout)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background: #0b0f19; color: #64748b; border-top: 1px solid #1e293b;")
        self.setStatusBar(self.status_bar)

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
             self.project_label.setText("")
             return
             
        self.project_label.setText(f"Project: {self.project_manager.current_project.name}")
        
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

    def on_segment_card_clicked(self, segment_id):
        self.current_segment_index = segment_id
        
        for i in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, SegmentCard):
                widget.set_active(widget.segment_id == segment_id)
                
        self.status_bar.showMessage(f"Selected Segment {segment_id}")
        self.ai_text.setText("Click 'Regenerate' to get AI suggestion for this segment.\n(Model: Gemma-2B)")

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
            trans = self.llm_engine.translate(src, p.source_language, p.target_language)
            
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
                glossary_terms=glossary_terms
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

    def search_dictionary(self):
        """Search the dictionary for the entered query"""
        from src.core.dictionary_manager import DictionaryManager
        
        query = self.dict_search.text().strip()
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
            
        if not self.llm_engine or not self.llm_engine.is_available():
            QMessageBox.warning(self, "Error", "LLM engine not available. Please configure in Settings.")
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
            
            translated_count = 0
            
            for i, seg in enumerate(untranslated):
                # Update progress
                progress = int((i / total) * 100)
                self.status_bar.showMessage(f"Translating segment {i+1}/{total} ({progress}%)")
                QApplication.processEvents()
                
                try:
                    # Translate
                    translation = self.llm_engine.translate(
                        seg.source_text,
                        project.source_language,
                        project.target_language,
                        glossary_terms=glossary_terms,
                        genre=project.genre,
                        custom_instructions=project.custom_instructions
                    )
                    
                    # Save
                    seg.target_text = translation
                    seg.status = 'translated'
                    seg.save()
                    translated_count += 1
                    
                except Exception as e:
                    print(f"Error translating segment {seg.index}: {e}")
                    
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
        dialog = SettingsDialog(self)
        dialog.exec()

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

    def open_project_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "NovelTrad Projects (*.ntrad)")
        if fname:
            try:
                self.project_manager.load_project(fname)
                self.load_chapters()
                self.load_segments()
                self.status_bar.showMessage(f"Loaded project: {fname}")
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



from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QSplitter, 
                             QListWidget, QTextEdit, QLabel, QFileDialog, QDockWidget, QTabWidget, QMenu,
                             QStatusBar, QToolBar, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidgetItem,
                             QScrollArea, QFrame)
from src.gui.components import SegmentCard, Sidebar
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
import os
import sys

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.project_manager import ProjectManager
from src.engines.llm_engine import LLMEngine
from src.core.database import Segment, GlossaryTerm

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad - Desktop")
        self.setGeometry(100, 100, 1280, 800)
        
        self.project_manager = ProjectManager()
        self.llm_engine = LLMEngine() 
        self.current_segment_index = -1
        
        # Apply Styles
        from src.gui.styles import DARK_THEME
        self.setStyleSheet(DARK_THEME)
        
        self.init_ui()
        
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
        title_label = QLabel("NovelTrad <span>PREMIUM</span>")
        title_label.setObjectName("HeaderLabel")
        header_layout.addWidget(title_label)
        
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
        
        header_layout.addWidget(btn_new)
        header_layout.addWidget(btn_open)
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
        # Mock Data matching screenshot
        self.sidebar.add_item("Chapter 1: The Descent", 100)
        self.sidebar.add_item("Chapter 2: Obsidian Gate", 45, active=True)
        self.sidebar.add_item("Chapter 3: Silent Echoes", 0)
        self.sidebar.add_item("Chapter 4: The Ritual", 0)
        
        sidebar_layout.addWidget(self.sidebar)
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
        
        right_layout.addWidget(ai_box)
        
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
        
        right_layout.addWidget(gloss_box)
        right_layout.addStretch()
        
        workspace_layout.addWidget(right_panel)
        main_layout.addLayout(workspace_layout)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background: #0b0f19; color: #64748b; border-top: 1px solid #1e293b;")
        self.setStatusBar(self.status_bar)

    def load_segments(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.project_manager.current_project:
             self.project_label.setText("")
             return
             
        self.project_label.setText(f"Project: {self.project_manager.current_project.name}")
             
        segments = self.project_manager.get_segments()
        for seg in segments[:50]: 
            card = SegmentCard(seg)
            card.clicked.connect(self.on_segment_card_clicked)
            self.cards_layout.insertWidget(self.cards_layout.count()-1, card)
            
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
           
    def glossary_context_menu(self, pos):
        pass

    def new_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        layout = QFormLayout(dialog)
        name_input = QLineEdit()
        file_input = QPushButton("Select File...")
        self.selected_file = None
        
        def select_file():
            fname, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Supported Files (*.epub *.docx *.txt)")
            if fname:
                self.selected_file = fname
                file_input.setText(os.path.basename(fname))
        
        file_input.clicked.connect(select_file)
        layout.addRow("Project Name:", name_input)
        layout.addRow("Source File:", file_input)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Create")
        ok_btn.clicked.connect(dialog.accept)
        buttons.addWidget(ok_btn)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not name_input.text() or not self.selected_file:
                QMessageBox.warning(self, "Error", "Please fill all fields")
                return
            self.create_project(name_input.text(), self.selected_file)

    def create_project(self, name, source_file):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            projects_dir = os.path.join(base_dir, "projects")
            os.makedirs(projects_dir, exist_ok=True)
            db_path = os.path.join(projects_dir, f"{name}.ntrad")
            
            if os.path.exists(db_path):
                QMessageBox.warning(self, "Error", "Project already exists!")
                return

            self.project_manager.create_project(name, db_path, source_file)
            self.load_segments()
            self.status_bar.showMessage(f"Project '{name}' created successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_project_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "NovelTrad Projects (*.ntrad)")
        if fname:
            try:
                self.project_manager.load_project(fname)
                self.load_segments()
                self.status_bar.showMessage(f"Loaded project: {fname}")
            except Exception as e:
                 QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")

from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QStackedWidget,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QSize

class ToolsPanel(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("RightPanel")
        self.setFixedWidth(300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tools Header (Tabs Simulation)
        tools_header = QFrame()
        tools_header.setObjectName("ToolsHeader")
        tools_header_layout = QHBoxLayout(tools_header)
        tools_header_layout.setContentsMargins(12, 12, 12, 12)
        
        tools_title = QLabel("OUTILS")
        tools_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 1px;")
        tools_header_layout.addWidget(tools_title)
        tools_header_layout.addStretch()
        
        self.btn_chat = QPushButton()
        self.btn_chat.setIcon(self.main_window.colorize_icon("forum", "#0d7ff2"))
        self.btn_chat.setToolTip("Ouvrir le Chat IA")
        self.btn_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chat.clicked.connect(self.main_window.ai_ctrl.show_chat)
        tools_header_layout.addWidget(self.btn_chat)
        
        layout.addWidget(tools_header)
        
        # Stacked Widget for Chat vs Tools
        self.stack = QStackedWidget()
        
        # Tools Container (Scrollable)
        tools_container = QWidget()
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(12, 0, 12, 12)
        tools_layout.setSpacing(20)
        
        # 1. Dictionary
        dict_box = self.create_tool_box("DICTIONNAIRE", "search")
        self.main_window.dict_input = QLineEdit()
        self.main_window.dict_input.setPlaceholderText("Rechercher un mot...")
        self.main_window.dict_input.returnPressed.connect(self.main_window.tools_ctrl.search_dictionary)
        self.main_window.dict_results = QLabel("Résultats s'afficheront ici.")
        self.main_window.dict_results.setWordWrap(True)
        self.main_window.dict_results.setStyleSheet("color: #94a3b8; font-size: 11px;")
        dict_box.layout().addWidget(self.main_window.dict_input)
        dict_box.layout().addWidget(self.main_window.dict_results)
        tools_layout.addWidget(dict_box)
        
        # 2. Glossary
        gloss_box = self.create_tool_box("GLOSSAIRE DU SEGMENT", "menu_book")
        self.main_window.glossary_list = QListWidget()
        self.main_window.glossary_list.setFixedHeight(120)
        gloss_box.layout().addWidget(self.main_window.glossary_list)
        tools_layout.addWidget(gloss_box)
        
        # 3. Fuzzy Matches (TM)
        fuzzy_box = self.create_tool_box("MÉMOIRE DE TRADUCTION", "history")
        from src.gui.fuzzy_match_viewer import FuzzyMatchViewer
        self.main_window.fuzzy_viewer = FuzzyMatchViewer()
        self.main_window.fuzzy_viewer.applyMatch.connect(self.main_window.editor_ctrl.apply_translation_match)
        fuzzy_box.layout().addWidget(self.main_window.fuzzy_viewer)
        tools_layout.addWidget(fuzzy_box)
        
        # 4. AI Suggestion
        ai_box = self.create_tool_box("SUGGESTION IA", "auto_awesome")
        self.main_window.ai_text = QLabel("Cliquez sur 'Régénérer' pour obtenir une traduction IA.")
        self.main_window.ai_text.setWordWrap(True)
        self.main_window.ai_text.setStyleSheet("color: #e2e8f0; font-size: 12px; font-style: italic;")
        self.btn_regenerate = QPushButton("Régénérer Suggestion")
        self.btn_regenerate.setObjectName("PrimaryButton")
        self.btn_regenerate.clicked.connect(self.main_window.editor_ctrl.auto_translate_current)
        ai_box.layout().addWidget(self.main_window.ai_text)
        ai_box.layout().addWidget(self.btn_regenerate)
        tools_layout.addWidget(ai_box)
        
        # 5. Concordancier
        conc_box = self.create_tool_box("CONCORDANCIER", "find_in_page")
        self.main_window.conc_input = QLineEdit()
        self.main_window.conc_input.setPlaceholderText("Rechercher dans tout le projet...")
        self.main_window.conc_input.returnPressed.connect(self.main_window.tools_ctrl.search_concordancer)
        self.main_window.conc_results = QListWidget()
        self.main_window.conc_results.setFixedHeight(120)
        conc_box.layout().addWidget(self.main_window.conc_input)
        conc_box.layout().addWidget(self.main_window.conc_results)
        tools_layout.addWidget(conc_box)
        
        tools_layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tools_container)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.stack.addWidget(scroll)
        layout.addWidget(self.stack)

    def create_tool_box(self, title, icon_name):
        box = QFrame()
        box.setObjectName("ToolBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.main_window.colorize_icon(icon_name, "#0d7ff2").pixmap(14, 14))
        label = QLabel(title)
        label.setStyleSheet("font-size: 9px; font-weight: 800; color: #0d7ff2; letter-spacing: 0.5px;")
        header_layout.addWidget(icon)
        header_layout.addWidget(label)
        header_layout.addStretch()
        
        box_layout.addLayout(header_layout)
        return box

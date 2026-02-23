from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QSize

class HeaderPanel(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("Header")
        self.setFixedHeight(56)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        # Logo & Premium Badge
        logo_icon = QLabel()
        logo_icon.setFixedSize(32, 32)
        logo_icon.setPixmap(self.main_window.colorize_icon("menu_book", "#ffffff").pixmap(24, 24))
        logo_icon.setStyleSheet("background-color: #0d7ff2; border-radius: 4px;")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_container = QVBoxLayout()
        title_container.setSpacing(0)
        title_container.setContentsMargins(0, 0, 0, 0)
        
        main_title = QLabel("NovelTrad")
        main_title.setStyleSheet("font-size: 15px; font-weight: 800; color: white;") 
        
        premium_label = QLabel("PREMIUM")
        premium_label.setStyleSheet("color: #0d7ff2; font-size: 8px; font-weight: 700; letter-spacing: 1px;")
        
        title_container.addWidget(main_title)
        title_container.addWidget(premium_label)
        
        layout.addWidget(logo_icon)
        layout.addLayout(title_container)
        
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(24)
        sep1.setStyleSheet("background-color: #333333;")
        layout.addWidget(sep1)
        
        layout.addStretch()
        
        # Project Info
        project_info = QHBoxLayout()
        project_info.setSpacing(8)
        project_label = QLabel("Projet :")
        project_label.setObjectName("ProjectTitle")
        self.project_name_label = QLabel("Aucun Projet Chargé")
        self.project_name_label.setObjectName("ProjectName")
        project_info.addWidget(project_label)
        project_info.addWidget(self.project_name_label)
        layout.addLayout(project_info)
        
        layout.addStretch()
        
        # Actions
        self.btn_undo = self.create_header_btn("undo", "Annuler (Ctrl+Z)", self.main_window.editor_ctrl.undo)
        self.btn_redo = self.create_header_btn("redo", "Rétablir (Ctrl+Y)", self.main_window.editor_ctrl.redo)
        self.btn_save = self.create_header_btn("save", "Valider et Sauvegarder Segment (Ctrl+S)", self.main_window.editor_ctrl.save_active_segment)
        
        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_redo)
        layout.addWidget(self.btn_save)

    def create_header_btn(self, icon_name, tooltip, callback):
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setIcon(self.main_window.colorize_icon(icon_name, "#ffffff"))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn
        
    def set_project_name(self, name):
        self.project_name_label.setText(name if name else "Aucun Projet Chargé")

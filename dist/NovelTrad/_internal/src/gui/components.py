from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QWidget, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

class SegmentCard(QFrame):
    clicked = pyqtSignal(int)      # Signal to notify selection
    textChanged = pyqtSignal(int, str) # Signal to auto-save

    def __init__(self, segment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.segment_id = segment.index
        self.is_active = False
        
        # Style
        self.setObjectName("SegmentCard")
        self.setProperty("status", segment.status or "draft")  # draft, translated, translating
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header Row (ID and Status)
        header_layout = QHBoxLayout()
        
        id_badge = QLabel(f"{self.segment_id:03d}")
        id_badge.setObjectName("IdBadge")
        id_badge.setFixedWidth(40)
        id_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_label = QLabel(self.segment.status.upper() if self.segment.status else "DRAFT")
        status_label.setObjectName("StatusLabel")
        
        header_layout.addWidget(id_badge)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        
        main_layout.addLayout(header_layout)
        
        # Content Row (Source | Target)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Source Text
        self.source_edit = QTextEdit(self.segment.source_text)
        self.source_edit.setReadOnly(True)
        self.source_edit.setObjectName("SourceText")
        self.source_edit.setFrameShape(QFrame.Shape.NoFrame)
        # Auto-height logic needed, but for now fixed min
        self.source_edit.setMinimumHeight(80)
        self.source_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Target Text
        self.target_edit = QTextEdit(self.segment.target_text or "")
        self.target_edit.setPlaceholderText("Click to start translating...")
        self.target_edit.setObjectName("TargetText")
        self.target_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.target_edit.setMinimumHeight(80)
        self.target_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.target_edit.textChanged.connect(self.on_text_changed)
        
        # Add focus event filter to detect activation? 
        # Easier: click event on frame -> active.
        
        content_layout.addWidget(self.source_edit)
        content_layout.addWidget(self.target_edit)
        
        main_layout.addLayout(content_layout)
        
        # Footer (Actions) - Visible only on hover/active ideally
        # For now, keep it simpler to match screenshot which has bottom bar on active card
        self.footer = QFrame()
        self.footer.setObjectName("CardFooter")
        self.footer.setVisible(False)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        words_label = QLabel(f"Words: {len(self.segment.source_text.split())}")
        words_label.setStyleSheet("color: #64748b; font-size: 11px;")
        
        confirm_label = QLabel("Press Ctrl+Enter to confirm")
        confirm_label.setStyleSheet("color: #3b82f6; font-size: 11px; font-weight: bold;")
        
        footer_layout.addWidget(words_label)
        footer_layout.addStretch()
        footer_layout.addWidget(confirm_label)
        
        main_layout.addWidget(self.footer)
        
        # Click handling
        self.mousePressEvent = self.on_click
        self.source_edit.mousePressEvent = self.on_click
        self.target_edit.mousePressEvent = self.on_click

    def on_click(self, event):
        self.clicked.emit(self.segment_id)
        # Forward event to child if needed
        if hasattr(super(), 'mousePressEvent'):
            super().mousePressEvent(event)
            
        # If clicked on editor, focus it
        if isinstance(self.sender(), QTextEdit):
            self.sender().setFocus()

    def set_active(self, active):
        self.is_active = active
        self.setProperty("active", active)
        self.footer.setVisible(active)
        
        # Refresh style
        self.style().unpolish(self)
        self.style().polish(self)
        
        if active:
            self.target_edit.setFocus()

    def on_text_changed(self):
        self.textChanged.emit(self.segment_id, self.target_edit.toPlainText())

class SidebarItem(QFrame):
    clicked = pyqtSignal(str) # Emits item ID/Name

    def __init__(self, title, progress=0, is_active=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_active = is_active
        self.setObjectName("SidebarItem")
        self.setProperty("active", is_active)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        
        # Title Row
        title_row = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #e2e8f0; font-weight: 500;")
        title_row.addWidget(self.title_lbl)
        
        if progress > 0:
            prog_lbl = QLabel(f"{progress}%")
            prog_lbl.setStyleSheet("color: #3b82f6; font-size: 11px; font-weight: bold;")
            title_row.addWidget(prog_lbl)
            
        layout.addLayout(title_row)
        
        # Progress Bar line (visual indicator)
        if is_active:
             line = QFrame()
             line.setFixedHeight(2)
             line.setStyleSheet("background-color: #3b82f6; border-radius: 1px;")
             layout.addWidget(line)
             
    def mousePressEvent(self, event):
        self.clicked.emit(self.title)
        
    def set_active(self, active):
        self.is_active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Rebuild layout to show/hide line? Or simpler: Just change background/border
        # For now relying on QSS property "active"

class Sidebar(QWidget):
    itemClicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 0)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header "CHAPTERS"
        header = QHBoxLayout()
        header.setContentsMargins(20, 0, 20, 10)
        lbl = QLabel("CHAPTERS")
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        header.addWidget(lbl)
        header.addStretch()
        btn_add = QPushButton("+")
        btn_add.setFixedSize(20, 20)
        btn_add.setStyleSheet("background: transparent; color: #3b82f6; border: none; font-weight: bold;")
        header.addWidget(btn_add)
        self.layout.addLayout(header)
        
        self.items = []
        
    def add_item(self, title, progress=0, active=False):
        item = SidebarItem(title, progress, active)
        item.clicked.connect(self.on_item_clicked)
        self.layout.addWidget(item)
        self.items.append(item)
        
    def on_item_clicked(self, title):
        for item in self.items:
            item.set_active(item.title == title)
        self.itemClicked.emit(title)


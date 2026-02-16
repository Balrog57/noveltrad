from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
import os

class SegmentCard(QFrame):
    clicked = pyqtSignal(int)      # Signal to notify selection
    textChanged = pyqtSignal(int, str) # Signal to auto-save
    lookupWord = pyqtSignal(str)   # Signal to lookup word in dictionary

    def __init__(self, segment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.segment_id = segment.index
        self.is_active = False
        
        # Style
        self.setObjectName("SegmentCard")
        self.setProperty("active", False)
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        
        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        id_label = QLabel(f"SEGMENT #{self.segment_id}")
        id_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 1px;")
        
        self.status_badge = QLabel(self.segment.status.upper() if self.segment.status else "UNTRANSLATED")
        status_color = self.get_status_color(self.segment.status)
        self.status_badge.setStyleSheet(f"font-size: 9px; font-weight: 800; color: {status_color}; padding: 2px 6px; border: 1px solid {status_color}; border-radius: 4px;")
        
        header_layout.addWidget(id_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)
        
        # Text areas (50/50 Split)
        text_layout = QHBoxLayout()
        text_layout.setSpacing(0) # No spacing, use border-r
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # Source (Left)
        source_container = QFrame()
        source_container.setObjectName("SourceContainer")
        source_container.setStyleSheet("border-r: 1px solid #333333; padding: 12px;")
        source_layout = QVBoxLayout(source_container)
        
        self.source_edit = QTextEdit(self.segment.source_text)
        self.source_edit.setObjectName("SourceText")
        self.source_edit.setReadOnly(True)
        self.source_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.source_edit.installEventFilter(self)
        source_layout.addWidget(self.source_edit)
        
        # Target (Right)
        target_container = QFrame()
        target_container.setObjectName("TargetContainer")
        target_container.setStyleSheet("padding: 12px;")
        target_layout = QVBoxLayout(target_container)
        
        self.target_edit = QTextEdit(self.segment.target_text or "")
        self.target_edit.setObjectName("TargetText")
        self.target_edit.setPlaceholderText("Click to start translating...")
        self.target_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.target_edit.textChanged.connect(self.on_text_changed)
        self.target_edit.installEventFilter(self)
        target_layout.addWidget(self.target_edit)
        
        text_layout.addWidget(source_container, 1)
        text_layout.addWidget(target_container, 1)
        main_layout.addLayout(text_layout)
        
        # Footer Action (Visible only when active)
        self.footer = QFrame()
        self.footer.setFixedHeight(24)
        self.footer.setVisible(False)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        words_count = len(self.segment.source_text.split())
        words_info = QLabel(f"{words_count} words")
        words_info.setStyleSheet("color: #64748b; font-size: 10px;")
        
        help_text = QLabel("Press Ctrl+Enter to confirm and save")
        help_text.setStyleSheet("color: #0d7ff2; font-size: 10px; font-weight: 600;")
        
        footer_layout.addWidget(words_info)
        footer_layout.addStretch()
        footer_layout.addWidget(help_text)
        main_layout.addWidget(self.footer)

    def get_status_color(self, status):
        colors = {
            'translated': '#3b82f6',
            'ai_refined': '#8b5cf6',
            'validated': '#22c55e',
            'machine': '#f59e0b'
        }
        return colors.get(status, '#ef4444')

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            self.clicked.emit(self.segment_id)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        self.clicked.emit(self.segment_id)
        super().mousePressEvent(event)

    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        self.setProperty("active", active)
        self.footer.setVisible(active)
        
        # Trigger style refresh
        self.style().unpolish(self)
        self.style().polish(self)
        
        if active:
            self.target_edit.setFocus()

    def on_text_changed(self):
        self.textChanged.emit(self.segment_id, self.target_edit.toPlainText())

class SidebarItem(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, item_id, title, progress=0, is_active=False, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.title = title
        self.is_active = is_active
        self.progress = progress
        
        self.setProperty("active", is_active)
        self.setFixedHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_row = QHBoxLayout()
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        
        self.prog_pct = QLabel(f"{self.progress}%")
        self.prog_pct.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b;")
        
        title_row.addWidget(self.title_lbl)
        title_row.addStretch()
        title_row.addWidget(self.prog_pct)
        layout.addLayout(title_row)
        
        # Progress Bar
        self.bar_bg = QFrame()
        self.bar_bg.setFixedHeight(4)
        self.bar_bg.setStyleSheet("background-color: #1e1e1e; border-radius: 2px;")
        
        self.bar_fill = QFrame(self.bar_bg)
        self.bar_fill.setFixedHeight(4)
        fill_color = "#22c55e" if self.progress == 100 else "#0d7ff2"
        self.bar_fill.setStyleSheet(f"background-color: {fill_color}; border-radius: 2px;")
        
        layout.addWidget(self.bar_bg)
        self.update_progress(self.progress)

    def update_progress(self, progress):
        self.progress = progress
        self.prog_pct.setText(f"{progress}%")
        # In a real layout, we'd use a resize event or layout stretch
        # For simplicity in this demo component:
        width = int((progress / 100.0) * 228) # Approximate width
        # Better: use a layout or paintEvent for the bar
        self.bar_fill.setFixedWidth(max(0, width))

    def mousePressEvent(self, event):
        self.clicked.emit(self.item_id)
        
    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        
        title_color = "#ffffff" if active else "#cbd5e1"
        self.title_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {title_color};")

class Sidebar(QWidget):
    itemClicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.items = []
        
    def add_item(self, item_id, title, progress=0, active=False):
        item = SidebarItem(item_id, title, progress, active)
        item.clicked.connect(self.on_item_clicked)
        self.layout.addWidget(item)
        self.items.append(item)
        
    def clear(self):
        for item in self.items:
            self.layout.removeWidget(item)
            item.deleteLater()
        self.items = []
        
    def on_item_clicked(self, item_id):
        for item in self.items:
            item.set_active(item.item_id == item_id)
        self.itemClicked.emit(item_id)


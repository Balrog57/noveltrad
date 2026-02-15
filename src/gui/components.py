from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QWidget, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor

class SegmentCard(QFrame):
    clicked = pyqtSignal(int)      # Signal to notify selection
    textChanged = pyqtSignal(int, str) # Signal to auto-save
    lookupWord = pyqtSignal(str)   # Signal to lookup word in dictionary

class SegmentCard(QFrame):
    clicked = pyqtSignal(int)      # Signal to notify selection
    textChanged = pyqtSignal(int, str) # Signal to auto-save

    STATUS_COLORS = {
        'untranslated': {'border': '#ef4444', 'badge': '#ef4444', 'label': 'UNTRANSLATED'},
        'machine': {'border': '#f97316', 'badge': '#f97316', 'label': 'MACHINE'},
        'translated': {'border': '#3b82f6', 'badge': '#3b82f6', 'label': 'TRANSLATED'},
        'ai_refined': {'border': '#8b5cf6', 'badge': '#8b5cf6', 'label': 'AI REFINED'},
        'validated': {'border': '#22c55e', 'badge': '#22c55e', 'label': 'VALIDATED'},
    }

    def __init__(self, segment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.segment_id = segment.index
        self.is_active = False
        
        # Determine status for styling
        status = segment.status or 'untranslated'
        self.setProperty("segment_status", status)
        
        # Style
        self.setObjectName("SegmentCard")
        self.setProperty("status", status)
        
        self.init_ui()
        
    def init_ui(self):
        status = self.segment.status or 'untranslated'
        colors = self.STATUS_COLORS.get(status, self.STATUS_COLORS['untranslated'])
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header Row (ID and Status)
        header_layout = QHBoxLayout()
        
        id_badge = QLabel(f"{self.segment_id:03d}")
        id_badge.setObjectName("IdBadge")
        id_badge.setFixedWidth(40)
        id_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_label = QLabel(colors['label'])
        status_label.setObjectName("StatusLabel")
        status_label.setStyleSheet(f"color: {colors['badge']}; font-weight: bold;")
        
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
        self.source_edit.setMinimumHeight(80)
        self.source_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.source_edit.installEventFilter(self)
        
        # Target Text
        self.target_edit = QTextEdit(self.segment.target_text or "")
        self.target_edit.setPlaceholderText("Click to start translating...")
        self.target_edit.setObjectName("TargetText")
        self.target_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.target_edit.setMinimumHeight(80)
        self.target_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.target_edit.textChanged.connect(self.on_text_changed)
        self.target_edit.installEventFilter(self)
        
        content_layout.addWidget(self.source_edit)
        content_layout.addWidget(self.target_edit)
        
        main_layout.addLayout(content_layout)
        
        # Footer (Actions)
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
        
        # Apply dynamic styling based on status
        self.setStyleSheet(f"""
            #SegmentCard {{
                background-color: #111625;
                border-radius: 8px;
                border-left: 4px solid {colors['border']};
            }}
            #SegmentCard[segment_status="untranslated"] {{
                border-left: 4px solid #ef4444;
            }}
            #SegmentCard[segment_status="machine"] {{
                border-left: 4px solid #f97316;
            }}
            #SegmentCard[segment_status="translated"] {{
                border-left: 4px solid #3b82f6;
            }}
            #SegmentCard[segment_status="ai_refined"] {{
                border-left: 4px solid #8b5cf6;
            }}
            #SegmentCard[segment_status="validated"] {{
                border-left: 4px solid #22c55e;
            }}
            #SegmentCard[active="true"] {{
                background-color: #1e293b;
                border: 1px solid #3b82f6;
            }}
        """)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            self.clicked.emit(self.segment_id)
        
        if event.type() == event.Type.MouseMove and obj == self.source_edit:
            cursor = self.source_edit.cursorForPosition(event.pos())
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText().strip()
            if word and len(word) > 1:
                self.lookupWord.emit(word)
        
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        self.clicked.emit(self.segment_id)
        super().mousePressEvent(event)

    def set_active(self, active):
        if self.is_active == active: return
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
    clicked = pyqtSignal(int) # Emits item ID

    def __init__(self, item_id, title, progress=0, is_active=False, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.title = title
        self.is_active = is_active
        self.setObjectName("SidebarItem")
        self.setProperty("active", is_active)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        # Title Row
        title_row = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("SidebarTitle")
        self.title_lbl.setStyleSheet("border: none; background: transparent;") # Reset potential inheritance
        title_row.addWidget(self.title_lbl)
        
        if progress > 0 or is_active:
             # Show percentage if progress > 0 or if active (even if 0%)
            prog_text = f"{progress}%"
            prog_lbl = QLabel(prog_text)
            prog_lbl.setObjectName("SidebarProgress")
            prog_lbl.setStyleSheet("border: none; background: transparent;")
            title_row.addWidget(prog_lbl)
            
        layout.addLayout(title_row)
        
        # Progress Bar Container
        # HTML: <div class="w-full bg-border-dark h-1 rounded-full"><div class="bg-green-500..." /></div>
        prog_container = QFrame()
        prog_container.setFixedHeight(4)
        prog_container.setStyleSheet("background-color: #333333; border-radius: 2px; border: none;")
        prog_layout = QHBoxLayout(prog_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(0)
        
        # Fill
        if progress > 0:
            fill = QFrame()
            # If 100%, green, else primary blue
            color = "#22c55e" if progress == 100 else "#0d7ff2"
            fill.setStyleSheet(f"background-color: {color}; border-radius: 2px; border: none;")
            
            # Use stretch factors to simulate width percentage
            prog_layout.addWidget(fill, progress)
            prog_layout.addStretch(100 - progress)
        else:
            prog_layout.addStretch(1)

        layout.addWidget(prog_container)

    def mousePressEvent(self, event):
        self.clicked.emit(self.item_id)
        
    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        if hasattr(self, 'title_lbl'):
             self.title_lbl.style().unpolish(self.title_lbl)
             self.title_lbl.style().polish(self.title_lbl)

class Sidebar(QWidget):
    itemClicked = pyqtSignal(int)
    
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


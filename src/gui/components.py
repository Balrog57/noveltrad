from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QWidget, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction
from src.utils.tag_utils import validate_tags
from src.core.grammar_checker import GrammarChecker
import os

class SegmentCard(QFrame):
    clicked = pyqtSignal(int)      # Signal to notify selection
    textChanged = pyqtSignal(int, str) # Signal to auto-save
    lookupWord = pyqtSignal(str)   # Signal to lookup word in dictionary
    forceTranslation = pyqtSignal(int) # Signal to execute Enforce TM
    machineTranslation = pyqtSignal(int) # Signal to execute MT suggestions

    def __init__(self, segment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.segment_id = segment.id if getattr(segment, 'id', None) is not None else segment.index
        self.segment_index = getattr(segment, 'index', self.segment_id)
        self.is_active = False
        
        # Style
        self.setObjectName("SegmentCard")
        self.setProperty("active", False)
        self.layout_mode = "horizontal"  # horizontal (side-by-side) or vertical (stacked)
        
        # Grammar Check Logic
        self.grammar_checker = GrammarChecker()
        self.grammar_enabled = True
        self.grammar_timer = QTimer(self)
        self.grammar_timer.setSingleShot(True)
        self.grammar_timer.timeout.connect(self.check_grammar_realtime)
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        
        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        display_index = self.segment_index + 1 if isinstance(self.segment_index, int) else self.segment_id
        id_label = QLabel(f"SEGMENT #{display_index}")
        id_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 1px;")
        
        status = self.segment.get_status()
        self.status_badge = QLabel(status.get_label().upper())
        status_color = status.get_color().name()
        self.status_badge.setStyleSheet(f"font-size: 9px; font-weight: 800; color: {status_color}; padding: 2px 6px; border: 1px solid {status_color}; border-radius: 4px;")
        
        header_layout.addWidget(id_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)
        
        # Tag Warning Label
        self.tag_warning_label = QLabel()
        self.tag_warning_label.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 600; background-color: #450a0a; border: 1px solid #991b1b; border-radius: 4px; padding: 4px 8px;")
        self.tag_warning_label.setWordWrap(True)
        self.tag_warning_label.setVisible(False)
        main_layout.addWidget(self.tag_warning_label)
        
        # Grammar Warning Label
        self.grammar_warning_label = QLabel()
        self.grammar_warning_label.setStyleSheet("color: #3b82f6; font-size: 10px; font-weight: 600; background-color: #1e1b4b; border: 1px solid #1e3a8a; border-radius: 4px; padding: 4px 8px;")
        self.grammar_warning_label.setWordWrap(True)
        self.grammar_warning_label.setVisible(False)
        main_layout.addWidget(self.grammar_warning_label)
        
        # Text areas
        self.text_layout_container = QFrame()
        self.text_layout_container.setLayout(QVBoxLayout())
        self.text_layout_container.layout().setContentsMargins(0, 0, 0, 0)
        self.text_layout_container.layout().setSpacing(0)
        
        self._setup_text_areas()
        self._apply_layout_mode()
        
        main_layout.addWidget(self.text_layout_container)
        
        # Apply Status Color Border
        self.update_status_style()
        
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

    def get_status_color(self, status_str):
        # We can keep this if needed by other components, but segment uses segment.get_status().get_color()
        from src.core.segment_status import SegmentStatus
        return SegmentStatus.from_string(status_str).get_color().name()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            self.clicked.emit(self.segment_id)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.segment_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        force_action = menu.addAction("Forcer translation (Enforce TM)")
        mt_action = menu.addAction("Suggestions Machine (MT)")
        
        # Set colors for actions
        force_action.setStyleSheet("color: #ef4444; font-weight: bold;") 
        mt_action.setStyleSheet("color: #f59e0b;")

        action = menu.exec(event.globalPos())
        
        if action == force_action:
            self.forceTranslation.emit(self.segment_id)
        elif action == mt_action:
            self.machineTranslation.emit(self.segment_id)
        
        super().contextMenuEvent(event)

    def _setup_text_areas(self):
        # Source
        self.source_container = QFrame()
        self.source_container.setObjectName("SourceContainer")
        self._source_layout = QVBoxLayout(self.source_container)
        self.source_edit = QTextEdit(self.segment.source_text)
        self.source_edit.setObjectName("SourceText")
        self.source_edit.setReadOnly(True)
        self.source_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.source_edit.installEventFilter(self)
        self._source_layout.addWidget(self.source_edit)
        
        # Reference Text (Third Language) - Hidden by default
        self.reference_display = QLabel("")
        self.reference_display.setWordWrap(True)
        self.reference_display.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic; margin-left: 5px; margin-top: 5px;")
        self.reference_display.hide()
        self._source_layout.addWidget(self.reference_display)
        
        # Target
        self.target_container = QFrame()
        self.target_container.setObjectName("TargetContainer")
        self._target_layout = QVBoxLayout(self.target_container)
        self.target_edit = QTextEdit(self.segment.target_text or "")
        self.target_edit.setObjectName("TargetText")
        self.target_edit.setPlaceholderText("Click to start translating...")
        self.target_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.target_edit.textChanged.connect(self.on_text_changed)
        self.target_edit.installEventFilter(self)
        self._target_layout.addWidget(self.target_edit)
        
        # Initial validation
        self.perform_tag_validation(self.segment.target_text or "")

    def _apply_layout_mode(self):
        # Clear existing layout
        layout = self.text_layout_container.layout()
        if layout:
            QWidget().setLayout(layout) # Trick to delete layout
            
        if self.layout_mode == "horizontal":
            layout = QHBoxLayout(self.text_layout_container)
            self.source_container.setStyleSheet("border-right: 1px solid #404040; padding: 12px;")
            self.target_container.setStyleSheet("padding: 12px;")
        else:
            layout = QVBoxLayout(self.text_layout_container)
            self.source_container.setStyleSheet("border-bottom: 1px solid #404040; padding: 12px;")
            self.target_container.setStyleSheet("padding: 12px;")
            
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(self.source_container, 1)
        layout.addWidget(self.target_container, 1)

    def set_layout_mode(self, mode):
        """Set layout mode: 'horizontal' or 'vertical'."""
        if mode not in ["horizontal", "vertical"]: return
        self.layout_mode = mode
        self._apply_layout_mode()

    def set_reference_text(self, text: str):
        """Displays a third language translation as reference."""
        if text:
            self.reference_display.setText(f"📘 Réf: {text}")
            self.reference_display.show()
        else:
            self.reference_display.hide()

    def update_status_style(self):
        """Review status color and apply to card border."""
        status = self.segment.get_status()
        color = status.get_color().name()
        # Update badge
        self.status_badge.setText(status.get_label().upper())
        self.status_badge.setStyleSheet(f"font-size: 9px; font-weight: 800; color: {color}; padding: 2px 6px; border: 1px solid {color}; border-radius: 4px;")
        
        # Update card border (Left thick border)
        base_style = """
            QFrame#SegmentCard {
                background-color: #262626;
                border-radius: 8px;
                border-left: 4px solid %s;
            }
            QFrame#SegmentCard[active="true"] {
                background-color: #333333;
                border: 1px solid #3b82f6;
                border-left: 4px solid #3b82f6;
            }
        """ % color
        self.setStyleSheet(base_style)

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
            # Active overrides status color with selection color
            self.setStyleSheet("""
                QFrame#SegmentCard {
                    background-color: #333333;
                    border: 1px solid #3b82f6;
                    border-left: 4px solid #3b82f6;
                }
            """)
        else:
            self.update_status_style() # Revert to status color

    def on_text_changed(self):
        text = self.target_edit.toPlainText()
        self.textChanged.emit(self.segment_id, text)
        self.perform_tag_validation(text)
        
        # Restart grammar debounce timer (1.5s)
        self.grammar_timer.start(1500)

    def perform_tag_validation(self, target_text):
        """Validates tags and updates the warning label."""
        is_valid, missing, extra = validate_tags(self.segment.source_text, target_text)
        if not is_valid:
            msg = "<b>Tag Alert:</b>"
            if missing:
                msg += f" Missing {', '.join(missing)}"
            if extra:
                if missing: msg += " |"
                msg += f" Extra {', '.join(extra)}"
            self.tag_warning_label.setText(msg)
            self.tag_warning_label.setVisible(True)
        else:
            self.tag_warning_label.setVisible(False)

    def set_grammar_enabled(self, enabled):
        """Enable or disable real-time grammar checking."""
        self.grammar_enabled = enabled
        if not enabled:
            self.grammar_warning_label.setVisible(False)
            self.grammar_timer.stop()

    def check_grammar_realtime(self):
        """Perform real-time grammar check (debounced)."""
        if not self.grammar_enabled:
            return
            
        text = self.target_edit.toPlainText()
        if not text or len(text) < 3:
            self.grammar_warning_label.setVisible(False)
            return
            
        # For now, assume Target Language = French if not specified
        # In the future, we should get this from Project context via higher component
        lang = "fr" 
        
        issues = self.grammar_checker.check(text, lang)
        if issues:
            # Show first issue for simplicity in real-time
            issue = issues[0]
            msg = f"<b>Grammar:</b> {issue.message}"
            if issue.suggestions:
                msg += f" (Suggestions: {', '.join(issue.suggestions[:3])})"
            self.grammar_warning_label.setText(msg)
            self.grammar_warning_label.setVisible(True)
        else:
            self.grammar_warning_label.setVisible(False)

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
        self.bar_bg.setStyleSheet("background-color: #262626; border-radius: 2px;")
        
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
        self.set_active_item(item_id)
        self.itemClicked.emit(item_id)

    def set_active_item(self, item_id):
        for item in self.items:
            item.set_active(item.item_id == item_id)

    def update_item_progress(self, item_id, progress):
        for item in self.items:
            if item.item_id == item_id:
                item.update_progress(progress)
                break

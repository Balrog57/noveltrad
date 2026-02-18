"""
Real-time Tag Validation Widget for NovelTrad.
Provides instant feedback on tag errors during editing.
Conforms to §12.9 of the specification.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QFrame, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QPalette


class TagValidationIndicator(QWidget):
    """
    Real-time tag validation indicator that shows tag status.
    Displays warnings/errors as the user types.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_tags = []
        self.target_tags = []
        self.errors = []
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Icon
        self.icon_label = QLabel("🏷️")
        self.icon_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.icon_label)
        
        # Status text
        self.status_label = QLabel("Tags OK")
        self.status_label.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.status_label)
        
        # Error count
        self.error_count = QLabel("")
        self.error_count.setStyleSheet("background-color: #22c55e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;")
        self.error_count.setVisible(False)
        layout.addWidget(self.error_count)
        
        layout.addStretch()
        
        # Details button
        self.details_btn = QPushButton("Details")
        self.details_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.details_btn.clicked.connect(self.show_details)
        self.details_btn.setVisible(False)
        layout.addWidget(self.details_btn)
    
    def validate(self, source_text: str, target_text: str):
        """
        Validate tags in real-time.
        
        Args:
            source_text: Original source segment text
            target_text: Current target segment text
        """
        from src.core.tag_manager import TagManager
        
        tm = TagManager()
        
        # Extract tags from both
        _, source_tags = tm.extract_tags(source_text)
        _, target_tags = tm.extract_tags(target_text)
        
        self.source_tags = source_tags
        self.target_tags = target_tags
        
        # Validate
        self.errors = tm.validate_tags(source_text, target_text)
        
        # Update UI
        self.update_display()
    
    def update_display(self):
        """Update the indicator based on validation results."""
        if not self.source_tags:
            # No tags in source, hide indicator
            self.setVisible(False)
            return
        
        self.setVisible(True)
        
        if not self.errors:
            # All good
            self.status_label.setText("Tags OK")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: 600;")
            self.error_count.setVisible(False)
            self.details_btn.setVisible(False)
        else:
            # Has errors
            error_count = len(self.errors)
            self.status_label.setText(f"Tag Error{'' if error_count == 1 else 's'}")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 600;")
            
            self.error_count.setText(str(error_count))
            self.error_count.setStyleSheet("background-color: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;")
            self.error_count.setVisible(True)
            
            self.details_btn.setVisible(True)
    
    def show_details(self):
        """Show detailed error information."""
        if not self.errors:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        error_text = "Tag Validation Errors:\n\n"
        
        for error in self.errors:
            error_text += f"• {error.error_type.upper()}: {error.message}\n"
            if hasattr(error, 'tag'):
                error_text += f"  Tag: {error.tag}\n"
            error_text += "\n"
        
        QMessageBox.Warning(self, "Tag Validation Details", error_text)


class RealTimeTagValidator:
    """
    Mixin class to add real-time tag validation to segment editing.
    """
    
    def setup_tag_validation(self, segment_card):
        """
        Setup real-time validation for a segment card.
        
        Args:
            segment_card: SegmentCard widget
        """
        # Connect to text change signal
        if hasattr(segment_card, 'target_edit'):
            segment_card.target_edit.textChanged.connect(
                lambda: self.on_target_text_changed(segment_card)
            )
    
    def on_target_text_changed(self, segment_card):
        """Handle target text changes for real-time validation."""
        if not hasattr(self, 'tag_validation_indicator'):
            return
        
        source_text = segment_card.source_text or ""
        target_text = segment_card.target_edit.toPlainText() or ""
        
        self.tag_validation_indicator.validate(source_text, target_text)


def create_tag_validation_label(main_window):
    """
    Create and attach tag validation indicator to main window.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        TagValidationIndicator instance
    """
    indicator = TagValidationIndicator()
    return indicator

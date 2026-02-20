"""
Segment Filter Toolbar for NovelTrad.
Allows filtering segments by status (like OmegaT).
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QComboBox, 
                             QPushButton, QButtonGroup, QRadioButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class SegmentFilterToolbar(QWidget):
    """
    Toolbar for filtering segments by status.
    Similar to OmegaT's filter functionality.
    """
    
    filterChanged = pyqtSignal(str)  # Signal when filter changes
    
    # Filter constants
    FILTER_ALL = "all"
    FILTER_UNTRANSLATED = "untranslated"
    FILTER_TRANSLATED = "translated"
    FILTER_MACHINE = "machine"
    FILTER_VALIDATED = "validated"
    FILTER_AI_REFINED = "ai_refined"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = self.FILTER_ALL
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Label
        label = QLabel("Filter:")
        label.setStyleSheet("font-weight: 600; color: #64748b;")
        layout.addWidget(label)
        
        # Filter buttons (radio-style)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.button_group.buttonClicked.connect(self.on_filter_changed)
        
        # All
        self.btn_all = QRadioButton("All")
        self.btn_all.setChecked(True)
        self.button_group.addButton(self.btn_all, self.FILTER_ALL)
        
        # Untranslated
        self.btn_untranslated = QRadioButton("Untranslated")
        self.button_group.addButton(self.btn_untranslated, self.FILTER_UNTRANSLATED)
        
        # Translated (machine)
        self.btn_machine = QRadioButton("Machine")
        self.button_group.addButton(self.btn_machine, self.FILTER_MACHINE)
        
        # AI Refined
        self.btn_ai = QRadioButton("AI Refined")
        self.button_group.addButton(self.btn_ai, self.FILTER_AI_REFINED)
        
        # Validated
        self.btn_validated = QRadioButton("Validated")
        self.button_group.addButton(self.btn_validated, self.FILTER_VALIDATED)
        
        # Add buttons to layout
        for btn in [self.btn_all, self.btn_untranslated, self.btn_machine, 
                    self.btn_ai, self.btn_validated]:
            layout.addWidget(btn)
        
        # Stats label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #94a3b8; font-size: 11px; margin-left: 20px;")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
    
    def on_filter_changed(self, button):
        """Handle filter change."""
        filter_type = self.button_group.id(button)
        self.current_filter = self.button_group.checkedButton().text().lower()
        
        # Map button to filter
        filter_map = {
            self.btn_all: self.FILTER_ALL,
            self.btn_untranslated: self.FILTER_UNTRANSLATED,
            self.btn_machine: self.FILTER_TRANSLATED,
            self.btn_ai: self.FILTER_AI_REFINED,
            self.btn_validated: self.FILTER_VALIDATED,
        }
        
        self.current_filter = filter_map.get(button, self.FILTER_ALL)
        self.filterChanged.emit(self.current_filter)
    
    def set_filter(self, filter_type):
        """Set filter programmatically."""
        self.current_filter = filter_type
        
        button_map = {
            self.FILTER_ALL: self.btn_all,
            self.FILTER_UNTRANSLATED: self.btn_untranslated,
            self.FILTER_TRANSLATED: self.btn_machine,
            self.FILTER_AI_REFINED: self.btn_ai,
            self.FILTER_VALIDATED: self.btn_validated,
        }
        
        if filter_type in button_map:
            button_map[filter_type].setChecked(True)
        
        self.filterChanged.emit(filter_type)
    
    def update_stats(self, total, untranslated, translated, ai_refined, validated):
        """Update the stats display."""
        self.stats_label.setText(
            f"Total: {total} | Untranslated: {untranslated} | "
            f"Machine: {translated} | AI: {ai_refined} | Validated: {validated}"
        )
    
    def get_filtered_indices(self, segments):
        """
        Get indices of segments that match the current filter.
        
        Args:
            segments: List of segment objects
            
        Returns:
            List of indices
        """
        indices = []
        
        for i, seg in enumerate(segments):
            status = seg.status or 'untranslated'
            
            if self.current_filter == self.FILTER_ALL:
                indices.append(i)
            elif self.current_filter == self.FILTER_UNTRANSLATED:
                if status == 'untranslated':
                    indices.append(i)
            elif self.current_filter == self.FILTER_TRANSLATED:
                if status == 'translated':
                    indices.append(i)
            elif self.current_filter == self.FILTER_MACHINE:
                if status == 'machine':
                    indices.append(i)
            elif self.current_filter == self.FILTER_AI_REFINED:
                if status == 'ai_refined':
                    indices.append(i)
            elif self.current_filter == self.FILTER_VALIDATED:
                if status == 'validated':
                    indices.append(i)
        
        return indices


def create_filter_toolbar(main_window):
    """
    Create and attach filter toolbar to main window.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        SegmentFilterToolbar instance
    """
    toolbar = SegmentFilterToolbar()
    
    # Connect to segment list update
    toolbar.filterChanged.connect(lambda f: main_window.apply_segment_filter(f))
    
    return toolbar

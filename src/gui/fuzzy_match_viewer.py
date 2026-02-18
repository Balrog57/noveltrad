"""
Fuzzy Match Viewer for NovelTrad.
Displays translation memory matches for current segment (OmegaT-style).
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class FuzzyMatchCard(QFrame):
    """
    A single fuzzy match result from the TM.
    """
    selected = pyqtSignal(dict)  # Signal when user selects this match
    
    def __init__(self, match_data, parent=None):
        """
        Args:
            match_data: Dict with keys: 'source', 'target', 'similarity', 'source_lang', 'target_lang'
        """
        super().__init__(parent)
        self.match_data = match_data
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 8px;
                margin: 4px;
            }
            QFrame:hover {
                border-color: #0d7ff2;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        # Header: similarity score
        similarity = self.match_data.get('similarity', 0)
        header_layout = QHBoxLayout()
        
        # Color-coded similarity
        if similarity >= 100:
            color = "#22c55e"  # Green
        elif similarity >= 85:
            color = "#f59e0b"  # Orange
        else:
            color = "#64748b"  # Gray
        
        self.similarity_label = QLabel(f"{similarity}%")
        self.similarity_label.setStyleSheet(f"""
            font-weight: 800;
            font-size: 14px;
            color: {color};
            background-color: #2a2a2a;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        
        header_layout.addWidget(self.similarity_label)
        header_layout.addStretch()
        
        # Source text
        source_label = QLabel("Source:")
        source_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        layout.addWidget(source_label)
        
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setText(self.match_data.get('source', ''))
        self.source_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f0f0f;
                color: #e2e8f0;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        self.source_text.setMaximumHeight(60)
        layout.addWidget(self.source_text)
        
        # Target text
        target_label = QLabel("Target:")
        target_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        layout.addWidget(target_label)
        
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        self.target_text.setText(self.match_data.get('target', ''))
        self.target_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f0f0f;
                color: #60a5fa;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        self.target_text.setMaximumHeight(60)
        layout.addWidget(self.target_text)
        
        # Apply button
        apply_btn = QPushButton("Apply Translation")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7ff2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        apply_btn.clicked.connect(self.on_apply)
        layout.addWidget(apply_btn)
    
    def on_apply(self):
        """Emit signal when user selects this match."""
        self.selected.emit(self.match_data)


class FuzzyMatchViewer(QWidget):
    """
    Panel displaying fuzzy matches from translation memory.
    Shows matches similar to OmegaT's match viewer.
    """
    
    applyMatch = pyqtSignal(dict)  # Signal when user applies a match
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.matches = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("🔍 Translation Memory Matches")
        header.setStyleSheet("""
            font-weight: 700;
            font-size: 13px;
            color: #e2e8f0;
            padding: 10px;
            background-color: #1a1a1a;
            border-bottom: 1px solid #333;
        """)
        layout.addWidget(header)
        
        # Scroll area for matches
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0f0f0f;
                border: none;
            }
        """)
        
        self.matches_container = QWidget()
        self.matches_layout = QVBoxLayout(self.matches_container)
        self.matches_layout.setSpacing(4)
        self.matches_layout.addStretch()
        
        scroll.setWidget(self.matches_container)
        layout.addWidget(scroll)
        
        # Empty state
        self.empty_label = QLabel("No matches found in translation memory")
        self.empty_label.setStyleSheet("""
            color: #64748b;
            font-style: italic;
            padding: 20px;
            alignment: center;
        """)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.matches_layout.insertWidget(0, self.empty_label)
    
    def set_matches(self, matches):
        """
        Set fuzzy matches to display.
        
        Args:
            matches: List of match dicts with keys: 'source', 'target', 'similarity'
        """
        self.matches = sorted(matches, key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Clear existing matches (keep empty label and stretch)
        while self.matches_layout.count() > 2:
            item = self.matches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new matches
        if not self.matches:
            self.empty_label.setVisible(True)
        else:
            self.empty_label.setVisible(False)
            
            for match in self.matches[:5]:  # Show top 5 matches
                card = FuzzyMatchCard(match)
                card.selected.connect(self.on_match_selected)
                self.matches_layout.insertWidget(self.matches_layout.count() - 1, card)
    
    def on_match_selected(self, match_data):
        """Handle match selection."""
        self.applyMatch.emit(match_data)
    
    def clear(self):
        """Clear all matches."""
        self.set_matches([])
    
    def get_match_count(self):
        """Get number of matches."""
        return len(self.matches)


def create_fuzzy_match_panel(main_window):
    """
    Create and attach fuzzy match panel to main window.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        FuzzyMatchViewer instance
    """
    panel = FuzzyMatchViewer()
    
    # Connect to segment change
    if hasattr(main_window, 'segment_list'):
        # When segment changes, update matches
        pass
    
    return panel

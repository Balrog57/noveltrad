"""
Search and Replace Dialog with Regex Support for NovelTrad.
Conforms to §12.5 of the specification.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit,
                             QComboBox, QProgressBar, QGroupBox, QButtonGroup,
                             QRadioButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
import re


class SearchReplaceDialog(QDialog):
    """
    Dialog for searching and replacing text with regex support.
    """
    
    replaceInAll = pyqtSignal(str, str, bool, bool)  # search, replace, use_regex, case_sensitive
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search & Replace")
        self.resize(600, 400)
        self.matches = []
        self.current_match = 0
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Search group
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout()
        
        # Search input
        search_row = QHBoxLayout()
        search_label = QLabel("Find:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        search_row.addWidget(search_label)
        search_row.addWidget(self.search_input)
        search_layout.addLayout(search_row)
        
        # Options
        options_row = QHBoxLayout()
        
        self.use_regex = QCheckBox("Use Regex")
        self.use_regex.toggled.connect(self.on_options_changed)
        options_row.addWidget(self.use_regex)
        
        self.case_sensitive = QCheckBox("Case Sensitive")
        self.case_sensitive.setChecked(True)
        self.case_sensitive.toggled.connect(self.on_options_changed)
        options_row.addWidget(self.case_sensitive)
        
        self.search_source = QCheckBox("Search Source")
        self.search_source.setChecked(True)
        self.search_source.toggled.connect(self.on_options_changed)
        options_row.addWidget(self.search_source)
        
        self.search_target = QCheckBox("Search Target")
        self.search_target.setChecked(True)
        self.search_target.toggled.connect(self.on_options_changed)
        options_row.addWidget(self.search_target)
        
        options_row.addStretch()
        search_layout.addLayout(options_row)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Replace group
        replace_group = QGroupBox("Replace")
        replace_layout = QVBoxLayout()
        
        replace_row = QHBoxLayout()
        replace_label = QLabel("Replace with:")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Enter replacement text...")
        replace_row.addWidget(replace_label)
        replace_row.addWidget(self.replace_input)
        replace_layout.addLayout(replace_row)
        
        replace_group.setLayout(replace_layout)
        layout.addWidget(replace_group)
        
        # Results
        results_layout = QHBoxLayout()
        
        self.results_label = QLabel("0 matches found")
        self.results_label.setStyleSheet("color: #64748b; font-size: 12px;")
        results_layout.addWidget(self.results_label)
        
        results_layout.addStretch()
        
        find_next_btn = QPushButton("Find Next")
        find_next_btn.clicked.connect(self.find_next)
        results_layout.addWidget(find_next_btn)
        
        find_prev_btn = QPushButton("Find Previous")
        find_prev_btn.clicked.connect(self.find_prev)
        results_layout.addWidget(find_prev_btn)
        
        layout.addLayout(results_layout)
        
        # Match preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(100)
        self.preview.setPlaceholderText("Match preview will appear here...")
        layout.addWidget(self.preview)
        
        # Progress bar (for replace all)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace_current)
        buttons.addWidget(replace_btn)
        
        replace_all_btn = QPushButton("Replace All in Current Chapter")
        replace_all_btn.setStyleSheet("background-color: #f59e0b; color: white; font-weight: bold;")
        replace_all_btn.clicked.connect(self.replace_all_chapter)
        buttons.addWidget(replace_all_btn)
        
        replace_all_project_btn = QPushButton("Replace All in Project")
        replace_all_project_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold;")
        replace_all_project_btn.clicked.connect(self.replace_all_project)
        buttons.addWidget(replace_all_project_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons.addWidget(close_btn)
        
        layout.addLayout(buttons)
        
        # Connect search input
        self.search_input.textChanged.connect(self.on_search_changed)
    
    def on_options_changed(self):
        """Handle option changes."""
        self.search()
    
    def on_search_changed(self):
        """Handle search text changes."""
        self.search()
    
    def search(self):
        """Perform search based on current options."""
        query = self.search_input.text()
        
        if not query:
            self.matches = []
            self.results_label.setText("0 matches found")
            self.preview.clear()
            return
        
        # Build regex if needed
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        if self.use_regex.isChecked():
            try:
                pattern = re.compile(query, flags)
            except re.error as e:
                self.results_label.setText(f"Invalid regex: {e}")
                return
        else:
            # Escape regex special chars for literal search
            pattern = re.compile(re.escape(query), flags)
        
        # This would be connected to actual segment data in the main window
        # For now, just update UI
        self.results_label.setText(f"Searching in {'source' if self.search_source.isChecked() else ''} {'target' if self.search_target.isChecked() else ''}...")
    
    def find_next(self):
        """Navigate to next match."""
        if self.matches:
            self.current_match = (self.current_match + 1) % len(self.matches)
            self.highlight_match()
    
    def find_prev(self):
        """Navigate to previous match."""
        if self.matches:
            self.current_match = (self.current_match - 1) % len(self.matches)
            self.highlight_match()
    
    def highlight_match(self):
        """Highlight current match in preview."""
        if self.matches and self.current_match < len(self.matches):
            match = self.matches[self.current_match]
            # Would scroll to and highlight the segment
            self.results_label.setText(f"Match {self.current_match + 1} of {len(self.matches)}")
    
    def replace_current(self):
        """Replace the current match."""
        if not self.matches:
            return
        
        # Emit signal to replace in main window
        self.replaceInAll.emit(
            self.search_input.text(),
            self.replace_input.text(),
            self.use_regex.isChecked(),
            self.case_sensitive.isChecked()
        )
    
    def replace_all_chapter(self):
        """Replace all matches in current chapter."""
        self.replaceInAll.emit(
            self.search_input.text(),
            self.replace_input.text(),
            self.use_regex.isChecked(),
            self.case_sensitive.isChecked()
        )
        QMessageBox.information(self, "Replace", "Replaced in current chapter.")
    
    def replace_all_project(self):
        """Replace all matches in project."""
        reply = QMessageBox.question(
            self, "Confirm",
            "This will replace ALL occurrences in the entire project. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.replaceInAll.emit(
                self.search_input.text(),
                self.replace_input.text(),
                self.use_regex.isChecked(),
                self.case_sensitive.isChecked()
            )
            QMessageBox.information(self, "Replace", "Replaced in entire project.")


def create_search_replace_dialog(main_window):
    """
    Create and show search/replace dialog.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        SearchReplaceDialog instance
    """
    dialog = SearchReplaceDialog(main_window)
    
    # Connect signals to main window methods
    dialog.replaceInAll.connect(main_window.perform_replace_all)
    
    return dialog

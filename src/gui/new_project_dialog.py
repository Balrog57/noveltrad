from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QFileDialog, QFormLayout, 
                             QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt
import os

class NewProjectDialog(QDialog):
    def __init__(self, parent=None, language_manager=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setFixedWidth(500)
        self.language_manager = language_manager
        self.source_path = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Novel Project")
        form_layout.addRow("Project Name:", self.name_edit)
        
        # Source File
        self.file_btn = QPushButton("Select File or Folder")
        self.file_btn.clicked.connect(self.select_source)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888;")
        form_layout.addRow("Source Content:", self.file_btn)
        form_layout.addRow("", self.file_label)
        
        # Languages
        self.source_lang = QComboBox()
        self.target_lang = QComboBox()
        
        if self.language_manager:
            langs = self.language_manager.get_supported_languages()
            # Filter? Maybe not strict filter here, let user choose from all supported
            # But prioritizing installed ones
            
            for lang in langs:
                 self.source_lang.addItem(lang['name'], lang['code'])
                 self.target_lang.addItem(lang['name'], lang['code'])
                 
            # Defaults
            self.source_lang.setCurrentText("English")
            self.target_lang.setCurrentText("French")
            
        form_layout.addRow("Source Language:", self.source_lang)
        form_layout.addRow("Target Language:", self.target_lang)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        create_btn = QPushButton("Create Project")
        create_btn.clicked.connect(self.create_project)
        create_btn.setStyleSheet("""
            background-color: #0d7ff2; 
            color: white; 
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        """)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(create_btn)
        
        layout.addLayout(btn_layout)
        
    def select_source(self):
        # We allow file or directory
        # For simplicity, let's pick file first, but maybe we need a toggle?
        # Let's use getOpenFileName for now, extended to folder if needed (custom logic)
        # Standard approach: Pick file (txt, docx, epub)
        
        fname, _ = QFileDialog.getOpenFileName(
            self, "Select Source File", "", 
            "Documents (*.txt *.docx *.epub *.pdf);;All Files (*)"
        )
        
        if fname:
            self.source_path = fname
            self.file_label.setText(os.path.basename(fname))
            # Auto-fill name if empty
            if not self.name_edit.text():
                base = os.path.splitext(os.path.basename(fname))[0]
                self.name_edit.setText(base)
                
    def create_project(self):
        if not self.name_edit.text():
            QMessageBox.warning(self, "Error", "Please enter a project name.")
            return
            
        if not self.source_path:
            QMessageBox.warning(self, "Error", "Please select a source file.")
            return
            
        self.accept()
        
    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "source_path": self.source_path,
            "source_lang": self.source_lang.currentData(),
            "target_lang": self.target_lang.currentData()
        }

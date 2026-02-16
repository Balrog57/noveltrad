from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QProgressBar, 
                             QComboBox, QFrame, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import os

class InstallThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, manager, code):
        super().__init__()
        self.manager = manager
        self.code = code

    def run(self):
        try:
            self.manager.install_language_pack(self.code, callback=self.on_progress)
            self.finished.emit(True, self.code)
        except Exception as e:
            self.finished.emit(False, str(e))

    def on_progress(self, message, value):
        self.progress.emit(message, value)

class LanguageStore(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Language Store (Unified)")
        self.resize(600, 600)
        
        from src.core.language_manager import LanguageManager
        self.lang_manager = LanguageManager()
        
        self.init_ui()
        self.load_languages()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Unified Language Packs")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #e2e8f0; margin-bottom: 10px;")
        layout.addWidget(header)
        
        description = QLabel("Installing a pack adds support for Argos Translate, NLLB, and the Dictionary.")
        description.setStyleSheet("color: #94a3b8; margin-bottom: 10px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Models List
        self.models_list = QListWidget()
        self.models_list.setStyleSheet("""
            QListWidget { background-color: #111625; border: 1px solid #1e293b; border-radius: 8px; color: #e2e8f0; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #1e293b; }
            QListWidget::item:selected { background-color: #1e293b; color: #3b82f6; }
        """)
        layout.addWidget(self.models_list)
        
        # Progress
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #1e293b; border-radius: 4px; text-align: center; height: 10px; }
            QProgressBar::chunk { background-color: #3b82f6; }
        """)
        layout.addWidget(self.progress_bar)
        
        # Actions
        actions = QHBoxLayout()
        self.install_btn = QPushButton("Install Pack")
        self.install_btn.setProperty("primary", True)
        self.install_btn.setMinimumHeight(40)
        self.install_btn.clicked.connect(self.install_selected)
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.reject)
        
        actions.addWidget(close_btn)
        actions.addWidget(self.install_btn)
        layout.addLayout(actions)

    def load_languages(self):
        self.models_list.clear() # Clear existing items
        languages = self.lang_manager.get_supported_languages()
        
        for lang in languages:
            # lang is {'code': 'fr', 'name': 'French', 'installed': bool}
            status = "(Installed)" if lang.get('installed') else ""
            display_text = f"{lang['name']} ({lang['code']}) {status}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, lang['code'])
            if status:
                item.setForeground(Qt.GlobalColor.gray) # Grey out installed items? Or Green?
                # Gray implies disabled/done. Let's keep it consistent with previous logic.
            self.models_list.addItem(item)
            
        self.status_label.setText(f"Found {len(languages)} supported languages.")

    def install_selected(self):
        selected = self.models_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select a language pack to install.")
            return
            
        code = selected.data(Qt.ItemDataRole.UserRole)
        name = selected.text()
        
        reply = QMessageBox.question(self, "Confirm Installation", 
                                   f"Install unified pack for {name}?\nThis will download models and dictionaries.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.No:
            return
        
        self.install_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.thread = InstallThread(self.lang_manager, code)
        self.thread.progress.connect(self.on_install_progress)
        self.thread.finished.connect(self.on_install_finished)
        self.thread.start()

    def on_install_progress(self, message, value):
        self.status_label.setText(message)
        self.progress_bar.setValue(value)

    def on_install_finished(self, success, result):
        self.install_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.status_label.setText(f"Successfully installed pack for {result}")
            QMessageBox.information(self, "Success", f"Language pack for {result} installed successfully.")
        else:
            self.status_label.setText(f"Installation failed")
            QMessageBox.critical(self, "Error", f"Installation failed: {result}")

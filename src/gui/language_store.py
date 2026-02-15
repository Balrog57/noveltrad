from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QProgressBar, 
                             QComboBox, QFrame, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import os

class InstallThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, engine, model_id):
        super().__init__()
        self.engine = engine
        self.model_id = model_id

    def run(self):
        try:
            success = self.engine.install_model(self.model_id, callback=self.on_progress)
            self.finished.emit(success, self.model_id)
        except Exception as e:
            self.finished.emit(False, str(e))

    def on_progress(self, message, value):
        self.progress.emit(message, value)

class LanguageStore(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Language Store")
        self.resize(600, 500)
        
        from src.engines import list_engines, get_engine_instance
        self.engines_list = list_engines()
        self.current_engine_name = self.engines_list[0] if self.engines_list else None
        
        self.init_ui()
        self.load_models()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Engine Selector
        header = QHBoxLayout()
        header.addWidget(QLabel("Select Engine:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(self.engines_list)
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        header.addWidget(self.engine_combo)
        header.addStretch()
        layout.addLayout(header)
        
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
        self.install_btn = QPushButton("Install Selected")
        self.install_btn.setProperty("primary", True)
        self.install_btn.setMinimumHeight(40)
        self.install_btn.clicked.connect(self.install_selected)
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.reject)
        
        actions.addWidget(close_btn)
        actions.addWidget(self.install_btn)
        layout.addLayout(actions)

    def on_engine_changed(self, name):
        self.current_engine_name = name
        self.load_models()

    def load_models(self):
        self.models_list.clear()
        if not self.current_engine_name:
            return
            
        from src.engines import get_engine_instance
        engine = get_engine_instance(self.current_engine_name)
        if not engine:
            return
            
        models = engine.get_available_models()
        installed = engine.get_supported_languages()
        
        for model in models:
            # model is dict: id, name, size, from_code, to_code
            status = "(Installed)" if model.get('from_code') in installed and model.get('to_code') in installed else ""
            display_text = f"{model['name']} {status}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, model['id'])
            if status:
                item.setForeground(Qt.GlobalColor.gray)
            self.models_list.addItem(item)

    def install_selected(self):
        selected = self.models_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select a language pack to install.")
            return
            
        model_id = selected.data(Qt.ItemDataRole.UserRole)
        
        from src.engines import get_engine_instance
        engine = get_engine_instance(self.current_engine_name)
        
        self.install_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.thread = InstallThread(engine, model_id)
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
            self.status_label.setText(f"Successfully installed {result}")
            QMessageBox.information(self, "Success", f"Language pack {result} installed successfully.")
            self.load_models()
        else:
            self.status_label.setText(f"Installation failed")
            QMessageBox.critical(self, "Error", f"Installation failed: {result}")

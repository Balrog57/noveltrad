from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QTabWidget, QWidget, 
                             QFormLayout, QSpinBox, QDoubleSpinBox, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt
import os
import json
from src.core.project_schema import ProjectSchema, Genre, SegmentationStrategy

class ProjectSettingsDialog(QDialog):
    def __init__(self, parent, project_manager):
        super().__init__(parent)
        self.project_manager = project_manager
        self.config = getattr(self.project_manager, 'project_config', None)
        
        self.setWindowTitle(f"Project Settings - {self.config.title if self.config else 'Unknown'}")
        self.resize(600, 550)
        
        self.layout = QVBoxLayout(self)
        
        if not self.config:
            self.layout.addWidget(QLabel("Error: No project configuration loaded."))
            btns = QHBoxLayout()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            btns.addWidget(close_btn)
            self.layout.addLayout(btns)
            return

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        self.init_metadata_tab()
        self.init_tm_tab()
        self.init_backup_tab()
        self.init_accessibility_tab()
        
        btns = QHBoxLayout()
        btns.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)
        btns.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        
        self.layout.addLayout(btns)
        
        self.load_data()

    def init_metadata_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.title_input = QLineEdit()
        layout.addRow("Project Title:", self.title_input)
        
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        layout.addRow("Description:", self.desc_input)
        
        self.genre_combo = QComboBox()
        for genre in Genre:
            self.genre_combo.addItem(genre.value.capitalize(), genre.value)
        layout.addRow("Main Genre:", self.genre_combo)
        
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["NLLB (Offline)", "Argos Translate (Offline)", "LLM (Online/Local)"])
        layout.addRow("Default Engine:", self.engine_combo)
        
        self.seg_combo = QComboBox()
        for seg in SegmentationStrategy:
            self.seg_combo.addItem(seg.value.capitalize(), seg.value)
        layout.addRow("Segmentation:", self.seg_combo)
        
        self.tabs.addTab(tab, "Metadata")

    def init_tm_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.tm_enforce = QLineEdit()
        layout.addRow("Enforce Folder:", self.tm_enforce)
        
        self.tm_auto = QLineEdit()
        layout.addRow("Auto Folder:", self.tm_auto)
        
        self.tm_mt = QLineEdit()
        layout.addRow("MT Folder:", self.tm_mt)
        
        self.fuzzy_threshold = QSpinBox()
        self.fuzzy_threshold.setRange(0, 100)
        self.fuzzy_threshold.setSuffix("%")
        layout.addRow("Fuzzy Threshold:", self.fuzzy_threshold)
        
        self.penalty = QSpinBox()
        self.penalty.setRange(0, 100)
        self.penalty.setSuffix("%")
        layout.addRow("MT Penalty:", self.penalty)
        
        self.auto_insert = QSpinBox()
        self.auto_insert.setRange(0, 100)
        self.auto_insert.setSuffix("%")
        layout.addRow("Auto Insert Confidence:", self.auto_insert)
        
        self.tabs.addTab(tab, "Translation Memory")

    def init_backup_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.backup_enabled = QCheckBox("Enable Automatic Backups")
        layout.addRow(self.backup_enabled)
        
        self.backup_before_mod = QCheckBox("Backup before segment modification")
        layout.addRow(self.backup_before_mod)
        
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 1440)
        self.backup_interval.setSuffix(" minutes")
        layout.addRow("Backup Interval:", self.backup_interval)
        
        self.max_snapshots = QSpinBox()
        self.max_snapshots.setRange(1, 100)
        layout.addRow("Max Snapshots:", self.max_snapshots)
        
        self.tabs.addTab(tab, "Backups")

    def init_accessibility_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        layout.addRow("Theme:", self.theme_combo)
        
        self.font_scale = QDoubleSpinBox()
        self.font_scale.setRange(0.5, 2.0)
        self.font_scale.setSingleStep(0.1)
        layout.addRow("Font Scale:", self.font_scale)
        
        self.colorblind_combo = QComboBox()
        self.colorblind_combo.addItems(["none", "deuteranopia", "protanopia", "tritanopia"])
        layout.addRow("Colorblind Mode:", self.colorblind_combo)
        
        self.high_contrast = QCheckBox("High Contrast Mode")
        layout.addRow(self.high_contrast)
        
        self.tabs.addTab(tab, "Accessibility")

    def load_data(self):
        # Metadata
        self.title_input.setText(self.config.title)
        self.desc_input.setPlainText(self.config.description or "")
        
        idx = self.genre_combo.findData(self.config.genres[0].value if self.config.genres else "general")
        if idx >= 0: self.genre_combo.setCurrentIndex(idx)
            
        self.engine_combo.setCurrentText(self.config.default_engine)
        
        idx = self.seg_combo.findData(self.config.segmentation.value)
        if idx >= 0: self.seg_combo.setCurrentIndex(idx)

        # TM
        self.tm_enforce.setText(self.config.tm_settings.enforce_folder)
        self.tm_auto.setText(self.config.tm_settings.auto_folder)
        self.tm_mt.setText(self.config.tm_settings.mt_folder)
        self.fuzzy_threshold.setValue(self.config.tm_settings.fuzzy_threshold)
        self.penalty.setValue(self.config.tm_settings.penalty_percentage)
        self.auto_insert.setValue(self.config.tm_settings.auto_insert_confidence)

        # Backups
        self.backup_enabled.setChecked(self.config.backup.enabled)
        self.backup_before_mod.setChecked(self.config.backup.before_modification)
        self.backup_interval.setValue(self.config.backup.interval_minutes)
        self.max_snapshots.setValue(self.config.backup.max_snapshots)

        # Accessibility
        self.theme_combo.setCurrentText(self.config.accessibility.theme)
        self.font_scale.setValue(self.config.accessibility.font_scale)
        idx = self.colorblind_combo.findText(self.config.accessibility.colorblind_mode)
        if idx >= 0: self.colorblind_combo.setCurrentIndex(idx)
        self.high_contrast.setChecked(self.config.accessibility.high_contrast)

    def save_and_close(self):
        if not self.config:
            return

        # Metadata
        self.config.title = self.title_input.text()
        self.config.description = self.desc_input.toPlainText()
        self.config.genres = [Genre(self.genre_combo.currentData())]
        self.config.default_engine = self.engine_combo.currentText()
        self.config.segmentation = SegmentationStrategy(self.seg_combo.currentData())

        # TM
        self.config.tm_settings.enforce_folder = self.tm_enforce.text()
        self.config.tm_settings.auto_folder = self.tm_auto.text()
        self.config.tm_settings.mt_folder = self.tm_mt.text()
        self.config.tm_settings.fuzzy_threshold = self.fuzzy_threshold.value()
        self.config.tm_settings.penalty_percentage = self.penalty.value()
        self.config.tm_settings.auto_insert_confidence = self.auto_insert.value()

        # Backups
        prev_backup_enabled = self.config.backup.enabled
        prev_interval = self.config.backup.interval_minutes
        
        self.config.backup.enabled = self.backup_enabled.isChecked()
        self.config.backup.before_modification = self.backup_before_mod.isChecked()
        self.config.backup.interval_minutes = self.backup_interval.value()
        self.config.backup.max_snapshots = self.max_snapshots.value()

        # Accessibility
        self.config.accessibility.theme = self.theme_combo.currentText()
        self.config.accessibility.font_scale = self.font_scale.value()
        self.config.accessibility.colorblind_mode = self.colorblind_combo.currentText()
        self.config.accessibility.high_contrast = self.high_contrast.isChecked()

        # Save to file
        try:
            if not self.project_manager.current_project:
                raise Exception("No active project loaded.")
                
            project_dir = os.path.dirname(os.path.abspath(self.project_manager.db.database))
            json_path = os.path.join(project_dir, ".noveltrad", "project.json")
            
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(self.config.model_dump_json(indent=2))
                
            # Restart auto backup if settings changed
            if hasattr(self.parent(), 'backup_manager') and self.parent().backup_manager:
                if self.config.backup.enabled:
                    if not prev_backup_enabled or prev_interval != self.config.backup.interval_minutes:
                        self.parent().backup_manager.stop_auto_backup()
                        self.parent().backup_manager.start_auto_backup(self.config.backup.interval_minutes)
                else:
                    self.parent().backup_manager.stop_auto_backup()

            QMessageBox.information(self, "Success", "Project settings saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

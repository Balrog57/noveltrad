"""
Project Settings Dialog v3 for NovelTrad OmegaT-compliant projects.
UI with tabs for metadata, TM settings, backup, and accessibility.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
        QPushButton, QComboBox, QCheckBox, QTabWidget, QWidget, 
        QFormLayout, QFileDialog, QSpinBox, QDoubleSpinBox, 
        QTextEdit, QGroupBox, QTreeWidget, QTreeWidgetItem, QStyledItemDelegate,
        QStyleOptionViewItem, QStyle, QApplication
    )
    from PyQt6.QtCore import Qt, QMargins, QModelIndex
    from PyQt6.QtGui import QPalette, QColor
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("PyQt6 not available. Install with: pip install PyQt6")


if QT_AVAILABLE:
    class ThemeDelegate(QStyledItemDelegate):
        """Delegate for themed combobox items."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.themes = {
                "Dark": "#2b2b2b",
                "Light": "#f5f5f5",
                "High Contrast": "#000000",
                "Deuteranopia": "#1a1a2e",
                "Protanopia": "#1a2e1a",
                "Tritanopia": "#2e1a1a",
            }
        
        def paint(self, painter, option, index):
            theme_name = index.data(Qt.ItemDataRole.DisplayRole)
            bg_color = self.themes.get(theme_name, "#2b2b2b")
            
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QColor(bg_color))
            
            super().paint(painter, option, index)
    
    class ProjectSettingsDialogV3(QDialog):
        """
        Project Settings Dialog v3 for OmegaT-compliant projects.
        
        Features:
        - Metadata tab: title, description, languages, genres
        - Translation Memory tab: TM folders layout
        - Backup tab: interval, max snapshots, backup location
        - Accessibility tab: themes, colorblind mode, font scale
        
        Usage:
        ```python
        dialog = ProjectSettingsDialogV3(parent, project_data)
        if dialog.exec():
            updated_data = dialog.get_data()
        ```
        """
        
        def __init__(
            self,
            project_data: Dict[str, Any],
            parent: Optional[QWidget] = None
        ):
            if not QT_AVAILABLE:
                raise RuntimeError("PyQt6 not available")
            
            super().__init__(parent)
            self.setWindowTitle("Project Settings v3")
            self.resize(700, 600)
            
            self.project_data = project_data.copy()
            self.original_data = project_data.copy()
            
            self.layout = QVBoxLayout(self)
            
            self.tabs = QTabWidget()
            self.layout.addWidget(self.tabs)
            
            self._init_metadata_tab()
            self._init_segmentation_tab()
            self._init_tm_tab()
            self._init_glossary_tab()
            self._init_backup_tab()
            self._init_sync_tab()
            self._init_accessibility_tab()
            
            buttons = QHBoxLayout()
            buttons.addStretch()
            
            self.save_btn = QPushButton("Save")
            self.save_btn.clicked.connect(self.save_and_close)
            self.save_btn.setMinimumHeight(40)
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            buttons.addWidget(self.save_btn)
            
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self.reject)
            self.cancel_btn.setMinimumHeight(40)
            self.cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            buttons.addWidget(self.cancel_btn)
            
            self.layout.addLayout(buttons)
            
            self._load_settings()
        
        def _init_metadata_tab(self) -> None:
            """Initialize metadata configuration tab."""
            self.metadata_tab = QWidget()
            self.tabs.addTab(self.metadata_tab, "Métadonnées")
            
            layout = QVBoxLayout(self.metadata_tab)
            layout.setSpacing(15)
            
            form = QFormLayout()
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            
            self.txt_title = QLineEdit()
            self.txt_title.setPlaceholderText("Project display title")
            form.addRow("<b>Title</b>", self.txt_title)
            
            self.txt_description = QTextEdit()
            self.txt_description.setMaximumHeight(100)
            self.txt_description.setPlaceholderText("Project description...")
            form.addRow("Description", self.txt_description)
            
            self.txt_project_name = QLineEdit()
            self.txt_project_name.setPlaceholderText("internal_name (no spaces)")
            form.addRow("Project Name", self.txt_project_name)
            
            self.cmb_source_lang = QComboBox()
            self.cmb_source_lang.addItems([
                "en", "fr", "es", "de", "it", "pt", "ru", "ja", "zh", "ko",
                "ar", "he", "tr", "nl", "pl", "cs", "sv", "da", "fi", "no"
            ])
            form.addRow("Source Language", self.cmb_source_lang)
            
            self.cmb_target_lang = QComboBox()
            self.cmb_target_lang.addItems([
                "fr", "en", "es", "de", "it", "pt", "ru", "ja", "zh", "ko",
                "ar", "he", "tr", "nl", "pl", "cs", "sv", "da", "fi", "no"
            ])
            form.addRow("Target Language", self.cmb_target_lang)
            
            self.cmb_genres = QComboBox()
            self.cmb_genres.addItems([
                "general", "literary", "technical", "science_fiction",
                "fantasy", "romance", "mystery", "history", "biography",
                "educational", "game", "custom"
            ])
            form.addRow("Genre", self.cmb_genres)
            
            layout.addLayout(form)
            
            tm_folders = QGroupBox("Translation Memory Folders")
            tm_layout = QVBoxLayout()
            
            tm_folder_tree = QTreeWidget()
            tm_folder_tree.setHeaderLabels(["TM Folder", "Purpose"])
            tm_folder_tree.setColumnWidth(0, 200)
            
            folders = [
                ("tm/enforce", "Force-insert TM (100% matches)"),
                ("tm/auto", "Auto-insert TM (high confidence)"),
                ("tm/mt", "Machine Translation"),
                ("tm/tmx2source", "Reference language display"),
                ("tm/export", "Export location"),
            ]
            
            for folder, purpose in folders:
                item = QTreeWidgetItem([folder, purpose])
                tm_folder_tree.addTopLevelItem(item)
            
            tm_layout.addWidget(tm_folder_tree)
            tm_folders.setLayout(tm_layout)
            layout.addWidget(tm_folders)
            
            layout.addStretch()
        
        def _init_tm_tab(self) -> None:
            """Initialize TM settings tab."""
            self.tm_tab = QWidget()
            self.tabs.addTab(self.tm_tab, "Mémoire de traduction")
            
            layout = QVBoxLayout(self.tm_tab)
            layout.setSpacing(15)
            
            form = QFormLayout()
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            
            self.spinbox_fuzzy_threshold = QSpinBox()
            self.spinbox_fuzzy_threshold.setRange(0, 100)
            self.spinbox_fuzzy_threshold.setValue(60)
            self.spinbox_fuzzy_threshold.setSuffix("%")
            form.addRow("Fuzzy Match Threshold", self.spinbox_fuzzy_threshold)
            
            self.spinbox_auto_insert_confidence = QSpinBox()
            self.spinbox_auto_insert_confidence.setRange(0, 100)
            self.spinbox_auto_insert_confidence.setValue(85)
            self.spinbox_auto_insert_confidence.setSuffix("%")
            form.addRow("Auto-Insert Confidence", self.spinbox_auto_insert_confidence)
            
            self.spinbox_penalty = QSpinBox()
            self.spinbox_penalty.setRange(0, 100)
            self.spinbox_penalty.setValue(30)
            self.spinbox_penalty.setSuffix("%")
            form.addRow("MT Penalty", self.spinbox_penalty)
            
            self.chk_auto_insert = QCheckBox("Auto-insert high-confidence TM matches")
            self.chk_auto_insert.setChecked(True)
            form.addRow("", self.chk_auto_insert)
            
            layout.addLayout(form)
            
            tmx_buttons = QGroupBox("TMX Management")
            tmx_layout = QVBoxLayout()
            
            btn_export_tm = QPushButton("Export to TMX...")
            btn_export_tm.setMinimumHeight(40)
            tmx_layout.addWidget(btn_export_tm)
            
            btn_import_tm = QPushButton("Import from TMX...")
            btn_import_tm.setMinimumHeight(40)
            tmx_layout.addWidget(btn_import_tm)
            
            tmx_buttons.setLayout(tmx_layout)
            layout.addWidget(tmx_buttons)
            
            layout.addStretch()
        
        def _init_backup_tab(self) -> None:
            """Initialize backup settings tab."""
            self.backup_tab = QWidget()
            self.tabs.addTab(self.backup_tab, "Sauvegardes")
            
            layout = QVBoxLayout(self.backup_tab)
            layout.setSpacing(15)
            
            auto_backup = QGroupBox("Automatic Backups")
            auto_layout = QFormLayout()
            auto_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            
            self.chk_backup_enabled = QCheckBox("Enable automatic backups")
            self.chk_backup_enabled.setChecked(True)
            auto_layout.addRow("", self.chk_backup_enabled)
            
            self.spinbox_backup_interval = QSpinBox()
            self.spinbox_backup_interval.setRange(1, 1440)
            self.spinbox_backup_interval.setValue(3)
            self.spinbox_backup_interval.setSuffix(" minutes")
            auto_layout.addRow("Backup Interval", self.spinbox_backup_interval)
            
            self.spinbox_max_snapshots = QSpinBox()
            self.spinbox_max_snapshots.setRange(1, 100)
            self.spinbox_max_snapshots.setValue(10)
            auto_layout.addRow("Max Snapshots", self.spinbox_max_snapshots)
            
            auto_backup.setLayout(auto_layout)
            layout.addWidget(auto_backup)
            
            locations = QGroupBox("Backup Locations")
            loc_layout = QFormLayout()
            
            self.txt_backup_location = QLineEdit()
            self.txt_backup_location.setText("backup")
            loc_layout.addRow("Backup Location", self.txt_backup_location)
            
            self.txt_snapshot_location = QLineEdit()
            self.txt_snapshot_location.setText("snapshots")
            loc_layout.addRow("Snapshot Location", self.txt_snapshot_location)
            
            locations.setLayout(loc_layout)
            layout.addWidget(locations)
            
            self.chk_before_mod = QCheckBox("Create snapshot before segment modification")
            self.chk_before_mod.setChecked(True)
            layout.addWidget(self.chk_before_mod)
            
            layout.addStretch()
        
        def _init_accessibility_tab(self) -> None:
            """Initialize accessibility settings tab."""
            self.accessibility_tab = QWidget()
            self.tabs.addTab(self.accessibility_tab, "Accessibilité")
            
            layout = QVBoxLayout(self.accessibility_tab)
            layout.setSpacing(15)
            
            theme_group = QGroupBox("Theme Settings")
            theme_layout = QFormLayout()
            
            self.cmb_theme = QComboBox()
            self.cmb_theme.addItems([
                "Dark (Default)",
                "Light",
                "High Contrast",
                "Deuteranopia",
                "Protanopia",
                "Tritanopia"
            ])
            theme_layout.addRow("Theme", self.cmb_theme)
            
            self.theme_delegate = ThemeDelegate(self.cmb_theme)
            self.cmb_theme.setItemDelegate(self.theme_delegate)
            
            self.chk_high_contrast = QCheckBox("High Contrast Mode")
            theme_layout.addRow("", self.chk_high_contrast)
            
            theme_group.setLayout(theme_layout)
            layout.addWidget(theme_group)
            
            font_group = QGroupBox("Font Settings")
            font_layout = QFormLayout()
            
            self.cmb_font_family = QComboBox()
            self.cmb_font_family.addItems([
                "Segoe UI",
                "Roboto",
                "Arial",
                "Helvetica",
                "DejaVu Sans",
                "Liberation Sans"
            ])
            font_layout.addRow("Font Family", self.cmb_font_family)
            
            self.spinbox_font_scale = QDoubleSpinBox()
            self.spinbox_font_scale.setRange(0.5, 2.0)
            self.spinbox_font_scale.setValue(1.0)
            self.spinbox_font_scale.setSingleStep(0.1)
            self.spinbox_font_scale.setSuffix("x")
            font_layout.addRow("Font Scale", self.spinbox_font_scale)
            
            self.chk_large_text = QCheckBox("Large Text Mode")
            font_layout.addRow("", self.chk_large_text)
            
            font_group.setLayout(font_layout)
            layout.addWidget(font_group)
            
            colorblind_group = QGroupBox("Colorblind Support")
            cb_layout = QVBoxLayout()
            
            self.cmb_colorblind_mode = QComboBox()
            self.cmb_colorblind_mode.addItems([
                "None",
                "Deuteranopia (red-green)",
                "Protanopia (red-green)",
                "Tritanopia (blue-yellow)"
            ])
            cb_layout.addWidget(self.cmb_colorblind_mode)
            
            self.chk_screen_reader = QCheckBox("Enable screen reader support")
            cb_layout.addWidget(self.chk_screen_reader)
            
            colorblind_group.setLayout(cb_layout)
            layout.addWidget(colorblind_group)
            
            layout.addStretch()

        def _init_segmentation_tab(self) -> None:
            self.segmentation_tab = QWidget()
            self.tabs.addTab(self.segmentation_tab, "Segmentation")
            layout = QVBoxLayout(self.segmentation_tab)
            layout.setSpacing(15)
            
            form = QFormLayout()
            self.cmb_segmentation_rule = QComboBox()
            self.cmb_segmentation_rule.addItems(["sentence", "paragraph"])
            form.addRow("Segmentation Rule", self.cmb_segmentation_rule)
            
            self.txt_local_rules = QLineEdit()
            self.txt_local_rules.setPlaceholderText("Path to local rules file (e.g., rules/segmentation.conf)")
            form.addRow("Local Rules File", self.txt_local_rules)
            layout.addLayout(form)
            layout.addStretch()

        def _init_glossary_tab(self) -> None:
            self.glossary_tab = QWidget()
            self.tabs.addTab(self.glossary_tab, "Glossary")
            layout = QVBoxLayout(self.glossary_tab)
            layout.setSpacing(15)
            
            form = QFormLayout()
            self.chk_glossary_auto_gen = QCheckBox("Enable auto-generation")
            form.addRow("", self.chk_glossary_auto_gen)
            
            self.txt_prompt_template = QTextEdit()
            self.txt_prompt_template.setPlaceholderText("Prompt template for Glossary AI")
            form.addRow("Prompt Template", self.txt_prompt_template)
            
            self.chk_feedback_loop = QCheckBox("Enable feedback loop")
            form.addRow("", self.chk_feedback_loop)
            layout.addLayout(form)
            layout.addStretch()

        def _init_sync_tab(self) -> None:
            self.sync_tab = QWidget()
            self.tabs.addTab(self.sync_tab, "Sync")
            layout = QVBoxLayout(self.sync_tab)
            layout.setSpacing(15)
            
            form = QFormLayout()
            self.cmb_vcs_type = QComboBox()
            self.cmb_vcs_type.addItems(["None", "Git", "SVN"])
            form.addRow("VCS Type", self.cmb_vcs_type)
            
            self.txt_remote_url = QLineEdit()
            self.txt_remote_url.setPlaceholderText("Remote URL (e.g., https://github.com/user/repo.git)")
            form.addRow("Remote URL", self.txt_remote_url)
            
            self.btn_sync_now = QPushButton("Sync Now")
            form.addRow("", self.btn_sync_now)
            layout.addLayout(form)
            layout.addStretch()
        
        def _load_settings(self) -> None:
            """Load current settings into UI."""
            data = self.project_data
            
            self.txt_title.setText(data.get('title', ''))
            self.txt_description.setPlainText(data.get('description', ''))
            self.txt_project_name.setText(data.get('name', ''))
            
            self.cmb_source_lang.setCurrentText(data.get('source_lang', 'en'))
            self.cmb_target_lang.setCurrentText(data.get('target_lang', 'fr'))
            self.cmb_genres.setCurrentText(data.get('genres', ['general'])[0])
            
            tm_settings = data.get('tm_settings', {})
            self.spinbox_fuzzy_threshold.setValue(tm_settings.get('fuzzy_threshold', 60))
            self.spinbox_auto_insert_confidence.setValue(tm_settings.get('auto_insert_confidence', 85))
            self.spinbox_penalty.setValue(tm_settings.get('penalty_percentage', 30))
            self.chk_auto_insert.setChecked(True)
            
            backup = data.get('backup', {})
            self.chk_backup_enabled.setChecked(backup.get('enabled', True))
            self.spinbox_backup_interval.setValue(backup.get('interval_minutes', 3))
            self.spinbox_max_snapshots.setValue(backup.get('max_snapshots', 10))
            self.chk_before_mod.setChecked(backup.get('before_modification', True))
            
            accessibility = data.get('accessibility', {})
            theme = accessibility.get('theme', 'Dark (Default)')
            self.cmb_theme.setCurrentText(theme)
            self.chk_high_contrast.setChecked(accessibility.get('high_contrast', False))
            self.cmb_font_family.setCurrentText(accessibility.get('font_family', 'Segoe UI'))
            self.spinbox_font_scale.setValue(accessibility.get('font_scale', 1.0))
            self.chk_large_text.setChecked(accessibility.get('large_text', False))
            self.cmb_colorblind_mode.setCurrentText(
                accessibility.get('colorblind_mode', 'none').replace('_', ' ').title()
            )
            self.chk_screen_reader.setChecked(accessibility.get('screen_reader', False))

            seg = data.get('segmentation', {})
            self.cmb_segmentation_rule.setCurrentText(seg.get('type', 'sentence'))
            self.txt_local_rules.setText(seg.get('local_rules_file', ''))

            gloss = data.get('glossary', {})
            self.chk_glossary_auto_gen.setChecked(gloss.get('auto_generate', False))
            self.txt_prompt_template.setPlainText(gloss.get('prompt_template', ''))
            self.chk_feedback_loop.setChecked(gloss.get('feedback_loop', False))

            sync = data.get('sync', {})
            self.cmb_vcs_type.setCurrentText(sync.get('vcs_type', 'None'))
            self.txt_remote_url.setText(sync.get('remote_url', ''))
        
        def save_and_close(self) -> None:
            """Save settings and close dialog."""
            self._save_settings()
            self.accept()
        
        def _save_settings(self) -> None:
            """Save UI settings to project data."""
            data = self.project_data
            
            data['title'] = self.txt_title.text().strip()
            data['description'] = self.txt_description.toPlainText().strip()
            data['name'] = self.txt_project_name.text().strip()
            
            data['source_lang'] = self.cmb_source_lang.currentText()
            data['target_lang'] = self.cmb_target_lang.currentText()
            data['genres'] = [self.cmb_genres.currentText()]
            
            data['default_engine'] = "NLLB (Offline)"
            
            data['tm_settings'] = {
                'fuzzy_threshold': self.spinbox_fuzzy_threshold.value(),
                'auto_insert_confidence': self.spinbox_auto_insert_confidence.value(),
                'penalty_percentage': self.spinbox_penalty.value(),
            }
            
            data['backup'] = {
                'enabled': self.chk_backup_enabled.isChecked(),
                'interval_minutes': self.spinbox_backup_interval.value(),
                'max_snapshots': self.spinbox_max_snapshots.value(),
                'before_modification': self.chk_before_mod.isChecked(),
            }
            
            theme_name = self.cmb_theme.currentText().replace(' (Default)', '')
            data['accessibility'] = {
                'theme': theme_name,
                'high_contrast': self.chk_high_contrast.isChecked(),
                'font_family': self.cmb_font_family.currentText(),
                'font_scale': self.spinbox_font_scale.value(),
                'large_text': self.chk_large_text.isChecked(),
                'colorblind_mode': self.cmb_colorblind_mode.currentText().lower().replace(' ', '_'),
                'screen_reader': self.chk_screen_reader.isChecked(),
            }

            data['segmentation'] = {
                'type': self.cmb_segmentation_rule.currentText(),
                'local_rules_file': self.txt_local_rules.text().strip(),
            }
            
            data['glossary'] = {
                'auto_generate': self.chk_glossary_auto_gen.isChecked(),
                'prompt_template': self.txt_prompt_template.toPlainText().strip(),
                'feedback_loop': self.chk_feedback_loop.isChecked(),
            }
            
            data['sync'] = {
                'vcs_type': self.cmb_vcs_type.currentText(),
                'remote_url': self.txt_remote_url.text().strip(),
            }
        
        def get_data(self) -> Dict[str, Any]:
            """Get updated project data."""
            return self.project_data
        
        def is_modified(self) -> bool:
            """Check if settings were modified."""
            return self.project_data != self.original_data


if __name__ == "__main__":
    if not QT_AVAILABLE:
        print("PyQt6 not available. Skipping UI test.")
        sys.exit(0)
    
    import json
    
    app = None
    if not QApplication.instance():
        app = QApplication(sys.argv)
    
    test_data = {
        "schema_version": "3.0.0",
        "name": "test_project",
        "title": "Test Project",
        "source_lang": "en",
        "target_lang": "fr",
        "genres": ["literary"],
        "description": "A test OmegaT-compliant project",
        "tm_settings": {
            "fuzzy_threshold": 70,
            "auto_insert_confidence": 85,
            "penalty_percentage": 25,
        },
        "backup": {
            "enabled": True,
            "interval_minutes": 5,
            "max_snapshots": 15,
        },
        "accessibility": {
            "theme": "Dark",
            "font_scale": 1.2,
            "colorblind_mode": "none",
        },
    }
    
    dialog = ProjectSettingsDialogV3(test_data)
    
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        print("Settings saved:")
        print(json.dumps(dialog.get_data(), indent=2))
    else:
        print("Dialog cancelled")

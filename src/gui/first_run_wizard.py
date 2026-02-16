from PyQt6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QRadioButton, 
                             QButtonGroup, QFormLayout)
from PyQt6.QtCore import Qt
import os
from src.core.config_manager import ConfigManager

class FirstRunWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad - Initial Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(600, 400)
        
        self.config = ConfigManager()
        
        # Pages
        self.addPage(WelcomePage())
        self.addPage(WorkspacePage(self.config))
        self.addPage(ThemePage(self.config))
        self.addPage(FinishPage())
        
        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        if result == QWizard.DialogCode.Accepted:
            self.config.set_first_run_complete()

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to NovelTrad")
        self.setSubTitle("The AI-powered translation tool for web novels.")
        
        layout = QVBoxLayout()
        label = QLabel("This wizard will help you configure the basic settings for your first use.\n\n"
                       "You can change these settings later in the application.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class WorkspacePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("Workspace Location")
        self.setSubTitle("Where should your projects be saved?")
        
        layout = QVBoxLayout()
        
        self.path_edit = QLineEdit(self.config.get("workspace_dir"))
        self.path_edit.setReadOnly(True)
        layout.addWidget(self.path_edit)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse)
        layout.addWidget(btn_browse)
        
        self.registerField("workspace", self.path_edit)
        self.setLayout(layout)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace Directory")
        if directory:
            self.path_edit.setText(directory)
            self.config.set("workspace_dir", directory)

class ThemePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("Interface Theme")
        self.setSubTitle("Choose your preferred visual style.")
        
        layout = QVBoxLayout()
        
        self.group = QButtonGroup()
        
        self.radio_dark = QRadioButton("Dark Mode (Recommended)")
        self.radio_light = QRadioButton("Light Mode")
        
        if self.config.get("theme") == "dark":
            self.radio_dark.setChecked(True)
        else:
            self.radio_light.setChecked(True)
            
        self.group.addButton(self.radio_dark)
        self.group.addButton(self.radio_light)
        
        self.radio_dark.toggled.connect(self.save_theme)
        
        layout.addWidget(self.radio_dark)
        layout.addWidget(self.radio_light)
        self.setLayout(layout)

    def save_theme(self):
        theme = "dark" if self.radio_dark.isChecked() else "light"
        self.config.set("theme", theme)

class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("You are ready to start translating!")
        
        layout = QVBoxLayout()
        label = QLabel("Click 'Finish' to launch the main application.")
        layout.addWidget(label)
        self.setLayout(layout)

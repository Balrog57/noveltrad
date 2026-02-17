from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QKeySequenceEdit, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

class ShortcutConfigDialog(QDialog):
    """
    Dialog to customize application keyboard shortcuts.
    Displays a list of actions and their current key sequences.
    """
    def __init__(self, shortcut_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration des Raccourcis")
        self.setMinimumSize(500, 600)
        self.shortcut_manager = shortcut_manager
        self.init_ui()
        self.load_shortcuts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Raccourcis Clavier")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action", "Raccourci"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { border: 1px solid #e2e8f0; border-radius: 4px; }")
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Réinitialiser par défaut")
        reset_btn.clicked.connect(self.reset_defaults)
        
        save_btn = QPushButton("Enregistrer")
        save_btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 8px 16px;")
        save_btn.clicked.connect(self.save_shortcuts)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def load_shortcuts(self):
        """Populates the table with current shortcuts."""
        self.table.setRowCount(0)
        # Using a list of keys to maintain order if needed, but dict is fine
        actions = sorted(self.shortcut_manager.shortcuts.keys())
        self.table.setRowCount(len(actions))
        
        for i, action_name in enumerate(actions):
            sequence = self.shortcut_manager.get(action_name)
            
            # Action Name Label
            name_label = action_name.replace("_", " ").title()
            name_item = QTableWidgetItem(name_label)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.UserRole, action_name) # Store the real key
            self.table.setItem(i, 0, name_item)
            
            # Key Sequence Edit
            key_edit = QKeySequenceEdit(QKeySequence(sequence))
            self.table.setCellWidget(i, 1, key_edit)

    def save_shortcuts(self):
        """Reads all values from the table and updates the manager."""
        for i in range(self.table.rowCount()):
            action_name = self.table.item(i, 0).data(Qt.ItemDataRole.UserRole)
            key_edit = self.table.cellWidget(i, 1)
            
            if isinstance(key_edit, QKeySequenceEdit):
                sequence_str = key_edit.keySequence().toString()
                self.shortcut_manager.set(action_name, sequence_str)
        
        self.shortcut_manager.save()
        QMessageBox.information(self, "Succès", "Raccourcis enregistrés. Redémarrez l'application ou rechargez le projet pour appliquer certains changements.")
        self.accept()

    def reset_defaults(self):
        """Resets the manager to defaults and reloads the table."""
        reply = QMessageBox.question(self, "Réinitialiser", 
                                   "Voulez-vous vraiment réinitialiser tous les raccourcis aux valeurs d'usine ?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.shortcut_manager.reset_to_defaults()
            self.load_shortcuts()

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QKeySequenceEdit,
    QWidget, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt

class ShortcutConfigDialog(QDialog):
    def __init__(self, shortcut_manager, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        self.setWindowTitle("Configuration des Raccourcis")
        self.resize(600, 500)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Catégorie", "Action", "Raccourci"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemDoubleClicked.connect(self.edit_selected_shortcut)
        
        layout.addWidget(self.table)
        
        # Edit Form
        edit_group = QGroupBox("Éditer la sélection")
        edit_layout = QHBoxLayout(edit_group)
        self.lbl_current_action = QLabel("Aucune action sélectionnée")
        self.key_edit = QKeySequenceEdit()
        self.key_edit.setEnabled(False)
        self.btn_apply = QPushButton("Appliquer")
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self.apply_shortcut)
        
        edit_layout.addWidget(self.lbl_current_action, 1)
        edit_layout.addWidget(self.key_edit, 1)
        edit_layout.addWidget(self.btn_apply)
        
        layout.addWidget(edit_group)
        
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_reset = QPushButton("Réinitialiser")
        self.btn_reset.clicked.connect(self.reset_defaults)
        
        self.btn_export = QPushButton("Exporter")
        self.btn_export.clicked.connect(self.export_shortcuts)
        
        self.btn_import = QPushButton("Importer")
        self.btn_import.clicked.connect(self.import_shortcuts)
        
        self.btn_save = QPushButton("Enregistrer et Fermer")
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setStyleSheet("background-color: #0d7ff2; color: white;")
        
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)

    def load_data(self):
        self.table.setRowCount(0)
        shortcuts = self.shortcut_manager.get_all_shortcuts()
        
        row = 0
        for category, bindings in shortcuts.items():
            for action_name, keyseq in bindings.items():
                self.table.insertRow(row)
                
                cat_item = QTableWidgetItem(category)
                act_item = QTableWidgetItem(action_name)
                key_item = QTableWidgetItem(keyseq)
                
                # Store original data in items user role
                act_item.setData(Qt.ItemDataRole.UserRole, action_name)
                
                self.table.setItem(row, 0, cat_item)
                self.table.setItem(row, 1, act_item)
                self.table.setItem(row, 2, key_item)
                row += 1

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.lbl_current_action.setText("Aucune action")
            self.key_edit.clear()
            self.key_edit.setEnabled(False)
            self.btn_apply.setEnabled(False)
            return
            
        row = selected[0].row()
        action_name = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        keyseq = self.table.item(row, 2).text()
        
        self.lbl_current_action.setText(action_name)
        from PyQt6.QtGui import QKeySequence
        self.key_edit.setKeySequence(QKeySequence(keyseq))
        self.key_edit.setEnabled(True)
        self.btn_apply.setEnabled(True)
        
    def edit_selected_shortcut(self, item):
        self.table.selectRow(item.row())
        self.key_edit.setFocus()

    def apply_shortcut(self):
        selected = self.table.selectedItems()
        if not selected: return
        
        row = selected[0].row()
        action_name = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        new_seq = self.key_edit.keySequence().toString()
        
        # Conflict detection
        shortcuts = self.shortcut_manager.get_all_shortcuts()
        conflict = None
        for cat, bindings in shortcuts.items():
            for act, seq in bindings.items():
                if seq == new_seq and act != action_name:
                    conflict = act
                    break
        
        if conflict:
            reply = QMessageBox.warning(
                self, "Conflit détecté",
                f"Le raccourci '{new_seq}' est déjà utilisé par '{conflict}'.\nVoulez-vous quand même l'assigner ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        self.shortcut_manager.set(action_name, new_seq)
        self.table.item(row, 2).setText(new_seq)
        QMessageBox.information(self, "Succès", "Raccourci mis à jour.")

    def reset_defaults(self):
        reply = QMessageBox.warning(
            self, "Réinitialiser",
            "Voulez-vous vraiment réinitialiser tous les raccourcis aux valeurs par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.shortcut_manager.reset_to_defaults()
            self.load_data()

    def export_shortcuts(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les raccourcis", "", "Fichiers TOML (*.toml)")
        if path:
            self.shortcut_manager.save_shortcuts_to_file(path)
            QMessageBox.information(self, "Succès", f"Raccourcis exportés vers {path}")

    def import_shortcuts(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer des raccourcis", "", "Fichiers TOML (*.toml)")
        if path:
            self.shortcut_manager.load_shortcuts_from_file(path)
            self.load_data()
            self.shortcut_manager.save_shortcuts_to_file(self.shortcut_manager.config_path)
            QMessageBox.information(self, "Succès", "Raccourcis importés avec succès.")

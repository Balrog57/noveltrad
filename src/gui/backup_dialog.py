import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QListWidgetItem, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt

class BackupDialog(QDialog):
    """
    Dialog to manage project snapshots/backups.
    Allows users to see history, create manual snapshots, and restore.
    """
    def __init__(self, backup_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des Snapshots")
        self.setMinimumSize(500, 400)
        self.backup_manager = backup_manager
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Historique des versions du projet")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        layout.addWidget(title)
        
        desc = QLabel("Sélectionnez une version pour la restaurer. Attention : la restauration écrasera les données actuelles.")
        desc.setStyleSheet("color: #64748b; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QListWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
                border-radius: 4px;
            }
        """)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("Restaurer cette version")
        self.restore_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; padding: 8px 16px;")
        self.restore_btn.clicked.connect(self.restore_selected)
        self.restore_btn.setEnabled(False)
        
        self.snapshot_btn = QPushButton("+ Nouveau Snapshot")
        self.snapshot_btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 8px 16px;")
        self.snapshot_btn.clicked.connect(self.create_manual_snapshot)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.snapshot_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def refresh_list(self):
        """Refresh the list of available snapshots."""
        self.list_widget.clear()
        snapshots = self.backup_manager.list_snapshots()
        
        if not snapshots:
            self.list_widget.addItem("Aucun snapshot disponible.")
            return

        for s in snapshots:
            # Format: 2024-02-17 14:30 - Label (1.2 MB)
            display_text = f"{s['timestamp']} — {s['label'].upper()}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, s['path'])
            
            # Subtitle with file info
            size_mb = os.path.getsize(s['path']) / (1024 * 1024)
            item.setToolTip(f"Chemin: {s['path']}\nTaille: {size_mb:.2f} MB")
            
            self.list_widget.addItem(item)

    def _on_selection_changed(self):
        """Enable restore button only if a valid snapshot is selected."""
        items = self.list_widget.selectedItems()
        if not items:
            self.restore_btn.setEnabled(False)
            return
            
        path = items[0].data(Qt.ItemDataRole.UserRole)
        self.restore_btn.setEnabled(path is not None)

    def create_manual_snapshot(self):
        """Prompt for a label and create a snapshot."""
        label, ok = QInputDialog.getText(self, "Nouveau Snapshot", "Nom/Label pour cette version :")
        if ok and label:
            path = self.backup_manager.create_snapshot(label=label)
            if path:
                self.refresh_list()
                QMessageBox.information(self, "Succès", f"Snapshot '{label}' créé.")

    def restore_selected(self):
        """Restore the selected snapshot."""
        items = self.list_widget.selectedItems()
        if not items: return
        
        path = items[0].data(Qt.ItemDataRole.UserRole)
        label = items[0].text()
        
        reply = QMessageBox.question(
            self, "Confirmer la restauration",
            f"Voulez-vous vraiment restaurer la version :\n{label} ?\n\n"
            "Toutes les modifications non sauvegardées dans la version actuelle seront perdues.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Create a safety backup of current state before restoring
                self.backup_manager.create_snapshot(label="pre-restore-safety")
                
                success = self.backup_manager.restore_snapshot(path)
                if success:
                    QMessageBox.information(self, "Succès", "Restauration terminée. L'application va maintenant recharger le projet.")
                    self.accept() # Close dialog and signal success
                else:
                    QMessageBox.critical(self, "Erreur", "La restauration a échoué.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la restauration : {str(e)}")

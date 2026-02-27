from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, 
    QTreeWidgetItem, QApplication, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

class ShortcutHelpDialog(QDialog):
    def __init__(self, shortcut_manager, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        self.setWindowTitle("Aide - Raccourcis Clavier")
        self.resize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Action", "Raccourci"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
        shortcuts = self.shortcut_manager.get_all_shortcuts()
        
        for category, bindings in shortcuts.items():
            cat_item = QTreeWidgetItem([category.capitalize(), ""])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            
            # Make category bold
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            
            for action_name, keyseq in bindings.items():
                act_item = QTreeWidgetItem([action_name, keyseq])
                cat_item.addChild(act_item)
                
            self.tree.addTopLevelItem(cat_item)
            
        self.tree.expandAll()
        layout.addWidget(self.tree)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton("Copier dans le presse-papier")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        
        self.btn_close = QPushButton("Fermer")
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        text = "Raccourcis Clavier NovelTrad:\n\n"
        shortcuts = self.shortcut_manager.get_all_shortcuts()
        for category, bindings in shortcuts.items():
            text += f"[{category.capitalize()}]\n"
            for act, seq in bindings.items():
                text += f"{act}: {seq}\n"
            text += "\n"
            
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copié", "Les raccourcis ont été copiés dans le presse-papier.")

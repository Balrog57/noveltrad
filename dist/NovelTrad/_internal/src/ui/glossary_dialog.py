from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QMessageBox, QFileDialog
)
from src.core.glossary_manager import GlossaryManager

class GlossaryDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Glossaire du Projet: {project.name}")
        self.resize(800, 600)
        self.manager = GlossaryManager(project)
        self.init_ui()
        self.load_terms()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        layout.addWidget(QLabel("Termes spécifiques à ce projet (Prioritaire sur le dictionnaire global)"))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Terme Source", "Traduction", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.hideColumn(0) # Hide ID
        layout.addWidget(self.table)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.src_input = QLineEdit()
        self.src_input.setPlaceholderText("Terme Source")
        self.tgt_input = QLineEdit()
        self.tgt_input.setPlaceholderText("Traduction")
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Catégorie (ex: Personnage)")
        
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self.add_term)
        
        input_layout.addWidget(self.src_input)
        input_layout.addWidget(self.tgt_input)
        input_layout.addWidget(self.cat_input)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # Actions
        action_layout = QHBoxLayout()
        del_btn = QPushButton("Supprimer Sélection")
        del_btn.clicked.connect(self.delete_term)
        
        import_btn = QPushButton("Importer CSV...")
        import_btn.clicked.connect(self.import_csv)
        
        action_layout.addWidget(del_btn)
        action_layout.addStretch()
        action_layout.addWidget(import_btn)
        
        layout.addLayout(action_layout)

    def load_terms(self):
        terms = self.manager.get_all()
        self.table.setRowCount(len(terms))
        for i, term in enumerate(terms):
            self.table.setItem(i, 0, QTableWidgetItem(str(term.id)))
            self.table.setItem(i, 1, QTableWidgetItem(term.source_term))
            self.table.setItem(i, 2, QTableWidgetItem(term.target_term))
            self.table.setItem(i, 3, QTableWidgetItem(term.category))

    def add_term(self):
        src_term = self.src_input.text().strip()
        tgt_term = self.tgt_input.text().strip()
        cat = self.cat_input.text().strip() or "general"
        
        if not src_term or not tgt_term:
            return
            
        self.manager.add_term(src_term, tgt_term, cat)
        self.src_input.clear()
        self.tgt_input.clear()
        self.load_terms()

    def delete_term(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
            
        for row in rows:
            term_id = int(self.table.item(row, 0).text())
            self.manager.delete_term(term_id)
            
        self.load_terms()

    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importer CSV", "", "CSV Files (*.csv)")
        if file_path:
            count = self.manager.import_csv(file_path)
            QMessageBox.information(self, "Import", f"{count} termes importés.")
            self.load_terms()

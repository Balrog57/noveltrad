from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QMessageBox, QFileDialog
)
from src.core.dictionary_manager import DictionaryManager

class DictionaryDialog(QDialog):
    def __init__(self, parent=None, initial_src="en", initial_tgt="fr"):
        super().__init__(parent)
        self.setWindowTitle("Dictionnaire Global")
        self.resize(800, 600)
        self.manager = DictionaryManager()
        self.initial_src = initial_src
        self.initial_tgt = initial_tgt
        self.init_ui()
        self.load_terms()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        self.src_combo = QComboBox()
        self.src_combo.addItems(["en", "zh", "fr", "de", "ja", "es", "it"])
        self.src_combo.setCurrentText(self.initial_src)
        self.src_combo.currentTextChanged.connect(self.load_terms)
        
        self.tgt_combo = QComboBox()
        self.tgt_combo.addItems(["fr", "en", "de", "es", "it"])
        self.tgt_combo.setCurrentText(self.initial_tgt)
        self.tgt_combo.currentTextChanged.connect(self.load_terms)
        
        filter_layout.addWidget(QLabel("Source:"))
        filter_layout.addWidget(self.src_combo)
        filter_layout.addWidget(QLabel("Cible:"))
        filter_layout.addWidget(self.tgt_combo)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Terme Source", "Traduction", "Contexte"])
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
        
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self.add_term)
        
        input_layout.addWidget(self.src_input)
        input_layout.addWidget(self.tgt_input)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # Database Actions
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
        src = self.src_combo.currentText()
        tgt = self.tgt_combo.currentText()
        terms = self.manager.get_all(src, tgt)
        
        self.table.setRowCount(len(terms))
        for i, term in enumerate(terms):
            self.table.setItem(i, 0, QTableWidgetItem(str(term.id)))
            self.table.setItem(i, 1, QTableWidgetItem(term.source_term))
            self.table.setItem(i, 2, QTableWidgetItem(term.target_term))
            self.table.setItem(i, 3, QTableWidgetItem(term.context or ""))

    def add_term(self):
        src_term = self.src_input.text().strip()
        tgt_term = self.tgt_input.text().strip()
        
        if not src_term or not tgt_term:
            return
            
        src_lang = self.src_combo.currentText()
        tgt_lang = self.tgt_combo.currentText()
        
        self.manager.add_term(src_lang, tgt_lang, src_term, tgt_term)
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
            src = self.src_combo.currentText()
            tgt = self.tgt_combo.currentText()
            count = self.manager.import_csv(file_path, src, tgt)
            QMessageBox.information(self, "Import", f"{count} termes importés.")
            self.load_terms()

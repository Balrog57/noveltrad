from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QCheckBox, QSpinBox, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget, QSplitter
)
from PyQt6.QtCore import Qt
from src.core.database import GlossaryTerm
import json

class GlossaryEditorDialog(QDialog):
    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Manage Glossary")
        self.resize(900, 600)
        self.current_term_id = None
        self.init_ui()
        self.load_terms()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Splitter: List (Left) | Editor (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel: List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search terms...")
        self.search_input.textChanged.connect(self.filter_terms)
        left_layout.addWidget(self.search_input)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Source", "Target", "Category", "Priority"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.table)
        
        # Buttons (Left)
        left_btns = QHBoxLayout()
        self.btn_new = QPushButton("New Term")
        self.btn_new.clicked.connect(self.clear_form)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_term)
        self.btn_delete.setEnabled(False)
        left_btns.addWidget(self.btn_new)
        left_btns.addWidget(self.btn_delete)
        left_layout.addLayout(left_btns)
        
        splitter.addWidget(left_widget)
        
        # Right Panel: Form
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.lbl_id = QLabel("New Term")
        self.lbl_id.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.lbl_id)
        
        # Fields
        right_layout.addWidget(QLabel("Source Term:"))
        self.inp_source = QLineEdit()
        right_layout.addWidget(self.inp_source)
        
        right_layout.addWidget(QLabel("Target Term:"))
        self.inp_target = QLineEdit()
        right_layout.addWidget(self.inp_target)
        
        right_layout.addWidget(QLabel("Category:"))
        self.inp_category = QLineEdit()
        self.inp_category.setPlaceholderText("general, name, location, etc.")
        right_layout.addWidget(self.inp_category)
        
        right_layout.addWidget(QLabel("Variants (comma separated):"))
        self.inp_variants = QLineEdit()
        right_layout.addWidget(self.inp_variants)
        
        right_layout.addWidget(QLabel("Notes:"))
        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(80)
        right_layout.addWidget(self.inp_notes)
        
        # Options
        opts_layout = QHBoxLayout()
        self.chk_case = QCheckBox("Case Sensitive")
        self.chk_case.setChecked(True)
        opts_layout.addWidget(self.chk_case)
        
        opts_layout.addWidget(QLabel("Priority:"))
        self.spin_priority = QSpinBox()
        self.spin_priority.setRange(0, 100)
        self.spin_priority.setValue(10)
        opts_layout.addWidget(self.spin_priority)
        opts_layout.addStretch()
        right_layout.addLayout(opts_layout)
        
        right_layout.addStretch()
        
        # Save Button
        self.btn_save = QPushButton("Save Term")
        self.btn_save.clicked.connect(self.save_term)
        self.btn_save.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px; font-weight: bold;")
        right_layout.addWidget(self.btn_save)
        
        splitter.addWidget(right_widget)
        
        # Set sizes (Left 60%, Right 40%)
        splitter.setSizes([500, 300])
        
        layout.addWidget(splitter)
        

    def load_terms(self):
        if not self.project: return
        
        self.table.setRowCount(0)
        query = self.search_input.text().lower()
        
        # Simple filter in memory for now, or update DB query
        terms = list(GlossaryTerm.select().where(GlossaryTerm.project == self.project))
        
        # Sort by priority desc
        terms.sort(key=lambda x: x.priority, reverse=True)
        
        for term in terms:
            if query and query not in term.source_term.lower() and query not in term.target_term.lower():
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(term.source_term))
            self.table.setItem(row, 1, QTableWidgetItem(term.target_term))
            self.table.setItem(row, 2, QTableWidgetItem(term.category))
            self.table.setItem(row, 3, QTableWidgetItem(str(term.priority)))
            
            # Store ID in hidden data
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, term.id)
            
    def filter_terms(self):
        self.load_terms()

    def on_selection_changed(self):
        items = self.table.selectedItems()
        if not items:
            self.clear_form()
            self.btn_delete.setEnabled(False)
            return
            
        self.btn_delete.setEnabled(True)
        # Get row of selected item to get the ID from column 0
        row = items[0].row()
        term_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.load_term_details(term_id)

    def load_term_details(self, term_id):
        try:
            term = GlossaryTerm.get_by_id(term_id)
            self.current_term_id = term.id
            self.lbl_id.setText(f"Editing Term #{term.id}")
            self.inp_source.setText(term.source_term)
            self.inp_target.setText(term.target_term)
            self.inp_category.setText(term.category)
            self.inp_notes.setPlainText(term.notes or "")
            self.spin_priority.setValue(term.priority)
            self.chk_case.setChecked(term.case_sensitive)
            
            # Variants
            if term.variants:
                try:
                    variants_list = json.loads(term.variants)
                    self.inp_variants.setText(", ".join(variants_list))
                except:
                    self.inp_variants.setText("")
            else:
                self.inp_variants.setText("")
                
        except:
            self.clear_form()

    def clear_form(self):
        self.current_term_id = None
        self.lbl_id.setText("New Term")
        self.inp_source.clear()
        self.inp_target.clear()
        self.inp_category.setText("general")
        self.inp_notes.clear()
        self.inp_variants.clear()
        self.spin_priority.setValue(10)
        self.chk_case.setChecked(True)
        self.table.clearSelection()
        self.btn_delete.setEnabled(False)

    def save_term(self):
        if not self.project: return
        
        source = self.inp_source.text().strip()
        target = self.inp_target.text().strip()
        
        if not source or not target:
            QMessageBox.warning(self, "Error", "Source and Target terms are required.")
            return
            
        category = self.inp_category.text().strip() or "general"
        notes = self.inp_notes.toPlainText().strip() or None
        priority = self.spin_priority.value()
        case_sensitive = self.chk_case.isChecked()
        
        variants_str = self.inp_variants.text().strip()
        variants = [v.strip() for v in variants_str.split(',') if v.strip()] if variants_str else None
        
        try:
            if self.current_term_id:
                # Update
                term = GlossaryTerm.get_by_id(self.current_term_id)
                term.source_term = source
                term.target_term = target
                term.category = category
                term.notes = notes
                term.priority = priority
                term.case_sensitive = case_sensitive
                term.variants = json.dumps(variants) if variants else None
                term.save()
            else:
                # Create
                GlossaryTerm.create(
                    project=self.project,
                    source_term=source,
                    target_term=target,
                    category=category,
                    notes=notes,
                    priority=priority,
                    case_sensitive=case_sensitive,
                    variants=json.dumps(variants) if variants else None,
                    source='manual'
                )
            
            self.load_terms()
            self.clear_form()
            QMessageBox.information(self, "Success", "Term saved.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save term: {e}")

    def delete_term(self):
        if not self.current_term_id: return
        
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this term?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.Yes:
            try:
                GlossaryTerm.delete_by_id(self.current_term_id)
                self.load_terms()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

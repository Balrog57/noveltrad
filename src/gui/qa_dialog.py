"""
Dialog de QA Check pour NovelTrad.
Affiche les résultats de l'assurance qualité avant export.
Conforme au cahier des charges §12.9.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from src.core.qa_checker import QAChecker


class QADialog(QDialog):
    """Dialog for running and displaying QA check results."""

    # Signal emitted when user double-clicks a segment to navigate to it
    navigate_to_segment = pyqtSignal(int)  # segment_id

    def __init__(self, parent=None, segments=None, glossary_terms=None):
        super().__init__(parent)
        self.setWindowTitle("Assurance Qualité (QA Check)")
        self.setMinimumSize(800, 500)
        self.segments = segments or []
        self.glossary_terms = glossary_terms or []
        self.qa_checker = QAChecker()
        self.issues = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Check options
        options_group = QGroupBox("Vérifications")
        options_layout = QHBoxLayout()

        self.chk_tags = QCheckBox("Balises")
        self.chk_tags.setChecked(True)
        self.chk_numbers = QCheckBox("Nombres")
        self.chk_numbers.setChecked(True)
        self.chk_glossary = QCheckBox("Glossaire")
        self.chk_glossary.setChecked(True)
        self.chk_empty = QCheckBox("Segments vides")
        self.chk_empty.setChecked(True)
        self.chk_punct = QCheckBox("Ponctuation")
        self.chk_punct.setChecked(True)

        for chk in [self.chk_tags, self.chk_numbers, self.chk_glossary,
                     self.chk_empty, self.chk_punct]:
            options_layout.addWidget(chk)

        run_btn = QPushButton("▶ Lancer le QA Check")
        run_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 16px; font-weight: bold;")
        run_btn.clicked.connect(self._run_qa)
        options_layout.addWidget(run_btn)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Summary
        self.summary_label = QLabel("Aucune vérification effectuée.")
        self.summary_label.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.summary_label)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Seg #", "Type", "Sévérité", "Message", "Source"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 80)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _run_qa(self):
        """Run QA checks with selected options."""
        self.issues = self.qa_checker.run_checks(
            self.segments,
            glossary_terms=self.glossary_terms,
            check_tags=self.chk_tags.isChecked(),
            check_numbers=self.chk_numbers.isChecked(),
            check_glossary=self.chk_glossary.isChecked(),
            check_empty=self.chk_empty.isChecked(),
            check_punctuation=self.chk_punct.isChecked(),
        )

        self._update_table()
        summary = self.qa_checker.get_summary(self.issues)
        self.summary_label.setText(
            f"✅ {summary['total']} problème(s) trouvé(s) — "
            f"🔴 {summary['by_severity'].get('error', 0)} erreur(s), "
            f"🟡 {summary['by_severity'].get('warning', 0)} avertissement(s), "
            f"ℹ️ {summary['by_severity'].get('info', 0)} info(s)"
        )

    def _update_table(self):
        """Update the results table with QA issues."""
        self.table.setRowCount(len(self.issues))

        severity_colors = {
            'error': QColor("#ef4444"),
            'warning': QColor("#f59e0b"),
            'info': QColor("#3b82f6"),
        }

        type_labels = {
            'missing_tag': "Balise manquante",
            'extra_tag': "Balise en trop",
            'number_mismatch': "Incohérence nombres",
            'glossary_violation': "Glossaire non respecté",
            'empty_translation': "Segment vide",
            'punctuation_mismatch': "Ponctuation",
        }

        for row, issue in enumerate(self.issues):
            seg_item = QTableWidgetItem(str(issue.segment_index + 1))
            type_item = QTableWidgetItem(type_labels.get(issue.issue_type, issue.issue_type))
            sev_item = QTableWidgetItem(issue.severity.upper())
            msg_item = QTableWidgetItem(issue.message)
            src_item = QTableWidgetItem(issue.source_text[:80] + "…" if len(issue.source_text) > 80 else issue.source_text)

            color = severity_colors.get(issue.severity, QColor("#94a3b8"))
            sev_item.setForeground(color)
            type_item.setForeground(color)

            self.table.setItem(row, 0, seg_item)
            self.table.setItem(row, 1, type_item)
            self.table.setItem(row, 2, sev_item)
            self.table.setItem(row, 3, msg_item)
            self.table.setItem(row, 4, src_item)

    def _on_double_click(self, index):
        """Navigate to the segment when double-clicked."""
        row = index.row()
        if 0 <= row < len(self.issues):
            seg_id = self.issues[row].segment_id
            self.navigate_to_segment.emit(seg_id)

    def set_segments(self, segments, glossary_terms=None):
        """Update the segments and glossary for QA checking."""
        self.segments = segments or []
        self.glossary_terms = glossary_terms or []

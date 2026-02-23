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
import fitz  # PyMuPDF
import os


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
        
        self.export_btn = QPushButton("Exporter HTML")
        self.export_btn.clicked.connect(self._export_html)
        self.export_btn.setEnabled(False) 
        btn_layout.addWidget(self.export_btn)
        
        self.export_pdf_btn = QPushButton("Exporter PDF")
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        self.export_pdf_btn.setEnabled(False)
        btn_layout.addWidget(self.export_pdf_btn)
        
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
        has_issues = len(self.issues) > 0
        self.export_btn.setEnabled(has_issues)
        self.export_pdf_btn.setEnabled(has_issues)
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

    def _export_html(self):
        """Export the current QA issues as an HTML report."""
        if not self.issues:
            return

        from PyQt6.QtWidgets import QFileDialog
        import os

        fname, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport QA", 
            "rapport_qa.html", 
            "Fichiers HTML (*.html)"
        )
        
        if fname:
            try:
                html = self._generate_html_report()
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(html)
                QMessageBox.information(self, "Export", f"Rapport exporté avec succès :\n{os.path.basename(fname)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export : {str(e)}")

    def _generate_html_report(self):
        """Generate HTML content for the QA report."""
        summary = self.qa_checker.get_summary(self.issues)
        
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport d'Assurance Qualité - NovelTrad</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f4f7f9; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .header-info {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
        .card.error {{ border-top: 4px solid #ef4444; }}
        .card.warning {{ border-top: 4px solid #f59e0b; }}
        .card.info {{ border-top: 4px solid #3b82f6; }}
        .card h3 {{ margin-top: 0; color: #7f8c8d; font-size: 0.8em; text-transform: uppercase; }}
        .card .value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e1e7ec; }}
        th {{ background-color: #34495e; color: white; text-transform: uppercase; font-size: 0.85em; }}
        tr:hover {{ background-color: #f8fbff; }}
        
        .severity {{ font-weight: bold; text-transform: uppercase; font-size: 0.8em; padding: 3px 8px; border-radius: 4px; }}
        .severity-error {{ background: #fee2e2; color: #ef4444; }}
        .severity-warning {{ background: #fef3c7; color: #d97706; }}
        .severity-info {{ background: #dbeafe; color: #3b82f6; }}
        
        .source-text {{ color: #64748b; font-size: 0.9em; font-style: italic; }}
        .target-text {{ font-weight: 500; }}
        footer {{ margin-top: 30px; text-align: center; color: #95a5a6; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>Rapport d'Assurance Qualité NovelTrad</h1>
    
    <div class="header-info">
        <div class="card error">
            <h3>Erreurs</h3>
            <div class="value">{summary['by_severity'].get('error', 0)}</div>
        </div>
        <div class="card warning">
            <h3>Avertissements</h3>
            <div class="value">{summary['by_severity'].get('warning', 0)}</div>
        </div>
        <div class="card info">
            <h3>Infos</h3>
            <div class="value">{summary['by_severity'].get('info', 0)}</div>
        </div>
        <div class="card">
            <h3>Total Problèmes</h3>
            <div class="value">{summary['total']}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 50px;">#</th>
                <th style="width: 150px;">Type</th>
                <th style="width: 100px;">Sévérité</th>
                <th>Message</th>
                <th>Texte (Source & Cible)</th>
            </tr>
        </thead>
        <tbody>
"""
        for issue in self.issues:
            sev_class = f"severity-{issue.severity}"
            html += f"""
            <tr>
                <td>{issue.segment_index + 1}</td>
                <td>{issue.issue_type}</td>
                <td><span class="severity {sev_class}">{issue.severity}</span></td>
                <td>{issue.message}</td>
                <td>
                    <div class="source-text">{issue.source_text}</div>
                    <div class="target-text">{issue.target_text}</div>
                </td>
            </tr>
"""
        html += """
        </tbody>
    </table>
    
    <footer>Généré par NovelTrad v2.0</footer>
</body>
</html>
"""
        return html
    def _export_pdf(self):
        """Export the current QA issues as a PDF report."""
        if not self.issues:
            return

        from PyQt6.QtWidgets import QFileDialog

        fname, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport QA (PDF)", 
            "rapport_qa.pdf", 
            "Fichiers PDF (*.pdf)"
        )
        
        if fname:
            try:
                self._generate_pdf_report(fname)
                QMessageBox.information(self, "Export", f"Rapport PDF exporté avec succès :\n{os.path.basename(fname)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export PDF : {str(e)}")

    def _generate_pdf_report(self, output_path):
        """Generate a PDF report using PyMuPDF."""
        doc = fitz.open()
        
        # Style constants
        margin = 50
        width = 595 - 2*margin
        height = 842 - 2*margin
        
        page = doc.new_page()
        y = margin
        
        # Title
        page.insert_text((margin, y), "Rapport d'Assurance Qualité NovelTrad", fontsize=18, fontname="helv-bold", color=(0.17, 0.24, 0.31))
        y += 40
        
        # Summary
        summary = self.qa_checker.get_summary(self.issues)
        page.insert_text((margin, y), f"Total problèmes : {summary['total']}", fontsize=12, fontname="helv-bold")
        y += 20
        page.insert_text((margin, y), f"Erreurs : {summary['by_severity'].get('error', 0)} | Avertissements : {summary['by_severity'].get('warning', 0)} | Infos : {summary['by_severity'].get('info', 0)}", fontsize=10)
        y += 40
        
        # Table Header
        headers = ["Seg #", "Type", "Sév.", "Message"]
        col_widths = [40, 100, 50, 300]
        curr_x = margin
        for i, h in enumerate(headers):
            page.insert_text((curr_x, y), h, fontsize=10, fontname="helv-bold")
            curr_x += col_widths[i]
        
        y += 5
        page.draw_line((margin, y), (margin + sum(col_widths), y), color=(0.5, 0.5, 0.5), width=0.5)
        y += 15
        
        severity_colors = {
            'error': (0.9, 0.2, 0.2),
            'warning': (0.9, 0.6, 0.1),
            'info': (0.2, 0.5, 0.9),
        }
        
        for issue in self.issues:
            if y > height - 60: # Page break
                page = doc.new_page()
                y = margin
                # Redraw Header on new page
                curr_x = margin
                for i, h in enumerate(headers):
                    page.insert_text((curr_x, y), h, fontsize=10, fontname="helv-bold")
                    curr_x += col_widths[i]
                y += 20
            
            curr_x = margin
            page.insert_text((curr_x, y), str(issue.segment_index + 1), fontsize=9)
            curr_x += col_widths[0]
            
            page.insert_text((curr_x, y), issue.issue_type, fontsize=9)
            curr_x += col_widths[1]
            
            sev_color = severity_colors.get(issue.severity, (0, 0, 0))
            page.insert_text((curr_x, y), issue.severity.upper(), fontsize=9, color=sev_color, fontname="helv-bold")
            curr_x += col_widths[2]
            
            # Wrap message if too long
            msg = issue.message
            if len(msg) > 65: msg = msg[:62] + "..."
            page.insert_text((curr_x, y), msg, fontsize=9)
            
            y += 18
            
        doc.save(output_path)
        doc.close()

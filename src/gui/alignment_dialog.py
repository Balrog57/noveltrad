"""
Dialog d'alignement pour NovelTrad.
Interface visuelle pour aligner deux fichiers (source + traduction existante)
et exporter les paires en TMX.
Conforme au cahier des charges §13.3.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QProgressBar, QSplitter, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from src.core.aligner import Aligner
from src.core.segmenter import Segmenter


class AlignmentDialog(QDialog):
    """Dialog for aligning source and target files to create TM entries."""

    def __init__(self, parent=None, project_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Outil d'Alignement")
        self.setMinimumSize(900, 600)
        self.project_manager = project_manager
        self.aligner = Aligner()
        self.pairs = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # File selection area
        file_layout = QHBoxLayout()

        # Source file
        src_group = QVBoxLayout()
        src_group.addWidget(QLabel("Fichier source :"))
        src_row = QHBoxLayout()
        self.src_label = QLabel("Aucun fichier sélectionné")
        self.src_label.setStyleSheet("color: #94a3b8; padding: 4px;")
        src_btn = QPushButton("Parcourir…")
        src_btn.clicked.connect(self._select_source)
        src_row.addWidget(self.src_label, 1)
        src_row.addWidget(src_btn)
        src_group.addLayout(src_row)
        file_layout.addLayout(src_group)

        # Target file
        tgt_group = QVBoxLayout()
        tgt_group.addWidget(QLabel("Fichier cible (traduction) :"))
        tgt_row = QHBoxLayout()
        self.tgt_label = QLabel("Aucun fichier sélectionné")
        self.tgt_label.setStyleSheet("color: #94a3b8; padding: 4px;")
        tgt_btn = QPushButton("Parcourir…")
        tgt_btn.clicked.connect(self._select_target)
        tgt_row.addWidget(self.tgt_label, 1)
        tgt_row.addWidget(tgt_btn)
        tgt_group.addLayout(tgt_row)
        file_layout.addLayout(tgt_group)

        layout.addLayout(file_layout)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Langue source :"))
        self.src_lang_combo = QComboBox()
        self.src_lang_combo.addItems(['en', 'fr', 'zh', 'ja', 'ko', 'de', 'es', 'ru'])
        lang_layout.addWidget(self.src_lang_combo)
        lang_layout.addWidget(QLabel("Langue cible :"))
        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.addItems(['fr', 'en', 'zh', 'ja', 'ko', 'de', 'es', 'ru'])
        lang_layout.addWidget(self.tgt_lang_combo)

        align_btn = QPushButton("🔗 Aligner")
        align_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 16px; font-weight: bold;")
        align_btn.clicked.connect(self._run_alignment)
        lang_layout.addWidget(align_btn)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Source", "Cible", "Confiance"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 80)
        layout.addWidget(self.table, 1)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.info_label)

        # Action buttons
        btn_layout = QHBoxLayout()

        merge_btn = QPushButton("Fusionner segments")
        merge_btn.setToolTip("Fusionner les segments sélectionnés")
        merge_btn.clicked.connect(self._merge_segments)
        btn_layout.addWidget(merge_btn)

        split_btn = QPushButton("Diviser segment")
        split_btn.setToolTip("Diviser le segment sélectionné en deux")
        split_btn.clicked.connect(self._split_segment)
        btn_layout.addWidget(split_btn)

        btn_layout.addStretch()

        export_btn = QPushButton("💾 Exporter en TMX")
        export_btn.setStyleSheet("background-color: #22c55e; color: white; padding: 6px 16px; font-weight: bold;")
        export_btn.clicked.connect(self._export_tmx)
        btn_layout.addWidget(export_btn)

        add_tm_btn = QPushButton("📥 Ajouter à la TM")
        add_tm_btn.setStyleSheet("background-color: #8b5cf6; color: white; padding: 6px 16px; font-weight: bold;")
        add_tm_btn.clicked.connect(self._add_to_tm)
        btn_layout.addWidget(add_tm_btn)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.source_text = ""
        self.target_text = ""

    def _select_source(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner le fichier source",
            "", "Fichiers texte (*.txt);;Tous (*)"
        )
        if fname:
            self.src_label.setText(fname)
            with open(fname, 'r', encoding='utf-8') as f:
                self.source_text = f.read()

    def _select_target(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner le fichier cible",
            "", "Fichiers texte (*.txt);;Tous (*)"
        )
        if fname:
            self.tgt_label.setText(fname)
            with open(fname, 'r', encoding='utf-8') as f:
                self.target_text = f.read()

    def _run_alignment(self):
        if not self.source_text or not self.target_text:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner les deux fichiers.")
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate

        src_lang = self.src_lang_combo.currentText()
        tgt_lang = self.tgt_lang_combo.currentText()

        self.pairs = self.aligner.align(
            self.source_text, self.target_text,
            src_lang=src_lang, tgt_lang=tgt_lang
        )

        self._update_table()
        self.progress.setVisible(False)
        self.info_label.setText(f"{len(self.pairs)} paire(s) alignée(s)")

    def _update_table(self):
        self.table.setRowCount(len(self.pairs))
        for row, pair in enumerate(self.pairs):
            src_item = QTableWidgetItem(pair.source)
            tgt_item = QTableWidgetItem(pair.target)
            conf_item = QTableWidgetItem(f"{pair.confidence:.0%}")

            # Color-code by confidence
            if pair.confidence >= 0.8:
                conf_item.setForeground(QColor("#22c55e"))
            elif pair.confidence >= 0.5:
                conf_item.setForeground(QColor("#f59e0b"))
            else:
                conf_item.setForeground(QColor("#ef4444"))

            self.table.setItem(row, 0, src_item)
            self.table.setItem(row, 1, tgt_item)
            self.table.setItem(row, 2, conf_item)

    def _merge_segments(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if len(rows) < 2:
            QMessageBox.information(self, "Info", "Sélectionnez au moins 2 lignes à fusionner.")
            return

        # Merge selected pairs
        first = rows[0]
        merged_src = ' '.join(self.pairs[r].source for r in rows)
        merged_tgt = ' '.join(self.pairs[r].target for r in rows)

        from src.core.aligner import AlignedPair
        merged = AlignedPair(
            source=merged_src,
            target=merged_tgt,
            confidence=min(self.pairs[r].confidence for r in rows),
            source_indices=[],
            target_indices=[],
        )

        # Replace rows with merged
        for r in reversed(rows):
            self.pairs.pop(r)
        self.pairs.insert(first, merged)
        self._update_table()

    def _split_segment(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez un segment à diviser.")
            return

        pair = self.pairs[row]
        segmenter = Segmenter()

        src_segs = segmenter.segment(pair.source)
        tgt_segs = segmenter.segment(pair.target)

        if len(src_segs) <= 1 and len(tgt_segs) <= 1:
            QMessageBox.information(self, "Info", "Ce segment ne peut pas être divisé davantage.")
            return

        # Simple split: divide source and target evenly
        from src.core.aligner import AlignedPair
        self.pairs.pop(row)
        max_segs = max(len(src_segs), len(tgt_segs))
        for i in range(max_segs):
            s = src_segs[i] if i < len(src_segs) else ''
            t = tgt_segs[i] if i < len(tgt_segs) else ''
            self.pairs.insert(row + i, AlignedPair(
                source=s, target=t,
                confidence=0.5,
                source_indices=[], target_indices=[]
            ))

        self._update_table()

    def _export_tmx(self):
        if not self.pairs:
            QMessageBox.warning(self, "Erreur", "Aucune paire à exporter.")
            return

        fname, _ = QFileDialog.getSaveFileName(
            self, "Exporter en TMX", "", "Fichiers TMX (*.tmx)"
        )
        if fname:
            from src.core.tmx_handler import TMXHandler
            src_lang = self.src_lang_combo.currentText()
            tgt_lang = self.tgt_lang_combo.currentText()

            # Create mock segments for TMXHandler
            class MockSeg:
                def __init__(self, src, tgt):
                    self.source_text = src
                    self.target_text = tgt

            mock_segs = [MockSeg(p.source, p.target) for p in self.pairs]
            TMXHandler.export_tmx(mock_segs, src_lang, tgt_lang, fname)
            QMessageBox.information(self, "Succès", f"{len(self.pairs)} paire(s) exportée(s).")

    def _add_to_tm(self):
        if not self.pairs or not self.project_manager:
            QMessageBox.warning(self, "Erreur", "Aucune paire ou pas de projet ouvert.")
            return

        count = 0
        for pair in self.pairs:
            if pair.source and pair.target:
                self.project_manager.add_to_tm(pair.source, pair.target)
                count += 1

        QMessageBox.information(self, "Succès", f"{count} paire(s) ajoutée(s) à la TM.")

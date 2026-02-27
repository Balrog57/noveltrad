"""
Dialog d'alignement pour NovelTrad (AlignmentDialog++).
Interface visuelle 3 colonnes pour aligner deux fichiers (source + traduction existante).
Conforme au cahier des charges §13.3.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QProgressBar, QSplitter, QWidget,
    QToolBar, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut

from src.core.aligner import Aligner
from src.core.segmenter import Segmenter
from src.utils.tag_utils import validate_tags

class AlignmentDialog(QDialog):
    """Dialog for aligning source and target files to create TM entries."""

    def __init__(self, parent=None, project_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Outil d'Alignement++")
        self.setMinimumSize(1000, 700)
        self.project_manager = project_manager
        self.aligner = Aligner()
        self.pairs = []
        
        # Navigation shortcuts
        self.shortcut_next = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_next.activated.connect(self._nav_next)
        
        self.shortcut_prev = QShortcut(QKeySequence("Ctrl+P"), self)
        self.shortcut_prev.activated.connect(self._nav_prev)

        self.shortcut_split = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_split.activated.connect(self._split_segment)

        self.shortcut_merge = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_merge.activated.connect(self._merge_segments)

        self.shortcut_next_tag = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_next_tag.activated.connect(self._nav_next_tag)

        self.shortcut_prev_tag = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_prev_tag.activated.connect(self._nav_prev_tag)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # File selection area
        file_layout = QHBoxLayout()

        # Source file
        src_group = QVBoxLayout()
        src_group.addWidget(QLabel("Fichier source :"))
        src_row = QHBoxLayout()
        self.src_label = QLabel("Aucun...")
        self.src_label.setStyleSheet("color: #94a3b8;")
        src_btn = QPushButton("Parcourir")
        src_btn.clicked.connect(self._select_source)
        src_row.addWidget(self.src_label, 1)
        src_row.addWidget(src_btn)
        src_group.addLayout(src_row)
        file_layout.addLayout(src_group)

        # Target file
        tgt_group = QVBoxLayout()
        tgt_group.addWidget(QLabel("Fichier cible :"))
        tgt_row = QHBoxLayout()
        self.tgt_label = QLabel("Aucun...")
        self.tgt_label.setStyleSheet("color: #94a3b8;")
        tgt_btn = QPushButton("Parcourir")
        tgt_btn.clicked.connect(self._select_target)
        tgt_row.addWidget(self.tgt_label, 1)
        tgt_row.addWidget(tgt_btn)
        tgt_group.addLayout(tgt_row)
        file_layout.addLayout(tgt_group)

        # Controls
        ctrl_layout = QVBoxLayout()
        lang_row = QHBoxLayout()
        self.src_lang_combo = QComboBox()
        self.src_lang_combo.addItems(['en', 'fr', 'zh', 'ja', 'ko', 'de', 'es', 'ru'])
        lang_row.addWidget(QLabel("Src:"))
        lang_row.addWidget(self.src_lang_combo)
        
        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.addItems(['fr', 'en', 'zh', 'ja', 'ko', 'de', 'es', 'ru'])
        lang_row.addWidget(QLabel("Tgt:"))
        lang_row.addWidget(self.tgt_lang_combo)
        ctrl_layout.addLayout(lang_row)
        
        align_btn = QPushButton("🔗 Aligner")
        align_btn.setStyleSheet("background-color: #3b82f6; color: white;")
        align_btn.clicked.connect(self._run_alignment)
        ctrl_layout.addWidget(align_btn)
        
        file_layout.addLayout(ctrl_layout)
        layout.addLayout(file_layout)

        # Toolbar for navigation and split/merge
        self.toolbar_layout = QHBoxLayout()
        btn_prev = QPushButton("◄ Préc")
        btn_prev.clicked.connect(self._nav_prev)
        btn_next = QPushButton("Suiv ►")
        btn_next.clicked.connect(self._nav_next)
        
        btn_split = QPushButton("✂ Diviser (Ctrl+S)")
        btn_split.clicked.connect(self._split_segment)
        btn_merge = QPushButton("🔗 Fusionner (Ctrl+M)")
        btn_merge.clicked.connect(self._merge_segments)

        self.toolbar_layout.addWidget(btn_prev)
        self.toolbar_layout.addWidget(btn_next)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(btn_split)
        self.toolbar_layout.addWidget(btn_merge)
        layout.addLayout(self.toolbar_layout)

        # 3-Column Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Conserver (Original)", "Source", "Cible"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #2a2a2a; background-color: #202020;")
        layout.addWidget(self.table, 1)

        # Footer
        footer_layout = QHBoxLayout()
        self.info_label = QLabel("Prêt")
        self.info_label.setStyleSheet("color: #94a3b8;")
        self.conf_label = QLabel("Confiance: N/A")
        
        export_btn = QPushButton("💾 Exporter TMX")
        export_btn.setStyleSheet("background-color: #22c55e;")
        export_btn.clicked.connect(self._export_tmx)
        
        add_tm_btn = QPushButton("📥 Ajouter TM")
        add_tm_btn.setStyleSheet("background-color: #8b5cf6;")
        add_tm_btn.clicked.connect(self._add_to_tm)
        
        footer_layout.addWidget(self.info_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.conf_label)
        footer_layout.addWidget(export_btn)
        footer_layout.addWidget(add_tm_btn)
        
        layout.addLayout(footer_layout)

        self.source_text = ""
        self.target_text = ""

    def _select_source(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Sélectionner source", "", "Fichiers (*.txt *.epub)")
        if fname:
            self.src_label.setText(fname)
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                     self.source_text = f.read()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Lecture impossible: {e}")

    def _select_target(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Sélectionner cible", "", "Fichiers (*.txt *.epub)")
        if fname:
            self.tgt_label.setText(fname)
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                     self.target_text = f.read()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Lecture impossible: {e}")

    def _run_alignment(self):
        if not self.source_text or not self.target_text:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner source et cible.")
            return

        self.info_label.setText("Alignement en cours...")
        src_lang = self.src_lang_combo.currentText()
        tgt_lang = self.tgt_lang_combo.currentText()

        self.pairs = self.aligner.align(
            self.source_text, self.target_text,
            src_lang=src_lang, tgt_lang=tgt_lang
        )

        self._update_table()
        self.info_label.setText(f"{len(self.pairs)} paires alignées.")

    def _update_table(self):
        self.table.setRowCount(len(self.pairs))
        for row, pair in enumerate(self.pairs):
            
            # Column 0: Conserver (Original text snippet, often equals source unless edited)
            cons_item = QTableWidgetItem(pair.source)
            cons_item.setFlags(cons_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read-only
            cons_item.setForeground(QColor("#94a3b8")) # Grayed out
            
            # Column 1: Source
            src_item = QTableWidgetItem(pair.source)
            
            # Column 2: Cible
            tgt_item = QTableWidgetItem(pair.target)

            # Color row background slightly based on confidence if low
            if pair.confidence < 0.5:
                src_item.setBackground(QColor("#450a0a"))
                tgt_item.setBackground(QColor("#450a0a"))

            self.table.setItem(row, 0, cons_item)
            self.table.setItem(row, 1, src_item)
            self.table.setItem(row, 2, tgt_item)

    def _nav_next(self):
        curr = self.table.currentRow()
        if curr < self.table.rowCount() - 1:
            self.table.selectRow(curr + 1)
            self._update_footer_conf()

    def _nav_prev(self):
        curr = self.table.currentRow()
        if curr > 0:
            self.table.selectRow(curr - 1)
            self._update_footer_conf()

    def _nav_next_tag(self):
        curr = self.table.currentRow()
        if curr < 0: curr = 0
        
        for r in range(curr + 1, self.table.rowCount()):
            src = self.table.item(r, 1).text()
            tgt = self.table.item(r, 2).text()
            is_valid, _, _ = validate_tags(src, tgt)
            if not is_valid:
                self.table.selectRow(r)
                self.info_label.setText("Tag manquant/en trop détecté (Ctrl+G)")
                return
        self.info_label.setText("Aucune erreur de tag trouvée après ce segment.")

    def _nav_prev_tag(self):
        curr = self.table.currentRow()
        if curr < 0: curr = self.table.rowCount() - 1
        
        for r in range(curr - 1, -1, -1):
            src = self.table.item(r, 1).text()
            tgt = self.table.item(r, 2).text()
            is_valid, _, _ = validate_tags(src, tgt)
            if not is_valid:
                self.table.selectRow(r)
                self.info_label.setText("Tag manquant/en trop détecté (Ctrl+T)")
                return
        self.info_label.setText("Aucune erreur de tag trouvée avant ce segment.")

    def _update_footer_conf(self):
        curr = self.table.currentRow()
        if 0 <= curr < len(self.pairs):
            self.conf_label.setText(f"Confiance: {self.pairs[curr].confidence:.0%}")

    def _merge_segments(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if len(rows) < 2:
            return

        first = rows[0]
        # Sync potentially edited text from table back to pairs before merge
        for r in rows:
             self.pairs[r].source = self.table.item(r, 1).text()
             self.pairs[r].target = self.table.item(r, 2).text()
             
        merged_src = ' '.join(self.pairs[r].source for r in rows)
        merged_tgt = ' '.join(self.pairs[r].target for r in rows)

        from src.core.aligner import AlignedPair
        merged = AlignedPair(
            source=merged_src, target=merged_tgt,
            confidence=min(self.pairs[r].confidence for r in rows),
            source_indices=[], target_indices=[],
        )

        for r in reversed(rows):
            self.pairs.pop(r)
        self.pairs.insert(first, merged)
        self._update_table()
        self.table.selectRow(first)

    def _split_segment(self):
        row = self.table.currentRow()
        if row < 0: return

        # Sync table edits to pair
        pair = self.pairs[row]
        pair.source = self.table.item(row, 1).text()
        pair.target = self.table.item(row, 2).text()

        segmenter = Segmenter()
        src_segs = segmenter.segment(pair.source)
        tgt_segs = segmenter.segment(pair.target)

        if len(src_segs) <= 1 and len(tgt_segs) <= 1:
            return

        from src.core.aligner import AlignedPair
        self.pairs.pop(row)
        max_segs = max(len(src_segs), len(tgt_segs))
        for i in range(max_segs):
            s = src_segs[i] if i < len(src_segs) else ''
            t = tgt_segs[i] if i < len(tgt_segs) else ''
            self.pairs.insert(row + i, AlignedPair(
                source=s, target=t, confidence=0.5,
                source_indices=[], target_indices=[]
            ))

        self._update_table()
        self.table.selectRow(row)

    def _export_tmx(self):
        if not self.pairs: return
        fname, _ = QFileDialog.getSaveFileName(self, "Exporter TMX", "", "TMX (*.tmx)")
        if fname:
            from src.core.tmx_handler import TMXHandler
            
            # Sync all current table edits to pairs
            for r in range(self.table.rowCount()):
                 self.pairs[r].source = self.table.item(r, 1).text()
                 self.pairs[r].target = self.table.item(r, 2).text()
                 
            class MockSeg:
                def __init__(self, src, tgt):
                    self.source_text = src
                    self.target_text = tgt

            mock_segs = [MockSeg(p.source, p.target) for p in self.pairs if p.source and p.target]
            TMXHandler.export_tmx(mock_segs, self.src_lang_combo.currentText(), self.tgt_lang_combo.currentText(), fname)
            QMessageBox.information(self, "Succès", f"{len(mock_segs)} paires exportées.")

    def _add_to_tm(self):
        if not self.pairs or not self.project_manager: return
        
        count = 0
        for r in range(self.table.rowCount()):
             src = self.table.item(r, 1).text().strip()
             tgt = self.table.item(r, 2).text().strip()
             if src and tgt:
                 self.project_manager.add_to_tm(src, tgt)
                 count += 1
                 
        QMessageBox.information(self, "Succès", f"{count} paires ajoutées au projet.")

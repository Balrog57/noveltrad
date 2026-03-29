from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QPushButton, QGroupBox,
                             QGridLayout)
from PyQt6.QtCore import Qt
from src.core.cost_estimator import CostEstimator

class StatisticsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Project Statistics")
        self.resize(600, 500)
        self.init_ui()
        self.calculate_stats()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # General Stats
        grp_gen = QGroupBox("General Information")
        gen_layout = QGridLayout()
        grp_gen.setLayout(gen_layout)
        
        self.lbl_segments = QLabel("Segments: Computing...")
        self.lbl_words = QLabel("Words: Computing...")
        self.lbl_chars = QLabel("Characters: Computing...")
        self.lbl_progress = QLabel("Progress: Computing...")
        
        gen_layout.addWidget(self.lbl_segments, 0, 0)
        gen_layout.addWidget(self.lbl_words, 0, 1)
        gen_layout.addWidget(self.lbl_chars, 1, 0)
        gen_layout.addWidget(self.lbl_progress, 1, 1)
        
        layout.addWidget(grp_gen)
        
        # Cost Estimation
        grp_cost = QGroupBox("AI Cost Estimation")
        cost_layout = QVBoxLayout()
        grp_cost.setLayout(cost_layout)
        
        help_lbl = QLabel("Estimated pricing based on character count / standard token ratios.\nActual costs may vary by provider.")
        help_lbl.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
        cost_layout.addWidget(help_lbl)
        
        self.cost_table = QTableWidget()
        self.cost_table.setColumnCount(3)
        self.cost_table.setHorizontalHeaderLabels(["Model", "Input Price / 1M", "Est. Total Cost"])
        self.cost_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cost_table.verticalHeader().setVisible(False)
        cost_layout.addWidget(self.cost_table)
        
        layout.addWidget(grp_cost)
        
        # Close Button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignRight)

    def calculate_stats(self):
        if not self.project: return
        
        from src.core.database import Segment
        from src.core.segment_status import SegmentStatus
        
        segments = list(Segment.select().where(Segment.project == self.project))
        
        total_segs = len(segments)
        translated_segs = sum(1 for s in segments if s.status in [SegmentStatus.MACHINE.value, SegmentStatus.AI_REFINED.value, SegmentStatus.VALIDATED.value])
        
        total_chars = sum(len(s.source_text) for s in segments if s.source_text)
        total_words = sum(len(s.source_text.split()) for s in segments if s.source_text)
        
        self.lbl_segments.setText(f"Segments: {total_segs}")
        self.lbl_words.setText(f"Words: {total_words:,}")
        self.lbl_chars.setText(f"Characters: {total_chars:,}")
        
        progress = (translated_segs / total_segs * 100) if total_segs > 0 else 0
        self.lbl_progress.setText(f"Progress: {progress:.1f}%")
        
        # Cost Calculation
        self.cost_table.setRowCount(0)
        
        models = CostEstimator.MODELS_PRICING
        row = 0
        for model_name, pricing in models.items():
            cost = CostEstimator.calculate_cost(" " * total_chars, model_name) # Approximation using chars
            # Actually calculate_cost uses text content to estimate tokens
            # But calculating tokens for all segments might be slow?
            # CostEstimator.estimate_tokens(text) uses len(text)/3.5
            # So passing a dummy string of same length works for estimation.
            
            self.cost_table.insertRow(row)
            self.cost_table.setItem(row, 0, QTableWidgetItem(model_name))
            self.cost_table.setItem(row, 1, QTableWidgetItem(f"${pricing['input']:.2f}"))
            self.cost_table.setItem(row, 2, QTableWidgetItem(f"${cost:.4f}"))
            row += 1

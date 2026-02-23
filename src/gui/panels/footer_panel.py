from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QWidget
from PyQt6.QtCore import Qt

class FooterPanel(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("Footer")
        self.setFixedHeight(32)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)
        
        # Status
        self.connectivity_point = QWidget()
        self.connectivity_point.setFixedSize(8, 8)
        self.connectivity_point.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
        self.connectivity_label = QLabel("EN LIGNE")
        self.connectivity_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        layout.addWidget(self.connectivity_point)
        layout.addWidget(self.connectivity_label)
        
        layout.addWidget(self.main_window.create_separator())
        
        # Language Selectors
        self.main_window.source_lang_combo = QComboBox()
        self.main_window.source_lang_combo.setMinimumWidth(120)
        self.main_window.source_lang_combo.currentIndexChanged.connect(lambda: self.main_window.on_language_changed('source'))
        
        self.main_window.target_lang_combo = QComboBox()
        self.main_window.target_lang_combo.setMinimumWidth(120)
        self.main_window.target_lang_combo.currentIndexChanged.connect(lambda: self.main_window.on_language_changed('target'))
        
        layout.addWidget(QLabel("Source :"))
        layout.addWidget(self.main_window.source_lang_combo)
        layout.addWidget(QLabel("Cible :"))
        layout.addWidget(self.main_window.target_lang_combo)
        
        layout.addStretch()
        
        # Progress
        progress_info = QVBoxLayout()
        progress_info.setSpacing(2)
        progress_head = QHBoxLayout()
        progress_head.addWidget(QLabel("PROGRESSION"))
        self.progress_pct = QLabel("0%")
        progress_head.addWidget(self.progress_pct)
        # Style
        progress_head.itemAt(0).widget().setStyleSheet("font-size: 8px; font-weight: 800; color: #64748b;")
        self.progress_pct.setStyleSheet("font-size: 8px; font-weight: 800; color: #64748b;")
        
        self.progress_bar_bg = QFrame()
        self.progress_bar_bg.setFixedHeight(4)
        self.progress_bar_bg.setFixedWidth(200)
        self.progress_bar_bg.setStyleSheet("background-color: #333333; border-radius: 2px;")
        self.progress_fill = QFrame(self.progress_bar_bg)
        self.progress_fill.setFixedHeight(4)
        self.progress_fill.setStyleSheet("background-color: #0d7ff2; border-radius: 2px;")
        self.progress_fill.setFixedWidth(0)
        
        progress_info.addLayout(progress_head)
        progress_info.addWidget(self.progress_bar_bg)
        layout.addLayout(progress_info)
        
        layout.addStretch()
        
        # Stats
        self.segments_count = QLabel("Segments: 0 / 0")
        self.words_count = QLabel("Words: 0 / 0")
        self.segments_count.setStyleSheet("font-size: 10px; color: #94a3b8;")
        self.words_count.setStyleSheet("font-size: 10px; color: #94a3b8;")
        layout.addWidget(self.segments_count)
        layout.addWidget(self.words_count)
        
        layout.addWidget(self.main_window.create_separator())
        
        # Auto-saved
        save_icon = QLabel()
        save_icon.setPixmap(self.main_window.colorize_icon("cloud_done", "#64748b").pixmap(12, 12))
        save_label = QLabel("AUTO-SAUVEGARDÉ")
        save_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b;")
        layout.addWidget(save_icon)
        layout.addWidget(save_label)

    def update_connectivity(self, is_online):
        if is_online:
            self.connectivity_point.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
            self.connectivity_label.setText("ONLINE")
        else:
            self.connectivity_point.setStyleSheet("background-color: #ef4444; border-radius: 4px;")
            self.connectivity_label.setText("OFFLINE (RESCUE MODE)")

    def update_progress(self, progress):
        self.progress_pct.setText(f"{progress}%")
        fill_width = int((progress / 100.0) * 200)
        self.progress_fill.setFixedWidth(fill_width)

    def update_stats(self, translated, total, source_words, target_words):
        self.segments_count.setText(f"Segments : {translated} / {total}")
        self.words_count.setText(f"Mots : {target_words:,} / {source_words:,}")

"""
Progress Dashboard for NovelTrad.
Visual progress tracking similar to AI Novel Translation.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QFrame, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen


class CircularProgress(QWidget):
    """
    Circular progress indicator widget.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.max_value = 100
        self.setMinimumSize(120, 120)
    
    def set_value(self, value, max_value=100):
        self.value = value
        self.max_value = max_value
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate sizes
        width = self.width()
        height = self.height()
        size = min(width, height)
        center = width // 2, height // 2
        radius = size // 2 - 10
        
        # Background circle
        painter.setPen(QPen(QColor("#333"), 4))
        painter.setBrush(QColor("#1a1a1a"))
        painter.drawEllipse(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
        
        # Progress arc
        if self.value > 0:
            percent = self.value / self.max_value
            angle = int(percent * 360)
            
            # Color based on progress
            if percent >= 1.0:
                color = QColor("#22c55e")  # Green
            elif percent >= 0.5:
                color = QColor("#0d7ff2")  # Blue
            else:
                color = QColor("#f59e0b")  # Orange
            
            painter.setPen(QPen(color, 6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw arc
            rect_x = center[0] - radius
            rect_y = center[1] - radius
            painter.drawArc(rect_x, rect_y, radius * 2, radius * 2, 
                          90 * 16, -angle * 16)
        
        # Center text
        painter.setPen(QColor("#e2e8f0"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)
        
        percent_text = f"{int(self.value / self.max_value * 100)}%" if self.max_value > 0 else "0%"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, percent_text)


class ProgressDashboard(QWidget):
    """
    Dashboard showing translation progress with visual indicators.
    Similar to AI Novel Translation's progress view.
    """
    
    openProject = pyqtSignal()  # Signal to open project settings
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📊 Translation Progress")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Circular progress
        self.circular = CircularProgress()
        layout.addWidget(self.circular, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Stats grid
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)
        
        # Total segments
        self.total_label = self._create_stat_card("Total Segments", "0", stats_layout, 0, 0)
        
        # Translated
        self.translated_label = self._create_stat_card("Translated", "0", stats_layout, 0, 1)
        
        # Remaining
        self.remaining_label = self._create_stat_card("Remaining", "0", stats_layout, 1, 0)
        
        # Validated
        self.validated_label = self._create_stat_card("Validated", "0", stats_layout, 1, 1)
        
        layout.addLayout(stats_layout)
        
        # Progress bar
        bar_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #1a1a1a;
                text-align: center;
                color: #e2e8f0;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #0d7ff2;
                border-radius: 3px;
            }
        """)
        bar_layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_label = QLabel("No project loaded")
        self.status_label.setStyleSheet("""
            color: #64748b;
            font-size: 12px;
            margin-top: 5px;
        """)
        bar_layout.addWidget(self.status_label)
        
        layout.addLayout(bar_layout)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        
        translate_all_btn = QPushButton("Translate All")
        translate_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7ff2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        actions_layout.addWidget(translate_all_btn)
        
        validate_btn = QPushButton("Validate All")
        validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        actions_layout.addWidget(validate_btn)
        
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def _create_stat_card(self, title, value, layout, row, col):
        """Create a stat card widget."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        card_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #e2e8f0; font-size: 24px; font-weight: 700;")
        card_layout.addWidget(value_label)
        
        layout.addWidget(card, row, col)
        
        return value_label
    
    def update_progress(self, total, translated, validated, ai_refined=0):
        """
        Update progress display.
        
        Args:
            total: Total number of segments
            translated: Number of translated segments
            validated: Number of validated segments
            ai_refined: Number of AI-refined segments
        """
        remaining = total - translated
        
        # Update circular
        self.circular.set_value(translated, total)
        
        # Update stats
        self.total_label.setText(str(total))
        self.translated_label.setText(str(translated))
        self.remaining_label.setText(str(remaining))
        self.validated_label.setText(str(validated))
        
        # Update progress bar
        if total > 0:
            percent = int(translated / total * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{translated}/{total} ({percent}%)")
            
            # Update status
            if validated == total:
                status = "✅ Complete! Ready for export."
                color = "#22c55e"
            elif translated == total:
                status = "🎯 All translated! Review and validate."
                color = "#f59e0b"
            else:
                status = f"📝 In progress... {remaining} segments remaining"
                color = "#64748b"
            
            self.status_label.setText(status)
            self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
    
    def set_project(self, project_name, total_segments):
        """Set project info."""
        self.project_name = project_name
        self.status_label.setText(f"Project: {project_name}")


def create_progress_dashboard(main_window):
    """
    Create and attach progress dashboard to main window.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        ProgressDashboard instance
    """
    dashboard = ProgressDashboard()
    return dashboard

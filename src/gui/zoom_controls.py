"""
Zoom and Font Size Controls for NovelTrad.
Allows users to adjust font size in the editor for better accessibility.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSlider
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ZoomControlWidget(QWidget):
    """
    Widget for controlling editor font size and zoom level.
    """
    zoomChanged = pyqtSignal(int)  # Signal emitted when zoom changes
    
    def __init__(self, parent=None, min_zoom=50, max_zoom=200, default_zoom=100):
        super().__init__(parent)
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.current_zoom = default_zoom
        
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Zoom out button
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(24, 24)
        self.zoom_out_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(self.min_zoom)
        self.zoom_slider.setMaximum(self.max_zoom)
        self.zoom_slider.setValue(self.current_zoom)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(25)
        self.zoom_slider.valueChanged.connect(self.on_slider_changed)
        
        # Zoom label
        self.zoom_label = QLabel(f"{self.current_zoom}%")
        self.zoom_label.setStyleSheet("font-size: 11px; min-width: 40px;")
        
        # Zoom in button
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(24, 24)
        self.zoom_in_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        # Reset button
        self.reset_btn = QPushButton("⟲")
        self.reset_btn.setFixedSize(24, 24)
        self.reset_btn.setStyleSheet("font-size: 14px;")
        self.reset_btn.setToolTip("Reset to default")
        self.reset_btn.clicked.connect(self.reset_zoom)
        
        layout.addWidget(self.zoom_out_btn)
        layout.addWidget(self.zoom_slider)
        layout.addWidget(self.zoom_label)
        layout.addWidget(self.zoom_in_btn)
        layout.addWidget(self.reset_btn)
    
    def zoom_in(self):
        """Increase zoom by 10%."""
        new_zoom = min(self.current_zoom + 10, self.max_zoom)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        """Decrease zoom by 10%."""
        new_zoom = max(self.current_zoom - 10, self.min_zoom)
        self.set_zoom(new_zoom)
    
    def reset_zoom(self):
        """Reset to default zoom level."""
        self.set_zoom(100)
    
    def set_zoom(self, value):
        """Set zoom to specific value."""
        self.current_zoom = value
        self.zoom_slider.setValue(value)
        self.zoom_label.setText(f"{value}%")
        self.zoomChanged.emit(value)
    
    def on_slider_changed(self, value):
        """Handle slider value change."""
        self.current_zoom = value
        self.zoom_label.setText(f"{value}%")
        self.zoomChanged.emit(value)
    
    def get_font_size(self, base_size):
        """Calculate actual font size based on zoom level."""
        return int(base_size * self.current_zoom / 100)


class StatusBarZoomControl:
    """
    Mixin to add zoom controls to the status bar.
    """
    
    def add_zoom_control_to_statusbar(self):
        """Add zoom control to the status bar."""
        from PyQt6.QtWidgets import QLabel
        
        # Create zoom widget
        self.zoom_widget = ZoomControlWidget()
        self.zoom_widget.zoomChanged.connect(self.on_zoom_changed)
        
        # Add to status bar
        self.statusBar().addPermanentWidget(QLabel("  Font: "))
        self.statusBar().addPermanentWidget(self.zoom_widget)
    
    def on_zoom_changed(self, zoom_level):
        """Handle zoom level change."""
        # Apply to all text edits in the main window
        if hasattr(self, 'segment_list'):
            base_font_size = 12  # Default base size
            new_size = self.zoom_widget.get_font_size(base_font_size)
            
            for segment_card in self.segment_list:
                if hasattr(segment_card, 'source_edit'):
                    font = segment_card.source_edit.font()
                    font.setPointSize(new_size)
                    segment_card.source_edit.setFont(font)
                
                if hasattr(segment_card, 'target_edit'):
                    font = segment_card.target_edit.font()
                    font.setPointSize(new_size)
                    segment_card.target_edit.setFont(font)
        
        self.statusBar().showMessage(f"Font size: {zoom_level}%", 2000)


def apply_zoom_to_widget(widget, zoom_percent):
    """
    Apply zoom to a specific widget by adjusting its font size.
    
    Args:
        widget: QWidget to apply zoom to
        zoom_percent: Zoom level (100 = normal)
    """
    font = widget.font()
    base_size = font.pointSize()
    if base_size <= 0:
        base_size = 12  # Default
    
    new_size = int(base_size * zoom_percent / 100)
    font.setPointSize(new_size)
    widget.setFont(font)

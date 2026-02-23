"""
Real-time Preview Module for NovelTrad.
Provides live EPUB/DOCX rendering preview of translated chapters.
Conforms to §4.3 of the specification.
"""
import os
from typing import Optional
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QDockWidget


class PreviewWidget(QWebEngineView):
    """
    Real-time preview widget for EPUB/DOCX rendering.
    Displays a read-only preview of the translated content.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 400)
        self._setup_html_template()
        
    def _setup_html_template(self):
        """Setup the HTML template for preview."""
        self.html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; }
        body {{
            font-family: {font_family};
            font-size: {font_size}px;
            line-height: {line_height};
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: {bg_color};
            color: {text_color};
        }}
        h1, h2, h3 {{
            color: {heading_color};
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        p {{ margin-bottom: 1em; text-align: justify; }}
        .chapter-title {{
            font-size: 1.5em;
            font-weight: bold;
            text-align: center;
            margin: 2em 0;
            color: {accent_color};
        }}
        b, strong {{ font-weight: bold; }}
        i, em {{ font-style: italic; }}
        .placeholder {{
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>"""
    
    def update_preview(self, translated_text: str, chapter_title: str = "",
                      font_family: str = "Georgia, serif",
                      font_size: int = 16,
                      line_height: float = 1.8,
                      theme: str = "light"):
        """
        Update preview with translated content.
        
        Args:
            translated_text: Translated text content
            chapter_title: Chapter title
            font_family: Font family for preview
            font_size: Font size in pixels
            line_height: Line height multiplier
            theme: 'light' or 'dark'
        """
        if theme == "dark":
            theme_colors = {
                'bg_color': '#1a1a1a',
                'text_color': '#e0e0e0',
                'heading_color': '#60a5fa',
                'accent_color': '#3b82f6'
            }
        else:
            theme_colors = {
                'bg_color': '#ffffff',
                'text_color': '#1a1a1a',
                'heading_color': '#1a1a1a',
                'accent_color': '#3b82f6'
            }
        
        # Format content with paragraphs
        content = ""
        if chapter_title:
            content += f'<div class="chapter-title">{chapter_title}</div>'
        
        for para in translated_text.split('\n\n'):
            if para.strip():
                content += f'<p>{para.strip()}</p>'
        
        if not content:
            content = '<p class="placeholder">Preview will appear here...</p>'
        
        html = self.html_template.format(
            content=content,
            font_family=font_family,
            font_size=font_size,
            line_height=line_height,
            **theme_colors
        )
        
        self.setHtml(html)
    
    def clear_preview(self):
        """Clear the preview."""
        self.update_preview("", theme="dark")


class PreviewDockWidget:
    """
    Dockable preview panel that can be toggled on/off.
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.preview_widget = None
        self.dock_widget = None
        
    def create_dock(self):
        """Create the preview dock widget."""
        
        self.preview_widget = PreviewWidget()
        
        self.dock_widget = QDockWidget("Aperçu temps réel", self.main_window)
        self.dock_widget.setWidget(self.preview_widget)
        self.dock_widget.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | 
                                         Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_widget.setVisible(False)  # Hidden by default
        
        return self.dock_widget
    
    def toggle_visibility(self):
        """Toggle preview visibility."""
        if self.dock_widget:
            self.dock_widget.setVisible(not self.dock_widget.isVisible())
    
    def update(self, text: str, title: str = ""):
        """Update preview content."""
        if self.preview_widget:
            theme = "dark" if self.main_window.is_dark_theme else "light"
            self.preview_widget.update_preview(text, title, theme=theme)


def create_preview_panel(main_window):
    """
    Factory function to create and attach preview panel to main window.
    
    Args:
        main_window: Main window instance
        
    Returns:
        PreviewDockWidget instance
    """
    preview = PreviewDockWidget(main_window)
    dock = preview.create_dock()
    main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    return preview

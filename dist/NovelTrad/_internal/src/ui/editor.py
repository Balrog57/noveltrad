from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QSplitter
)
from PyQt6.QtCore import Qt

class EditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Splitter for Side-by-Side view
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Source Panel
        self.source_widget = QWidget()
        source_layout = QVBoxLayout(self.source_widget)
        source_label = QLabel("Source")
        source_label.setStyleSheet("font-weight: bold; color: #555;")
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)  # Source is read-only by default
        self.source_text.setPlaceholderText("Source text will appear here...")
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_text)
        
        # Target Panel
        self.target_widget = QWidget()
        target_layout = QVBoxLayout(self.target_widget)
        target_label = QLabel("Traduction")
        target_label.setStyleSheet("font-weight: bold; color: #555;")
        self.target_text = QTextEdit()
        self.target_text.setPlaceholderText("Translation will appear here...")
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_text)
        
        # Add to splitter
        self.splitter.addWidget(self.source_widget)
        self.splitter.addWidget(self.target_widget)
        self.splitter.setSizes([500, 500])  # Initial 50/50 split
        
        layout.addWidget(self.splitter)
        
    def set_source_text(self, text):
        self.source_text.setPlainText(text)
        
    def get_target_text(self):
        return self.target_text.toPlainText()

    def load_segments(self, segments):
        source_content = ""
        target_content = ""
        
        for segment in segments:
            source_content += f"{segment.source_text}\n\n"
            if segment.target_text:
                target_content += f"{segment.target_text}\n\n"
            else:
                target_content += "\n\n"
                
        self.source_text.setPlainText(source_content)
        self.target_text.setPlainText(target_content)

    def get_current_segment_index(self):
        # ROI: Rudimentary way to find which segment the cursor is on.
        # Assuming double newlines separator.
        cursor = self.source_text.textCursor()
        text_upto_cursor = self.source_text.toPlainText()[:cursor.position()]
        # Count double newlines
        return text_upto_cursor.count('\n\n')

    def update_target_segment(self, index, text):
        # Update specific segment in target text edit
        # ROI: This is tricky with simple QTextEdit. ideally we use QListView or similar.
        # For this prototype, we'll rebuild the text or try to find the range.
        # Rebuilding is safer for sync but slower.
        
        content = self.target_text.toPlainText()
        segments = content.split('\n\n')
        
        if 0 <= index < len(segments):
            segments[index] = text
        elif index == len(segments): # Append
             segments.append(text)
        
        # Preserve cursor
        cursor = self.target_text.textCursor()
        pos = cursor.position()
        
        self.target_text.setPlainText('\n\n'.join(segments))
        
        # Restore cursor (approximate)
        new_cursor = self.target_text.textCursor()
        new_cursor.setPosition(min(pos, len(self.target_text.toPlainText())))
        self.target_text.setTextCursor(new_cursor)

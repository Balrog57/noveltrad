
DARK_THEME = """
/* Premium Dark Theme - NovelTrad */
QWidget {
    background-color: #0B0B0B;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QLabel {
    background-color: transparent;
}

QFrame#Header {
    background-color: #000000;
    border-bottom: 1px solid #333333;
}

QFrame#Footer {
    background-color: #000000;
    border-top: 1px solid #333333;
}

QFrame#Sidebar {
    background-color: #000000;
    border-right: 1px solid #333333;
}

QFrame#RightPanel {
    background-color: #000000;
    border-left: 1px solid #333333;
}

QSplitter::handle {
    background-color: #333333;
    border: none;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:hover {
    background-color: #0d7ff2;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 4px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #444444;
    min-height: 20px;
    border-radius: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}

/* Segment Cards */
QFrame#SegmentCard {
    background-color: #1a1a1a; 
    border: 1px solid #333333;
    border-radius: 8px;
    margin: 2px;
}
QFrame#SegmentCard:hover {
    border-color: #475569;
}
QFrame#SegmentCard[active="true"] {
    background-color: #1e1e1e;
    border: 2px solid #3b82f6;
}

/* Labels */
QLabel#SidebarTitle {
    color: #cbd5e1;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#ProjectTitle {
    color: #94a3b8;
    font-size: 11px;
}
QLabel#ProjectName {
    color: #cbd5e1;
    font-weight: 500;
}

/* Buttons */
QPushButton#IconButton {
    background-color: transparent;
    border: none;
    padding: 6px;
    border-radius: 4px;
}
QPushButton#IconButton:hover {
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton#PrimaryButton {
    background-color: #0d7ff2;
    color: white;
    font-weight: 700;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}
QPushButton#PrimaryButton:hover {
    background-color: #0b69c9;
}

/* Text Editors */
QTextEdit {
    background-color: transparent;
    border: none;
    font-family: 'Merriweather', 'Georgia', serif;
    font-size: 16px;
    line-height: 1.6;
}

QTextEdit#SourceText {
    color: #94a3b8;
}

QTextEdit#TargetText {
    color: #ffffff;
}

/* Dictionary & Glossary Sections */
QFrame#ToolSection {
    background-color: rgba(15, 23, 42, 0.3);
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 8px;
}

QListWidget {
    background-color: transparent;
    border: none;
    color: #cbd5e1;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #222222;
}

QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.05);
}

/* Glass Active for Sidebar */
QFrame#SidebarItem[active="true"] {
    background: rgba(13, 127, 242, 0.1);
    border-left: 3px solid #0d7ff2;
}

QListWidget#GlossaryList::item {
    background-color: rgba(22, 22, 22, 0.3);
    border: 1px solid #333333;
    border-radius: 8px;
    margin-bottom: 8px;
    padding: 12px;
}

QListWidget#GlossaryList::item:hover {
    background-color: rgba(22, 22, 22, 0.6);
    border-color: #475569;
}

/* ComboBox/Inputs */
QComboBox {
    background-color: #1e293b;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 2px 8px;
    color: #e2e8f0;
}
"""

LIGHT_THEME = """
/* Light Theme - NovelTrad */
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
/* ... existing light theme or simplified ... */
"""

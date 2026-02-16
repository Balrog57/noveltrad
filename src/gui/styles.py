
DARK_THEME = """
/* Premium Dark Theme - NovelTrad */
QWidget {
    background-color: #0B0B0B;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QFrame#Header {
    background-color: rgba(22, 22, 22, 0.5);
    border-bottom: 1px solid #333333;
}

QFrame#Footer {
    background-color: #161616;
    border-top: 1px solid #333333;
}

QFrame#Sidebar {
    background-color: #0B0B0B;
    border-right: 1px solid #333333;
}

QFrame#RightPanel {
    background-color: #161616;
    border-left: 1px solid #333333;
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
    background-color: rgba(22, 22, 22, 0.2);
    border: 1px solid #333333;
    border-radius: 8px;
    margin: 2px;
}
QFrame#SegmentCard:hover {
    border-color: #475569;
}
QFrame#SegmentCard[active="true"] {
    background-color: #161616;
    border: 2px solid #0d7ff2;
}

/* Labels */
QLabel#SidebarTitle {
    color: #94a3b8;
    font-weight: 700;
    font-size: 10px;
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

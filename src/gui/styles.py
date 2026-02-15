
DARK_THEME = """
/* Global Reset & Colors */
/* 
   Palette:
   Primary: #0d7ff2
   Background: #0B0B0B
   Panel: #161616
   Border: #333333
   Text Main: #e2e8f0 (Slate 200)
   Text Muted: #94a3b8 (Slate 400)
*/

QWidget {
    background-color: #0B0B0B;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 14px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0B0B0B;
    width: 6px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Sidebar */
QFrame#SidebarContainer {
    background-color: #0B0B0B;
    border-right: 1px solid #333333;
}

/* Sidebar Item */
QFrame#SidebarItem {
    background-color: transparent;
    border-radius: 4px;
    margin: 2px 8px; /* Spacing between items */
}
QFrame#SidebarItem:hover {
    background-color: rgba(255, 255, 255, 0.05); /* hover:bg-white/5 */
}
/* Active Sidebar Item - Glass effect simulation */
QFrame#SidebarItem[active="true"] {
    background-color: rgba(13, 127, 242, 0.1); /* Primary with opacity */
    border-left: 2px solid #0d7ff2;
}

/* Sidebar Labels */
QLabel#SidebarTitle {
    color: #94a3b8; /* Slate 400 */
    font-weight: 500;
}
QFrame#SidebarItem[active="true"] QLabel#SidebarTitle {
    color: #ffffff;
    font-weight: 700;
}
QLabel#SidebarProgress {
    color: #0d7ff2;
    font-weight: bold;
    font-size: 10px;
}

/* Segment Cards */
QFrame#SegmentCard {
    background-color: rgba(22, 22, 22, 0.4); /* Panel dark with some transparency */
    border: 1px solid #333333;
    border-radius: 8px;
}
QFrame#SegmentCard[status="translated"] {
    background-color: rgba(22, 22, 22, 0.6);
}
QFrame#SegmentCard[active="true"] {
    background-color: #161616;
    border: 1px solid #0d7ff2; /* Primary border */
    /* Shadow simulated via border for now in QSS */
}

/* ID Badge */
QLabel#IdBadge {
    background-color: #333333;
    color: #94a3b8;
    border-radius: 4px;
    padding: 2px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 11px;
}
QFrame#SegmentCard[active="true"] QLabel#IdBadge {
    background-color: rgba(13, 127, 242, 0.2);
    color: #0d7ff2;
}

/* Status Labels */
QLabel#StatusLabel {
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
    color: #64748b;
}
QLabel#StatusLabel[status="translated"] { color: #22c55e; }
QLabel#StatusLabel[status="translating"] { color: #0d7ff2; }

/* Text Areas */
QTextEdit {
    background-color: transparent;
    border: none;
    color: #e2e8f0;
    font-family: 'Merriweather', 'Georgia', serif; /* Serif for text */
    font-size: 15px;
    line-height: 1.5;
}
QTextEdit#TargetText {
    font-family: 'Segoe UI', 'Inter', sans-serif; /* Sans for target usually? Or serif too? HTML uses 'font-display' for UI but 'font-serif' for source P, textarea usually sans or defined. code.html textarea has font-display (Inter) */
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
/* Active Target Input */
QFrame#SegmentCard[active="true"] QTextEdit#TargetText {
    color: #ffffff;
}

/* Right Panel */
QFrame#RightPanel {
    background-color: #161616;
    border-left: 1px solid #333333;
}

/* Headers */
QLabel#PanelHeader {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
    color: #ffffff;
}
QPushButton[primary="true"] {
    background-color: #0d7ff2;
    color: white;
    border: none;
}
QPushButton[primary="true"]:hover {
    background-color: #0b69c9;
}

/* Glossary List */
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 8px;
    margin-bottom: 8px;
    color: #e2e8f0;
}
QListWidget::item:hover {
    border-color: #64748b;
}

/* Header Bar */
QLabel#HeaderLabel {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#PremiumBadge {
    color: #0d7ff2;
    font-size: 10px;
    font-weight: 700;
    border: 1px solid #0d7ff2;
    border-radius: 4px;
    background-color: rgba(13, 127, 242, 0.1);
}
"""

LIGHT_THEME = """
/* Light Theme - NovelTrad */
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 14px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Sidebar */
QFrame#SidebarContainer {
    background-color: #f1f5f9;
    border-right: 1px solid #e2e8f0;
}

/* Sidebar Item */
QFrame#SidebarItem {
    background-color: transparent;
    border-radius: 6px;
    margin: 2px 8px;
}
QFrame#SidebarItem:hover {
    background-color: #e2e8f0;
}
QFrame#SidebarItem[active="true"] {
    background-color: #dbeafe;
    border-left: 3px solid #0d7ff2;
}

/* Sidebar Labels */
QLabel#SidebarTitle {
    color: #64748b;
    font-weight: 500;
}
QFrame#SidebarItem[active="true"] QLabel#SidebarTitle {
    color: #1e293b;
    font-weight: 700;
}
QLabel#SidebarProgress {
    color: #0d7ff2;
    font-weight: bold;
    font-size: 10px;
}

/* Segment Cards */
QFrame#SegmentCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QFrame#SegmentCard[status="translated"] {
    background-color: #f0fdf4;
}
QFrame#SegmentCard[active="true"] {
    background-color: #eff6ff;
    border: 2px solid #0d7ff2;
}

/* ID Badge */
QLabel#IdBadge {
    background-color: #f1f5f9;
    color: #64748b;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}
QFrame#SegmentCard[active="true"] QLabel#IdBadge {
    background-color: #dbeafe;
    color: #0d7ff2;
}

/* Status Labels */
QLabel#StatusLabel {
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
    color: #94a3b8;
}
QLabel#StatusLabel[status="translated"] { color: #16a34a; }
QLabel#StatusLabel[status="translating"] { color: #0d7ff2; }

/* Text Areas */
QTextEdit {
    background-color: transparent;
    border: none;
    color: #334155;
    font-family: 'Merriweather', Georgia, serif;
    font-size: 15px;
    line-height: 1.6;
}
QTextEdit#TargetText {
    font-family: 'Segoe UI', Inter, sans-serif;
    color: #1e293b;
}
QTextEdit::placeholder {
    color: #94a3b8;
}
QFrame#SegmentCard[active="true"] QTextEdit#TargetText {
    color: #0f172a;
}

/* Right Panel */
QFrame#RightPanel {
    background-color: #ffffff;
    border-left: 1px solid #e2e8f0;
}

/* Headers */
QLabel#PanelHeader {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Buttons */
QPushButton {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #e2e8f0;
    color: #1e293b;
}
QPushButton[primary="true"] {
    background-color: #0d7ff2;
    color: white;
    border: none;
}
QPushButton[primary="true"]:hover {
    background-color: #0284c7;
}

/* Line Edit (Search) */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1e293b;
}
QLineEdit:focus {
    border-color: #0d7ff2;
}
QLineEdit::placeholder {
    color: #94a3b8;
}

/* ComboBox */
QComboBox {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 8px;
    color: #1e293b;
}
QComboBox::drop-down {
    border: none;
}

/* Glossary/Dictionary List */
QListWidget {
    background: transparent;
    border: none;
}
QListWidget::item {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-bottom: 6px;
    padding: 8px;
    color: #334155;
}
QListWidget::item:hover {
    border-color: #0d7ff2;
    background-color: #f0f9ff;
}

/* Header Bar */
QLabel#HeaderLabel {
    font-size: 18px;
    font-weight: 700;
    color: #1e293b;
}

QLabel#PremiumBadge {
    color: #0d7ff2;
    font-size: 10px;
    font-weight: 700;
    border: 1px solid #0d7ff2;
    border-radius: 4px;
    background-color: #eff6ff;
}

/* Status Bar */
QStatusBar {
    background-color: #f1f5f9;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
}

/* Header */
QFrame {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
"""

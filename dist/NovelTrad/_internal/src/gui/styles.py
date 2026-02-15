DARK_THEME = """
/* Global Reset */
QWidget {
    background-color: #0b0f19; /* Deepest background */
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 14px;
}

    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 5px;
    outline: none;
}

/* Sidebar (Left) */
QFrame#SidebarContainer {
    background-color: #0b0f19;
    border-right: 1px solid #1e293b;
}

QFrame#SidebarItem {
    background-color: transparent;
    border-left: 3px solid transparent;
    border-radius: 0px; 
}

QFrame#SidebarItem[active="true"] {
    background-color: rgba(59, 130, 246, 0.1); /* Subtle blue tint */
    border-left: 3px solid #3b82f6; 
}

QFrame#SidebarItem:hover {
    background-color: #111625;
}

/* Segment Cards (Center) */
QListWidget::item {
    background-color: #334155;
    color: #e2e8f0;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 5px;
}

QListWidget::item:selected {
    background-color: #3b82f6; /* Accent Blue */
    color: #ffffff;
    border: none;
}

QListWidget::item:hover {
    background-color: #475569;
}

/* Text Editors */
QTextEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px;
    color: #f1f5f9;
    font-size: 15px;
    selection-background-color: #3b82f6;
}

/* Buttons */
QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

/* Secondary Buttons (Wait, maybe add a class later) */

/* Inputs (QLineEdit) */
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px;
    color: #f1f5f9;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
}

/* Headers / Labels */
QLabel {
    color: #94a3b8;
    font-weight: bold;
    font-size: 12px;
    text-transform: uppercase;
    margin-bottom: 4px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #1e293b;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 12px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e293b;
    color: #3b82f6;
    font-weight: bold;
    border-bottom: 2px solid #3b82f6;
}

/* Custom Header Label (class name specific if possible, or just object name) */
QLabel#HeaderLabel {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    padding: 10px 0;
}

QLabel#HeaderLabel span {
    color: #3b82f6;
}
"""

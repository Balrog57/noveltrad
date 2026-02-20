"""
Recent Projects Manager for NovelTrad.
Tracks and displays recently opened projects for quick access.
"""
import os
import json
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu


class RecentProjectsManager:
    """
    Manages the list of recently opened projects.
    """
    
    MAX_RECENT = 10
    CONFIG_KEY = "recent_projects"
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.recent_list = self.load_recent()
    
    def load_recent(self):
        """Load recent projects from config."""
        recent = self.config.get(self.CONFIG_KEY, [])
        # Filter out projects that no longer exist
        valid = []
        for item in recent:
            if os.path.exists(item['path']):
                valid.append(item)
            # Limit to max
            if len(valid) >= self.MAX_RECENT:
                break
        return valid
    
    def save_recent(self):
        """Save recent projects to config."""
        self.config.set(self.CONFIG_KEY, self.recent_list)
        self.config.save_config()
    
    def add_recent(self, project_path, project_name):
        """
        Add a project to the recent list.
        
        Args:
            project_path: Path to the project file
            project_name: Display name of the project
        """
        # Remove if already exists
        self.recent_list = [p for p in self.recent_list if p['path'] != project_path]
        
        # Add to front
        self.recent_list.insert(0, {
            'path': project_path,
            'name': project_name,
            'last_opened': datetime.now().isoformat()
        })
        
        # Trim to max
        self.recent_list = self.recent_list[:self.MAX_RECENT]
        
        self.save_recent()
    
    def get_recent(self):
        """Get list of recent projects."""
        return self.recent_list
    
    def clear_recent(self):
        """Clear all recent projects."""
        self.recent_list = []
        self.save_recent()
    
    def remove_recent(self, project_path):
        """Remove a specific project from recent list."""
        self.recent_list = [p for p in self.recent_list if p['path'] != project_path]
        self.save_recent()


def create_recent_projects_menu(parent, recent_manager, open_callback):
    """
    Create a menu for recent projects.
    
    Args:
        parent: Parent widget
        recent_manager: RecentProjectsManager instance
        open_callback: Function to call when a project is selected (path)
    
    Returns:
        QMenu instance
    """
    menu = QMenu("Recent Projects", parent)
    
    recent_list = recent_manager.get_recent()
    
    if not recent_list:
        empty_action = menu.addAction("(No recent projects)")
        empty_action.setEnabled(False)
        return menu
    
    for item in recent_list:
        # Format: Project Name - DD/MM/YYYY
        name = item['name']
        try:
            dt = datetime.fromisoformat(item['last_opened'])
            date_str = dt.strftime("%d/%m/%Y")
            text = f"{name} - {date_str}"
        except:
            text = name
        
        action = menu.addAction(text)
        action.triggered.connect(lambda checked, p=item['path']: open_callback(p))
        
        # Add remove action
        action.setData(item['path'])
    
    menu.addSeparator()
    
    # Clear recent
    clear_action = menu.addAction("Clear Recent")
    clear_action.triggered.connect(lambda: recent_manager.clear_recent())
    
    return menu


def add_recent_to_filemenu(main_window, menu_bar):
    """
    Add recent projects to the File menu.
    
    Args:
        main_window: MainWindow instance
        menu_bar: QMenuBar instance
    """
    from PyQt6.QtWidgets import QMenu
    
    # Find File menu
    file_menu = None
    for action in menu_bar.actions():
        if action.text() == "File":
            file_menu = action.menu()
            break
    
    if not file_menu:
        return
    
    # Add recent projects submenu before Quit
    recent_menu = create_recent_projects_menu(
        main_window,
        main_window.recent_projects,
        main_window.open_project_from_path
    )
    
    # Insert before the last separator or Quit
    actions = file_menu.actions()
    insert_index = len(actions) - 1
    for i, action in enumerate(actions):
        if action.text() == "Quit" or action.text() == "Quitter":
            insert_index = i
            break
    
    file_menu.insertMenu(file_menu.actions()[insert_index] if insert_index < len(actions) else None, recent_menu)

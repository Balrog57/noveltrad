import os
from datetime import datetime, timezone
from typing import Dict, Optional

class LastEntryManager:
    """
    Manages the last_entry.properties file for OmegaT compatibility.
    Stores the last visited segment for chapters and the last opened project.
    """
    def __init__(self, noveltrad_dir: str):
        self.properties_path = os.path.join(noveltrad_dir, "last_entry.properties")
        self.data: Dict[str, str] = {}
        self.load()

    def load(self):
        """Loads properties from the file if it exists."""
        self.data.clear()
        if not os.path.exists(self.properties_path):
            return

        try:
            with open(self.properties_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        self.data[k.strip()] = v.strip()
        except Exception as e:
            print(f"Error loading last_entry.properties: {e}")

    def save(self):
        """Saves current properties to the file."""
        try:
            with open(self.properties_path, 'w', encoding='utf-8') as f:
                f.write("# Last visited segment for each chapter\n")
                f.write(f"# Updated automatically by NovelTrad\n")
                f.write(f"last_session={datetime.now(timezone.utc).isoformat()}\n")
                
                for k, v in self.data.items():
                    if k != "last_session": # Already written above
                         f.write(f"{k}={v}\n")
        except Exception as e:
            print(f"Error saving last_entry.properties: {e}")

    def update_last_segment(self, chapter_title: str, segment_id: int):
        """Records the last visited segment for a specific chapter."""
        key = f"{chapter_title}.last_segment"
        self.data[key] = str(segment_id)
        self.save()

    def get_last_segment(self, chapter_title: str) -> Optional[int]:
        """Retrieves the last visited segment ID for a specific chapter."""
        key = f"{chapter_title}.last_segment"
        val = self.data.get(key)
        if val and val.isdigit():
            return int(val)
        return None

    def set_last_project(self, project_path: str):
        self.data["last_project"] = project_path.replace('\\', '\\\\')
        self.save()

import os
import shutil
import datetime
import glob
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DBChangeHandler(FileSystemEventHandler):
    def __init__(self, backup_manager, interval_minutes):
        self.backup_manager = backup_manager
        self.interval_seconds = interval_minutes * 60
        self.last_backup_time = time.time()

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == os.path.abspath(self.backup_manager.project_db_path):
            current_time = time.time()
            if current_time - self.last_backup_time >= self.interval_seconds:
                self.backup_manager.create_snapshot(label="auto")
                self.last_backup_time = current_time

class BackupManager:
    """Handles automatic versioned snapshots for NovelTrad projects."""
    
    def __init__(self, project_db_path, max_backups=10):
        self.project_db_path = project_db_path
        self.max_backups = max_backups
        self.project_dir = os.path.dirname(os.path.abspath(project_db_path))
        self.backup_dir = os.path.join(self.project_dir, ".snapshots")
        self.observer = None

    def start_auto_backup(self, interval_minutes=3):
        """Starts a background watchdog to monitor DB changes and auto-backup."""
        if self.observer is not None:
            return
            
        if not os.path.exists(self.project_dir):
            return

        self.observer = Observer()
        handler = DBChangeHandler(self, interval_minutes)
        self.observer.schedule(handler, path=self.project_dir, recursive=False)
        self.observer.start()

    def stop_auto_backup(self):
        """Stops the background auto-backup watchdog."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None

    def create_snapshot(self, label=None):
        """
        Creates a versioned snapshot of the project database.
        
        Args:
            label (str): Optional label (e.g. 'auto', 'before_major_change')
        """
        if not os.path.exists(self.project_db_path):
            return None

        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"snapshot_{label}_" if label else "snapshot_"
        backup_name = f"{prefix}{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            # Using copy2 to preserve metadata
            shutil.copy2(self.project_db_path, backup_path)
            self._rotate_backups()
            return backup_path
        except Exception as e:
            print(f"Backup Error: {e}")
            return None

    def _rotate_backups(self):
        """Keeps only the last N backups to manage disk space."""
        pattern = os.path.join(self.backup_dir, "snapshot_*.db")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime)
        
        while len(backups) > self.max_backups:
            old_backup = backups.pop(0)
            try:
                os.remove(old_backup)
            except Exception as e:
                print(f"Rotation Error: {e}")

    def list_snapshots(self):
        """Lists available snapshots sorted by most recent first."""
        if not os.path.exists(self.backup_dir):
            return []
        pattern = os.path.join(self.backup_dir, "snapshot_*.db")
        return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    def restore_snapshot(self, snapshot_path):
        """
        Restores a snapshot to the main database file.
        Always creates a 'safety' snapshot of the current state before restoring.
        """
        if not os.path.exists(snapshot_path):
            return False
            
        # Create safety snapshot before overwriting
        self.create_snapshot(label="pre_restore_safety")
        
        try:
            shutil.copy2(snapshot_path, self.project_db_path)
            return True
        except Exception as e:
            print(f"Restore Error: {e}")
            return False

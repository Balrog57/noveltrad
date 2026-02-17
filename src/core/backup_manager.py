import os
import shutil
import datetime
import glob

class BackupManager:
    """Handles automatic versioned snapshots for NovelTrad projects."""
    
    def __init__(self, project_db_path, max_backups=10):
        self.project_db_path = project_db_path
        self.max_backups = max_backups
        self.project_dir = os.path.dirname(project_db_path)
        self.backup_dir = os.path.join(self.project_dir, ".snapshots")

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

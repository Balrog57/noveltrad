"""
BackupManager++ for NovelTrad OmegaT-compliant projects.
Features automatic snapshots, pre-modification backups, and watchdog integration.
"""

import os
import shutil
import glob
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass
import json

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: Watchdog not available. Install with: pip install watchdog")


@dataclass
class SnapshotInfo:
    """Information about a backup snapshot."""
    path: str
    timestamp: datetime
    label: str
    size: int
    type: str


class PreModifySnapshotHandler:
    """Handles pre-modification snapshots."""
    
    def __init__(self, backup_manager: 'BackupManagerPlusPlus'):
        self.backup_manager = backup_manager
        self.pending_snapshots: Dict[str, str] = {}
    
    def create_for_segment(self, segment_id: str, segment_data: Dict[str, Any]) -> str:
        """Create snapshot before segment modification."""
        label = f"pre_mod_{segment_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        snapshot_path = self.backup_manager.create_snapshot(label=label)
        if snapshot_path:
            self.pending_snapshots[segment_id] = snapshot_path
        return snapshot_path
    
    def rollback(self, segment_id: str) -> bool:
        """Rollback to pre-modification state."""
        if segment_id not in self.pending_snapshots:
            return False
        
        snapshot_path = self.pending_snapshots.pop(segment_id)
        return self.backup_manager.restore_snapshot(snapshot_path)
    
    def confirm(self, segment_id: str) -> None:
        """Confirm modification and remove pending snapshot."""
        if segment_id in self.pending_snapshots:
            del self.pending_snapshots[segment_id]
    
    def get_pending_count(self) -> int:
        """Get count of pending snapshots."""
        return len(self.pending_snapshots)


class BackupManagerPlusPlus:
    """
    Advanced backup manager with automatic snapshots and watchdog integration.
    
    Features:
    - Automatic snapshots every N minutes (default: 3 min)
    - Pre-modification snapshots for segments
    - Automatic cleanup rotating snapshots (max: 10)
    - Watchdog integration for file change detection
    - Timestamped backups
    
    Attributes:
        project_dir: Project directory path
        snapshot_interval: Minutes between automatic snapshots (default: 3)
        max_snapshots: Maximum snapshots to keep (default: 10)
        enabled: Whether backup is enabled
    """
    
    def __init__(
        self,
        project_dir: str,
        snapshot_interval: int = 3,
        max_snapshots: int = 10,
        enabled: bool = True
    ):
        self.project_dir = Path(project_dir)
        self.noveltrad_dir = self.project_dir / ".noveltrad"
        self.snapshots_dir = self.noveltrad_dir / "snapshots"
        self.backup_dir = self.noveltrad_dir / "backup"
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        self.enabled = enabled
        
        self._observer: Optional[Observer] = None
        self._watchdog_handler: Optional['_WatchdogHandler'] = None
        self._watched_files: List[str] = []
        self._snapshot_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.pre_modify = PreModifySnapshotHandler(self)
        
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_snapshot(self, label: Optional[str] = None) -> Optional[str]:
        """
        Create a snapshot of the project.
        
        Args:
            label: Optional label (e.g., 'auto', 'manual', 'pre_mod_123')
            
        Returns:
            Path to snapshot or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            prefix = f"snapshot_{label}_" if label else "snapshot_"
            snapshot_name = f"{prefix}{timestamp}.tmx"
            snapshot_path = self.snapshots_dir / snapshot_name
            
            tmx_source = self.noveltrad_dir / "project_save.tmx"
            if not tmx_source.exists():
                return None
            
            shutil.copy2(tmx_source, snapshot_path)
            self._rotate_snapshots()
            
            return str(snapshot_path)
            
        except Exception as e:
            print(f"Snapshot Error: {e}")
            return None
    
    def create_pre_mod_snapshot(self, segment_id: str, segment_data: Dict[str, Any]) -> Optional[str]:
        """
        Create snapshot before segment modification.
        
        Args:
            segment_id: Segment identifier
            segment_data: Current segment data
            
        Returns:
            Path to snapshot
        """
        return self.pre_modify.create_for_segment(segment_id, segment_data)
    
    def cleanup(self, max_snapshots: Optional[int] = None) -> int:
        """
        Cleanup old snapshots and keep only the most recent ones.
        
        Args:
            max_snapshots: Maximum snapshots to keep (default: instance value)
            
        Returns:
            Number of snapshots removed
        """
        if max_snapshots is None:
            max_snapshots = self.max_snapshots
        
        pattern = str(self.snapshots_dir / "snapshot_*.tmx")
        snapshots = sorted(glob.glob(pattern), key=os.path.getmtime)
        
        removed = 0
        while len(snapshots) > max_snapshots:
            old_snapshot = snapshots.pop(0)
            try:
                os.remove(old_snapshot)
                removed += 1
            except Exception as e:
                print(f"Cleanup Error: {e}")
        
        return removed
    
    def _rotate_snapshots(self) -> None:
        """Internal rotation method called after each snapshot."""
        self.cleanup()
    
    def list_snapshots(self) -> List[SnapshotInfo]:
        """List all snapshots sorted by most recent first."""
        pattern = str(self.snapshots_dir / "snapshot_*.tmx")
        snapshot_paths = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        
        snapshots = []
        for path in snapshot_paths:
            try:
                stat = os.stat(path)
                filename = os.path.basename(path)
                
                label = "auto"
                if "pre_mod_" in filename:
                    label = "pre_mod"
                elif "_manual_" in filename:
                    label = "manual"
                
                ts_str = filename.split('_')[-1].replace('.tmx', '')
                try:
                    timestamp = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                except ValueError:
                    timestamp = datetime.fromtimestamp(stat.st_mtime)
                
                snapshots.append(SnapshotInfo(
                    path=path,
                    timestamp=timestamp,
                    label=label,
                    size=stat.st_size,
                    type="tmx"
                ))
            except Exception as e:
                print(f"Snapshot Info Error: {e}")
        
        return snapshots
    
    def restore_snapshot(self, snapshot_path: str) -> bool:
        """
        Restore a snapshot to the main TMX file.
        
        Always creates a 'safety' snapshot of current state before restoring.
        
        Args:
            snapshot_path: Path to snapshot to restore
            
        Returns:
            Success status
        """
        if not os.path.exists(snapshot_path):
            return False
        
        current_snapshot = self.create_snapshot(label="pre_restore_safety")
        if not current_snapshot:
            print("Warning: Could not create pre-restore safety snapshot")
        
        try:
            tmx_target = self.noveltrad_dir / "project_save.tmx"
            shutil.copy2(snapshot_path, tmx_target)
            
            backup_path = self.backup_dir / f"restored_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tmx"
            shutil.copy2(tmx_target, backup_path)
            
            return True
            
        except Exception as e:
            print(f"Restore Error: {e}")
            return False
    
    def watch_files(self, files: List[str]) -> None:
        """
        Start watching files for changes.
        
        Args:
            files: List of file paths to watch
        """
        if not WATCHDOG_AVAILABLE:
            print("Watchdog not available. Install with: pip install watchdog")
            return
        
        if self._observer is None:
            self._watchdog_handler = _WatchdogHandler(self)
            self._observer = Observer()
            self._observer.schedule(self._watchdog_handler, str(self.noveltrad_dir), recursive=True)
        
        for file in files:
            if file not in self._watched_files:
                self._watched_files.append(file)
        
        if not self._observer.is_alive():
            self._observer.start()
    
    def stop_watching(self) -> None:
        """Stop watching files."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._watchdog_handler = None
            self._watched_files.clear()
    
    def start_auto_snapshots(self) -> None:
        """Start automatic snapshots in background thread."""
        if self._snapshot_thread and self._snapshot_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._snapshot_thread = threading.Thread(
            target=self._auto_snapshot_loop,
            daemon=True
        )
        self._snapshot_thread.start()
    
    def stop_auto_snapshots(self) -> None:
        """Stop automatic snapshots."""
        self._stop_event.set()
        if self._snapshot_thread:
            self._snapshot_thread.join(timeout=5)
            self._snapshot_thread = None
    
    def _auto_snapshot_loop(self) -> None:
        """Background loop for automatic snapshots."""
        last_snapshot = datetime.utcnow()
        
        while not self._stop_event.is_set():
            time.sleep(60)
            
            now = datetime.utcnow()
            elapsed = (now - last_snapshot).total_seconds()
            
            if elapsed >= self.snapshot_interval * 60:
                snapshot_path = self.create_snapshot(label="auto")
                if snapshot_path:
                    print(f"Auto-snapshot created: {snapshot_path}")
                last_snapshot = now
    
    def get_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        snapshots = self.list_snapshots()
        
        total_size = 0
        for snap in snapshots:
            if os.path.exists(snap.path):
                total_size += os.path.getsize(snap.path)
        
        return {
            'enabled': self.enabled,
            'snapshot_interval': self.snapshot_interval,
            'max_snapshots': self.max_snapshots,
            'total_snapshots': len(snapshots),
            'total_size_bytes': total_size,
            'backup_dir': str(self.backup_dir),
            'snapshots_dir': str(self.snapshots_dir),
            'pending_pre_mod': self.pre_modify.get_pending_count(),
        }


class _WatchdogHandler(FileSystemEventHandler):
    """Watchdog event handler for backup manager."""
    
    def __init__(self, backup_manager: BackupManagerPlusPlus):
        super().__init__()
        self.backup_manager = backup_manager
    
    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        
        if event.src_path.endswith('.tmx'):
            self.backup_manager.create_snapshot(label="file_change")
    
    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and event.src_path.endswith('.tmx'):
            self.backup_manager.create_snapshot(label="file_create")


if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManagerPlusPlus(
            project_dir=tmpdir,
            snapshot_interval=1,
            max_snapshots=5,
            enabled=True
        )
        
        print(f"Project dir: {tmpdir}")
        print(f"Snapshots dir: {manager.snapshots_dir}")
        print(f"Backup dir: {manager.backup_dir}")
        
        manager.start_auto_snapshots()
        
        for i in range(3):
            snapshot = manager.create_snapshot(label=f"test_{i}")
            if snapshot:
                print(f"Created: {snapshot}")
            time.sleep(1.5)
        
        snapshots = manager.list_snapshots()
        print(f"\nTotal snapshots: {len(snapshots)}")
        for snap in snapshots:
            print(f"  {snap.label}: {snap.timestamp}")
        
        stats = manager.get_stats()
        print(f"\nStats: {json.dumps(stats, indent=2, default=str)}")
        
        manager.stop_auto_snapshots()
        manager.cleanup()
        
        print(f"\nAfter cleanup: {len(manager.list_snapshots())} snapshots")

import os
import glob
from typing import Optional, Dict
from src.core.tmx_handler import TMXHandler

class EnforceTMManager:
    """
    Manages Translation Memories from the tm/enforce/ directory.
    Enforce TM contains 100% exact matches that MUST overwrite any existing target text.
    """
    def __init__(self):
        self.tm_data: Dict[str, str] = {}
        self.directory = "tm/enforce/"

    def load_tmx_files(self, base_project_dir: str):
        """Loads all TMX files from the project's tm/enforce/ directory."""
        self.tm_data.clear()
        target_dir = os.path.join(base_project_dir, ".noveltrad", *self.directory.split('/'))
        
        if not os.path.exists(target_dir):
            return

        tmx_files = glob.glob(os.path.join(target_dir, "*.tmx"))
        for file_path in tmx_files:
            pairs = TMXHandler.import_tmx(file_path)
            for src, tgt in pairs:
                self.tm_data[src.strip()] = tgt.strip()

    def enforce_translation(self, source_text: str) -> Optional[str]:
        """Returns the target text if an exact match is found in the Enforce TM."""
        if not source_text:
            return None
        return self.tm_data.get(source_text.strip())

    def force_replace(self, segment, target_text: str) -> None:
        """
        Forces the replacement of the target text of a segment, overwriting it entirely.
        """
        from src.core.database import SegmentStatus
        segment.target_text = target_text
        segment.status = SegmentStatus.VERIFIED.value # Force as verified since it's Enforced
        segment.save()

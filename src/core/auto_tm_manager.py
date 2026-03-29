import os
import glob
from typing import Optional, Dict
from src.core.tmx_handler import TMXHandler

class AutoTMManager:
    """
    Manages Translation Memories from the tm/auto/ directory.
    Auto TM allows exact matches to be automatically inserted without user confirmation,
    but it will NOT overwrite segments that are already translated.
    """
    def __init__(self):
        self.tm_data: Dict[str, str] = {}
        self.directory = "tm/auto/"

    def load_tmx_files(self, base_project_dir: str):
        """Loads all TMX files from the project's tm/auto/ directory."""
        self.tm_data.clear()
        target_dir = os.path.join(base_project_dir, ".noveltrad", *self.directory.split('/'))
        
        if not os.path.exists(target_dir):
            return

        tmx_files = glob.glob(os.path.join(target_dir, "*.tmx"))
        for file_path in tmx_files:
            pairs = TMXHandler.import_tmx(file_path)
            for src, tgt in pairs:
                self.tm_data[src.strip()] = tgt.strip()

    def search_exact_match(self, source_text: str) -> Optional[str]:
        """Returns the target text if an exact match is found in the Auto TM."""
        if not source_text:
            return None
        return self.tm_data.get(source_text.strip())

    def insert_auto(self, segment) -> bool:
        """
        Attempts to auto-insert a translation for a segment if an exact match is found
        and the segment is not already translated.
        Returns True if successful, False otherwise.
        """
        match = self.search_exact_match(segment.source_text)
        if match:
            # Do not overwrite if already translated
            from src.core.segment_status import SegmentStatus
            if segment.status in [SegmentStatus.MACHINE.value, SegmentStatus.AI_REFINED.value, SegmentStatus.VALIDATED.value]:
                return False
                
            segment.target_text = match
            segment.status = SegmentStatus.MACHINE.value
            segment.save()
            return True
        return False

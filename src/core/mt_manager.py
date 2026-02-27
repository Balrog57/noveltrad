import os
import glob
from typing import List, Dict
from src.core.tmx_handler import TMXHandler
from src.core.fuzzy_scoring import FuzzyScorer

class MTManager:
    """
    Manages Translation Memories from the tm/mt/ directory.
    MT matches are usually highlighting in red or considered less reliable.
    """
    def __init__(self):
        self.tm_data: Dict[str, str] = {}
        self.directory = "tm/mt/"
        self.scorer = FuzzyScorer()

    def load_tmx_files(self, base_project_dir: str):
        """Loads all TMX files from the project's tm/mt/ directory."""
        self.tm_data.clear()
        target_dir = os.path.join(base_project_dir, ".noveltrad", *self.directory.split('/'))
        
        if not os.path.exists(target_dir):
            return

        tmx_files = glob.glob(os.path.join(target_dir, "*.tmx"))
        for file_path in tmx_files:
            pairs = TMXHandler.import_tmx(file_path)
            for src, tgt in pairs:
                self.tm_data[src.strip()] = tgt.strip()

    def get_mt_suggestions(self, source_text: str, threshold: int = 50) -> List[Dict]:
        """
        Returns a list of MT suggestions for the given source text using fuzzy matching.
        """
        if not source_text:
            return []
        
        return self.scorer.get_fuzzy_matches(source_text, self.tm_data, threshold=threshold, penalty=0)

    def mark_as_mt(self, segment, mt_data: Dict) -> None:
        """
        Marks a segment as being translated by Machine Translation.
        Adds the prefix/suffix [MT] or sets a specific status flag if supported by the DB.
        """
        from src.core.database import SegmentStatus
        segment.target_text = mt_data['target']
        # Pending a specific status, fallback to TRANSLATED or leave UNTRANSLATED for manual review.
        # OmegaT usually treats MT as fuzzy matches requires review.
        segment.status = SegmentStatus.UNTRANSLATED.value
        segment.save()

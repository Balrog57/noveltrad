import os
from typing import Optional, Dict
from src.core.tmx_handler import TMXHandler

class Tmx2SourceManager:
    """
    Manages a reference TMX file (e.g., Japanese original for an EN->FR project)
    to display a third language as context underneath the main source text.
    """
    def __init__(self):
        self.reference_data: Dict[str, str] = {}
        self.current_mode = "normal"  # "normal" or "reference_below"

    def load_reference_tmx(self, tmx_path: str):
        """Loads a TMX file and caches its source-to-target mapping for exact matches."""
        self.reference_data.clear()
        if not os.path.exists(tmx_path):
            return

        try:
            # We assume the TMX source matches our project source exactly, 
            # and the target is the reference language.
            segments = TMXHandler.read_tmx_fast(tmx_path)
            for seg in segments:
                src = seg.get('source_text')
                tgt = seg.get('target_text')
                if src and tgt:
                    self.reference_data[src] = tgt
        except Exception as e:
            print(f"Error loading reference TMX {tmx_path}: {e}")

    def get_reference_text(self, source_text: str) -> Optional[str]:
        """Returns the reference text for a given source text if available."""
        if not source_text:
            return None
        return self.reference_data.get(source_text)

    def display_mode(self, mode: str):
        """Sets the display mode (normal or reference_below)."""
        if mode in ["normal", "reference_below"]:
            self.current_mode = mode

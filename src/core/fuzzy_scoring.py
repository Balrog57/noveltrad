from difflib import SequenceMatcher
from typing import List, Dict

class FuzzyScorer:
    """
    Handles fuzzy matching and scoring for translation memories.
    Applies penalties for matches coming from specific directories (e.g., penalty-030).
    """
    
    @staticmethod
    def calculate_score(source1: str, source2: str, penalty_percent: int = 0) -> int:
        """
        Calculates the similarity score between two strings using difflib.
        Returns a score from 0 to 100, minus any penalty.
        """
        if not source1 or not source2:
            return 0
            
        # Basic SequenceMatcher ratio
        ratio = SequenceMatcher(None, source1.lower(), source2.lower()).ratio()
        base_score = int(ratio * 100)
        
        # Apply penalty
        final_score = max(0, base_score - penalty_percent)
        return final_score

    def get_fuzzy_matches(self, search_text: str, tm_data: Dict[str, str], threshold: int = 75, penalty: int = 0) -> List[Dict]:
        """
        Searches a TM dictionary for fuzzy matches above a given threshold.
        Returns a list of dicts: [{'source': ..., 'target': ..., 'score': ...}]
        Sorted by score (descending).
        """
        matches = []
        for src, tgt in tm_data.items():
            score = self.calculate_score(search_text, src, penalty)
            if score >= threshold:
                matches.append({
                    'source': src,
                    'target': tgt,
                    'score': score
                })
                
        # Sort by best score first
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches

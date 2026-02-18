"""
Structure AI - Automatic chapter detection for NovelTrad.
Detects chapter boundaries in raw text files using pattern matching and LLM analysis.
Conforms to §12.3 of the specification.
"""
import re
from typing import List, Dict, Tuple, Optional


class StructureAI:
    """Automatic structure detection for novels."""

    # Common chapter title patterns
    CHAPTER_PATTERNS = [
        # English
        r'^(?:chapter|chap\.?)\s*(\d+|[ivxlcdm]+)',
        r'^chapter\s+(\d+|[ivxlcdm]+)[\s:]+(.+)',
        r'^Part\s+(\d+|[ivxlcdm]+)',
        r'^Book\s+(\d+|[ivxlcdm]+)',
        # French
        r'^chapitre\s*(\d+|[ivxlcdm]+)',
        r'^chapitre\s*(\d+|[ivxlcdm]+)[\s:]+(.+)',
        r'^première\s+partie|deuxième\s+partie|troisième\s+partie',
        # Chinese
        r'^第(\d+)[章节篇部]',
        r'^(?:章|节|卷)\s*(\d+|[一二三四五六七八九十百千]+)',
        # Japanese
        r'^第(\d+)章',
        r'^第(\d+)話',
    ]

    def __init__(self, llm_engine=None):
        self.llm_engine = llm_engine

    def detect_chapters(self, text: str) -> List[Dict]:
        """
        Detect chapter boundaries in raw text.
        
        Args:
            text: Raw text content
            
        Returns:
            List of chapter dicts with 'title', 'start_pos', 'end_pos', 'suggested_name'
        """
        chapters = []
        lines = text.split('\n')
        
        current_chapter = None
        current_start = 0
        line_positions = []
        
        # Build line position index
        pos = 0
        for i, line in enumerate(lines):
            line_positions.append(pos)
            pos += len(line) + 1
        
        # Detect chapter boundaries
        for i, line in enumerate(lines):
            chapter_info = self._is_chapter_start(line.strip())
            if chapter_info:
                # Save previous chapter
                if current_chapter is not None:
                    chapters.append({
                        'title': current_chapter,
                        'start_pos': current_start,
                        'end_pos': line_positions[i] - 1,
                        'suggested_name': current_chapter
                    })
                # Start new chapter
                current_chapter = chapter_info.get('title') or f"Chapter {chapter_info.get('number', len(chapters) + 1)}"
                current_start = line_positions[i]
        
        # Add final chapter
        if current_chapter is not None:
            chapters.append({
                'title': current_chapter,
                'start_pos': current_start,
                'end_pos': len(text),
                'suggested_name': current_chapter
            })
        
        # If no chapters detected, split by size
        if not chapters:
            chapters = self._split_by_size(text)
        
        return chapters

    def _is_chapter_start(self, line: str) -> Optional[Dict]:
        """Check if line is a chapter start."""
        line_lower = line.lower()
        
        for pattern in self.CHAPTER_PATTERNS:
            match = re.match(pattern, line_lower, re.IGNORECASE)
            if match:
                return {
                    'title': line.strip(),
                    'number': match.group(1) if match.groups() else None
                }
        
        return None

    def _split_by_size(self, text: str, chunk_size: int = 50000) -> List[Dict]:
        """Split text by size if no chapters detected."""
        chapters = []
        pos = 0
        chapter_num = 1
        
        while pos < len(text):
            end_pos = min(pos + chunk_size, len(text))
            # Try to end at paragraph boundary
            while end_pos < len(text) and text[end_pos] != '\n':
                end_pos += 1
            
            chapters.append({
                'title': f"Chapter {chapter_num}",
                'start_pos': pos,
                'end_pos': end_pos,
                'suggested_name': f"Chapter {chapter_num}"
            })
            pos = end_pos + 1
            chapter_num += 1
        
        return chapters

    async def detect_with_llm(self, text: str, genre: str = "general") -> List[Dict]:
        """
        Use LLM to detect chapter structure for complex cases.
        
        Args:
            text: Text to analyze
            genre: Novel genre (xianxia, scifi, fantasy, romance, general)
            
        Returns:
            List of detected chapters with AI-suggested names
        """
        if not self.llm_engine:
            return self.detect_chapters(text)
        
        # Sample text for analysis (first 10000 chars)
        sample = text[:10000]
        
        prompt = f"""Analyze the following text from a {genre} novel and identify chapter boundaries.
Return a JSON array of chapters, each with:
- "title": The chapter number/title as it appears
- "start_marker": A unique phrase that marks the start of this chapter
- "suggested_name": A clean English name for the chapter

Text:
{sample}

Respond with only JSON."""

        try:
            result = await self.llm_engine.translate(prompt, "auto", "en")
            # Parse JSON result
            import json
            chapters_data = json.loads(result)
            return chapters_data
        except Exception as e:
            # Fallback to pattern matching
            return self.detect_chapters(text)

    def get_chapter_text(self, text: str, chapter: Dict) -> str:
        """Extract text for a specific chapter."""
        return text[chapter['start_pos']:chapter['end_pos']]

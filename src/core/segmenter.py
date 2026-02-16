"""
Moteur de segmentation pour NovelTrad.
Découpe le texte en segments (phrases) selon des règles configurables par langue.
Conforme au cahier des charges §13.1.
"""
import re


# Abbreviations that should NOT trigger a sentence break
ABBREVIATIONS = {
    'fr': {
        'M', 'Mme', 'Mlle', 'Dr', 'Pr', 'Prof', 'Sr', 'Jr',
        'St', 'Ste', 'etc', 'vol', 'chap', 'p', 'pp', 'fig',
        'av', 'apr', 'J.-C', 'cf', 'éd', 'trad', 'nb',
        'ex', 'min', 'max', 'env', 'c.-à-d',
    },
    'en': {
        'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr',
        'St', 'etc', 'vol', 'chap', 'p', 'pp', 'fig',
        'vs', 'e.g', 'i.e', 'al', 'dept', 'approx',
        'Gen', 'Gov', 'Sgt', 'Cpl', 'Lt', 'Capt', 'Col',
    },
    'default': {
        'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr',
        'St', 'etc', 'vol', 'chap', 'p', 'pp', 'fig',
    },
}

# CJK sentence-ending punctuation
CJK_TERMINATORS = '。！？'

# CJK Unicode ranges
CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x3000, 0x303F),    # CJK Symbols and Punctuation
    (0x3040, 0x309F),    # Hiragana
    (0x30A0, 0x30FF),    # Katakana
    (0xAC00, 0xD7AF),    # Hangul Syllables
    (0xFF00, 0xFFEF),    # Fullwidth Forms
]


def _is_cjk_char(char):
    """Check if a character is in a CJK Unicode range."""
    cp = ord(char)
    return any(start <= cp <= end for start, end in CJK_RANGES)


def _is_cjk_text(text):
    """Heuristic: text is CJK if >30% of non-space chars are CJK."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return False
    cjk_count = sum(1 for c in chars if _is_cjk_char(c))
    return cjk_count / len(chars) > 0.3


class Segmenter:
    """
    Découpe un texte en segments (phrases) selon des règles de segmentation
    configurables par langue.

    Usage:
        segmenter = Segmenter()
        segments = segmenter.segment("Hello world. How are you?", lang='en')
        # -> ["Hello world.", "How are you?"]
    """

    def __init__(self, custom_abbreviations=None):
        """
        Args:
            custom_abbreviations: dict[str, set[str]] — custom abbreviations
                                  per language to merge with defaults.
        """
        self.abbreviations = {}
        for lang, abbrevs in ABBREVIATIONS.items():
            self.abbreviations[lang] = set(abbrevs)

        if custom_abbreviations:
            for lang, abbrevs in custom_abbreviations.items():
                if lang in self.abbreviations:
                    self.abbreviations[lang].update(abbrevs)
                else:
                    self.abbreviations[lang] = set(abbrevs)

    def _get_abbreviations(self, lang):
        """Get abbreviation set for the given language."""
        lang_short = lang.split('-')[0].split('_')[0].lower()
        return self.abbreviations.get(lang_short, self.abbreviations['default'])

    def segment(self, text, lang='en'):
        """
        Segment text into sentences.

        Args:
            text: The text to segment.
            lang: ISO language code (e.g., 'en', 'fr', 'zh', 'ja', 'ko').

        Returns:
            list[str]: List of sentence segments (stripped, non-empty).
        """
        if not text or not text.strip():
            return []

        lang_short = lang.split('-')[0].split('_')[0].lower()

        # Use CJK segmentation if the lang is CJK or text contains CJK
        if lang_short in ('zh', 'ja', 'ko') or _is_cjk_text(text):
            return self._segment_cjk(text)
        else:
            return self._segment_latin(text, lang)

    def _segment_latin(self, text, lang='en'):
        """Segment Latin-script text using punctuation rules with exceptions."""
        abbreviations = self._get_abbreviations(lang)

        # Regex: split on sentence-ending punctuation followed by space or end
        # The pattern captures: punctuation (. ! ?) optionally followed by
        # closing quotes/parens, then whitespace or end-of-string
        segments = []
        current = []
        tokens = re.split(r'(\S+)', text)

        for token in tokens:
            if not token:
                continue

            current.append(token)
            stripped = token.strip()

            if not stripped:
                continue

            # Check if this token ends a sentence
            if self._is_sentence_end(stripped, abbreviations):
                sentence = ''.join(current).strip()
                if sentence:
                    segments.append(sentence)
                current = []

        # Don't forget the last segment
        if current:
            sentence = ''.join(current).strip()
            if sentence:
                segments.append(sentence)

        return segments

    def _is_sentence_end(self, token, abbreviations):
        """
        Determine if a token marks the end of a sentence.
        Handles abbreviations, ellipsis, and quoted endings.
        """
        if not token:
            return False

        # Strip trailing quotes and parentheses for analysis
        clean = token.rstrip('»"\'")')

        if not clean:
            return False

        last_char = clean[-1]

        # Exclamation and question marks always end sentences
        if last_char in '!?':
            return True

        # Ellipsis (... or …) ends a sentence
        if clean.endswith('...') or clean.endswith('…'):
            return True

        # Period: check it's not an abbreviation
        if last_char == '.':
            # Get the word before the period
            word_before_dot = clean[:-1]

            # Single letter abbreviation (e.g., "M.", "J.")
            if len(word_before_dot) == 1 and word_before_dot.isupper():
                return False

            # Known abbreviation
            if word_before_dot in abbreviations:
                return False

            # Initials like "J.-C." or "U.S.A."
            if re.match(r'^([A-Z]\.)+$', clean):
                return False

            # Number followed by dot (e.g., "1.", "42.") - could be a list
            if word_before_dot.isdigit():
                return False

            return True

        return False

    def _segment_cjk(self, text):
        """
        Segment CJK text using CJK sentence-ending punctuation.
        Also handles embedded Latin punctuation.
        """
        # Split on CJK terminators AND standard terminators
        pattern = f'([{re.escape(CJK_TERMINATORS)}!?])'
        parts = re.split(pattern, text)

        segments = []
        current = ''

        for part in parts:
            current += part
            if part and part in CJK_TERMINATORS + '!?':
                segment = current.strip()
                if segment:
                    segments.append(segment)
                current = ''

        # Remainder
        if current.strip():
            segments.append(current.strip())

        return segments

    @staticmethod
    def join_segments(segments, separator='\n'):
        """
        Join segments back into text.

        Args:
            segments: List of segment strings.
            separator: String to join with (default: newline).

        Returns:
            str: Joined text.
        """
        return separator.join(segments)

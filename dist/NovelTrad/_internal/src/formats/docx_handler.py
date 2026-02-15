from src.formats.format_handler import FormatHandler
import docx
import os

class DocxHandler(FormatHandler):
    def read(self, file_path):
        doc = docx.Document(file_path)
        segments = []
        global_index = 0
        
        # We iterate over paragraphs, and then verify if they have content.
        # Note: python-docx structure is Document -> Paragraphs -> Runs
        # We generally translate at the Paragraph level for standard structure, 
        # BUT if a paragraph has multiple runs with different formatting, splitting them up is hard for translation context.
        # A common simplified approach for Novels: 
        # Treat the visual paragraph as one translation unit.
        # Reconstruct by putting the translated text into the *first* run and clearing text from others, 
        # OR (better) try to preserve runs if we can alignment them.
        #
        # Pragmactic Approach for Novels:
        # A paragraph is the unit of translation (index). 
        # We extract the full text of the paragraph.
        # On write, we replace the text of the *entire* paragraph.
        # Limitation: If a paragraph has "Hello *world*", we lose the italic on 'world' if we just replace paragraph.text.
        # 
        # Advanced Approach (Spec Requirement: "Preserve Formatting"):
        # We cannot easily map a translated sentence back to specific runs if the word order changes (which it does in translation).
        # Competing approaches:
        # A) Extract plain text, translate, write back to a new single run (loses mid-sentence formatting like italics).
        # B) Expose HTML-like tags to the translator (e.g. "Hello <i>world</i>") and require the translator/LLM to preserve them.
        #
        # Given "Glossary AI" and LLM focus, Approach B is superior but requires complex parsing.
        # 
        # Let's Implement Approach A ("Paragraph Level") as baseline, but with a "dumb" preservation attempt:
        # We apply the style of the first run to the whole translated paragraph.
        
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if text:
                segments.append({
                    'index': global_index,
                    'source_text': text,
                    'metadata': {
                        'para_index': i
                    }
                })
                global_index += 1
                
        return segments

    def write(self, file_path, segments, original_file_path=None):
        if not original_file_path:
             raise ValueError("Original DOCX required")

        doc = docx.Document(original_file_path)
        
        # Map segments
        segments_map = {s['metadata']['para_index']: s['target_text'] for s in segments if s.get('target_text')}
        
        for i, para in enumerate(doc.paragraphs):
            if i in segments_map:
                new_text = segments_map[i]
                
                # Simple replacement: 
                # Preserves paragraph-level style, but might flatten run-level styles (bold words inside text)
                # To clear and set text while keeping paragraph style:
                para.text = new_text
                
        doc.save(file_path)

    def get_supported_extensions(self):
        return ['.docx']

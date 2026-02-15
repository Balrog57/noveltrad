from src.core.database import init_db, Project, Chapter, Segment, GlossaryTerm, TranslationMemory
from src.formats.txt_handler import TxtHandler
from src.formats.epub_handler import EpubHandler
from src.formats.docx_handler import DocxHandler
from src.formats.pdf_handler import PdfHandler
import os
import json

class ProjectManager:
    def __init__(self):
        self.current_project = None
        self.db = None
        self.handlers = {
            '.txt': TxtHandler(),
            '.epub': EpubHandler(),
            '.docx': DocxHandler(),
            '.pdf': PdfHandler()
        }

    def create_project(self, name, db_path, source_file, source_lang='en', target_lang='fr'):
        """Creates a new project database and initializes it with segments from source_file."""
        self.db = init_db(db_path)
        
        # Determine handler
        _, ext = os.path.splitext(source_file)
        handler = self.handlers.get(ext.lower())
        if not handler:
             # Try to find a handler that supports this extension
             for h in self.handlers.values():
                 if ext.lower() in h.get_supported_extensions():
                     handler = h
                     break
        
        if not handler:
            raise ValueError(f"No handler found for file type: {ext}")

        # Create Project Record
        self.current_project = Project.create(
            name=name,
            source_language=source_lang,
            target_language=target_lang,
            file_path=source_file
        )
        
        # Import Segments
        segments_data = handler.read(source_file)
        self.import_segments(segments_data)
        
        return self.current_project

    def import_segments(self, segments_data):
        # Determine chapters based on metadata or default to single chapter
        current_chapter = None
        chapter_map = {} # item_name -> Chapter
        default_chapter = None

        # Pre-create default chapter if needed (for non-hierarchical formats)
        # But we don't know if we need it until we see data without item_name
        
        # We need to iterate and create chapters as we go or pre-process
        # Pre-process to identify chapters
        
        # Sort of optimized approach:
        # Just check the first segment? No, mixed content possible?
        # Let's just create chapters on the fly and cache them in chapter_map
        
        batch_size = 100
        for i in range(0, len(segments_data), batch_size):
            batch = segments_data[i:i+batch_size]
            with self.db.atomic():
                for data in batch:
                    meta = data.get('metadata')
                    chapter = None
                    
                    if meta and 'item_name' in meta:
                        item_name = meta['item_name']
                        if item_name not in chapter_map:
                            # Create new chapter
                            # Order index could be strictly increasing based on segment appearance
                            chapter = Chapter.create(
                                project=self.current_project,
                                title=item_name, # Use item name as title (e.g. chapter1.html)
                                order_index=len(chapter_map) + 1
                            )
                            chapter_map[item_name] = chapter
                        chapter = chapter_map[item_name]
                    else:
                        if not default_chapter:
                             default_chapter = Chapter.create(
                                 project=self.current_project,
                                 title="Main Content",
                                 order_index=0
                             )
                        chapter = default_chapter

                    Segment.create(
                        project=self.current_project,
                        chapter=chapter,
                        index=data['index'],
                        source_text=data['source_text'],
                        metadata=json.dumps(meta) if meta else None
                    )

    def load_project(self, db_path):
        """Loads an existing project database."""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Project interface not found at {db_path}")
            
        self.db = init_db(db_path)
        self.current_project = Project.select().first()
        return self.current_project

    def add_segment(self, source_text, index):
        if not self.current_project:
            raise ValueError("No active project")
            
        return Segment.create(
            project=self.current_project,
            index=index,
            source_text=source_text
        )

    def get_segments(self, chapter_id=None):
        if not self.current_project:
            return []
        if chapter_id:
             return list(Segment.select().where((Segment.project == self.current_project) & (Segment.chapter_id == chapter_id)).order_by(Segment.index))
        return list(self.current_project.all_segments)

    def get_chapters(self):
        if not self.current_project:
            return []
        return list(self.current_project.chapters.order_by(Chapter.order_index))

    def save_translation(self, segment_id, target_text):
        segment = Segment.get_by_id(segment_id)
        segment.target_text = target_text
        segment.status = 'translated'
        segment.save()

    def export_project(self, output_path):
        """Exports the current project to the target format."""
        if not self.current_project or not self.current_project.file_path:
            raise ValueError("No active project or source file missing")
            
        _, ext = os.path.splitext(self.current_project.file_path)
        handler = self.handlers.get(ext.lower())
        
        if not handler:
             for h in self.handlers.values():
                 if ext.lower() in h.get_supported_extensions():
                     handler = h
                     break
        
        if not handler:
            raise ValueError(f"No handler found for export format: {ext}")
            
        # Get all segments, ordered by index
        segments = Segment.select().where(Segment.project == self.current_project).order_by(Segment.index)
        
        # Prepare segments for handler - keep as objects or convert properly
        # The handler.write expects objects with target_text attribute
        valid_segments = []
        for seg in segments:
            valid_segments.append(seg)
            
        handler.write(output_path, valid_segments, original_file_path=self.current_project.file_path)

    def add_to_translation_memory(self, source_text, target_text, source_lang=None, target_lang=None):
        """Add a validated segment to translation memory."""
        if not self.current_project:
            return None
        src = source_lang or self.current_project.source_language
        tgt = target_lang or self.current_project.target_language
        return TranslationMemory.create(
            project=self.current_project,
            source_lang=src,
            target_lang=tgt,
            source_text=source_text,
            target_text=target_text
        )

    def search_translation_memory(self, text, source_lang=None, target_lang=None, threshold=60):
        """Search TM for similar segments using fuzzy matching."""
        if not self.current_project:
            return []
        src = source_lang or self.current_project.source_language
        tgt = target_lang or self.current_project.target_language
        
        results = TranslationMemory.select().where(
            (TranslationMemory.source_lang == src) &
            (TranslationMemory.target_lang == tgt)
        )
        
        matches = []
        for tm in results:
            similarity = self._calculate_similarity(text, tm.source_text)
            if similarity >= threshold:
                matches.append({
                    'source': tm.source_text,
                    'target': tm.target_text,
                    'similarity': similarity
                })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:10]

    def _calculate_similarity(self, s1, s2):
        """Calculate simple similarity percentage between two strings."""
        if not s1 or not s2:
            return 0
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 100
        
        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)
        if max_len == 0:
            return 100
        
        matches = sum(c1 == c2 for c1, c2 in zip(s1, s2))
        return int((matches / max_len) * 100)

    def export_tm(self, output_path):
        """Export translation memory to TMX format."""
        if not self.current_project:
            return
        
        tms = TranslationMemory.select().where(TranslationMemory.project == self.current_project)
        
        tmx_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        tmx_content += '<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n'
        tmx_content += '<tmx version="1.4">\n'
        tmx_content += '  <header creationtool="NovelTrad" datatype="plaintext"/>\n'
        tmx_content += '  <body>\n'
        
        for tm in tms:
            tmx_content += '    <tu>\n'
            tmx_content += f'      <tuv xml:lang="{tm.source_lang}"><seg>{self._escape_xml(tm.source_text)}</seg></tuv>\n'
            tmx_content += f'      <tuv xml:lang="{tm.target_lang}"><seg>{self._escape_xml(tm.target_text)}</seg></tuv>\n'
            tmx_content += '    </tu>\n'
        
        tmx_content += '  </body>\n'
        tmx_content += '</tmx>'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tmx_content)

    def import_tm(self, file_path):
        """Import translation memory from TMX format."""
        import xml.etree.ElementTree as ET
        
        count = 0
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for tu in root.findall('.//tu'):
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    src_lang = tuvs[0].get('{http://www.w3.org/XML/1998/namespace}lang') or tuvs[0].get('xml:lang', 'en')
                    tgt_lang = tuvs[1].get('{http://www.w3.org/XML/1998/namespace}lang') or tuvs[1].get('xml:lang', 'fr')
                    src_text = tuvs[0].find('seg').text or ''
                    tgt_text = tuvs[1].find('seg').text or ''
                    
                    if src_text and tgt_text:
                        TranslationMemory.create(
                            project=self.current_project,
                            source_lang=src_lang,
                            target_lang=tgt_lang,
                            source_text=src_text,
                            target_text=tgt_text
                        )
                        count += 1
        except Exception as e:
            print(f"TM Import Error: {e}")
        
        return count

    def _escape_xml(self, text):
        """Escape XML special characters."""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))



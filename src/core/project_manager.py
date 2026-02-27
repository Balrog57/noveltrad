from src.core.database import init_db, Project, Chapter, Segment, GlossaryTerm, TranslationMemory
from src.formats.txt_handler import TxtHandler
from src.formats.epub_handler import EpubHandler
from src.formats.docx_handler import DocxHandler
from src.formats.pdf_handler import PdfHandler
from src.core.tmx_handler import TMXHandler
from src.core.segment_status import SegmentStatus
from src.core.auto_tm_manager import AutoTMManager
from src.core.enforce_tm_manager import EnforceTMManager
from src.core.mt_manager import MTManager
from src.core.last_entry_manager import LastEntryManager
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
        self.auto_tm = AutoTMManager()
        self.enforce_tm = EnforceTMManager()
        self.mt_manager = MTManager()
        self.last_entry = None

    def create_project(self, name, db_path, source_file, source_lang='en', target_lang='fr', genre='general', custom_instructions=None):
        """Creates a new project database (file or directory)."""
        self.db = init_db(db_path)
        
        # Determine the project directory (which contains the db_path)
        project_dir = os.path.dirname(os.path.abspath(db_path))
        noveltrad_dir = os.path.join(project_dir, ".noveltrad")
        
        # 1. Create .noveltrad directory structure
        directories_to_create = [
            noveltrad_dir,
            os.path.join(noveltrad_dir, "tm", "enforce"),
            os.path.join(noveltrad_dir, "tm", "auto"),
            os.path.join(noveltrad_dir, "tm", "mt"),
            os.path.join(noveltrad_dir, "tm", "penalty-030"),
            os.path.join(noveltrad_dir, "tmx2source"),
            os.path.join(noveltrad_dir, ".repositories", "git"),
            os.path.join(noveltrad_dir, ".repositories", "svn"),
        ]
        
        for directory in directories_to_create:
            os.makedirs(directory, exist_ok=True)
            
        # 2. Create project.json
        from src.core.project_schema import ProjectSchema, Genre
        import re
        
        genre_enum = Genre.GENERAL
        if hasattr(Genre, str(genre).upper()):
             genre_enum = Genre[str(genre).upper()]
        elif genre.lower() == 'science fiction':
             genre_enum = Genre.SCIENCE_FICTION
             
        # Sanitize internal name (no spaces, pure alphanumeric + hyphen/underscore)
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        project_data = ProjectSchema(
            name=safe_name,
            title=name,
            source_lang=source_lang,
            target_lang=target_lang,
            genres=[genre_enum],
        )
        with open(os.path.join(noveltrad_dir, "project.json"), "w", encoding="utf-8") as f:
            f.write(project_data.model_dump_json(indent=2))
            
        # 3. Create initial project_save.tmx
        tmx_path = os.path.join(noveltrad_dir, "project_save.tmx")
        if not os.path.exists(tmx_path):
            TMXHandler.create_empty_tmx_v3(tmx_path, source_lang, target_lang, project_data.schema_version)
            
        # Create Project Record
        self.current_project = Project.create(
            name=name,
            source_language=source_lang,
            target_language=target_lang,
            genre=genre,
            custom_instructions=custom_instructions,
            file_path=source_file
        )

        if os.path.isdir(source_file):
            # Special case: Import directory (only .txt supported for now)
            txt_files = [f for f in os.listdir(source_file) if f.lower().endswith('.txt')]
            txt_files.sort()
            
            handler = self.handlers.get('.txt')
            for i, filename in enumerate(txt_files):
                full_path = os.path.join(source_file, filename)
                segments_data = handler.read(full_path)
                
                # Create a chapter for each file
                chapter = Chapter.create(
                    project=self.current_project,
                    title=filename,
                    order_index=i + 1
                )
                
                # Import segments to this specific chapter
                with self.db.atomic():
                    for data in segments_data:
                        Segment.create(
                            project=self.current_project,
                            chapter=chapter,
                            index=data['index'],
                            source_text=data['source_text'],
                            metadata=json.dumps(data.get('metadata')) if data.get('metadata') else None
                        )
        else:
            # Determine handler for single file
            _, ext = os.path.splitext(source_file)
            handler = self.handlers.get(ext.lower())
            if not handler:
                 for h in self.handlers.values():
                     if ext.lower() in h.get_supported_extensions():
                         handler = h
                         break
            
            if not handler:
                raise ValueError(f"No handler found for file type: {ext}")

            # Import Segments
            segments_data = handler.read(source_file)
            self.import_segments(segments_data)
        
        self.last_entry = LastEntryManager(noveltrad_dir)
        self.last_entry.set_last_project(db_path)
        
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

                    src_text = data['source_text']
                    tgt_text = None
                    status = SegmentStatus.UNTRANSLATED.value
                    
                    # Apply Translation Memories automatically
                    enforce_match = self.enforce_tm.enforce_translation(src_text)
                    if enforce_match:
                        tgt_text = enforce_match
                        status = SegmentStatus.VERIFIED.value
                    else:
                        auto_match = self.auto_tm.search_exact_match(src_text)
                        if auto_match:
                            tgt_text = auto_match
                            status = SegmentStatus.TRANSLATED.value

                    Segment.create(
                        project=self.current_project,
                        chapter=chapter,
                        index=data['index'],
                        source_text=src_text,
                        target_text=tgt_text,
                        status=status,
                        metadata=json.dumps(meta) if meta else None
                    )

    def import_file(self, file_path):
        """Imports a file as a new chapter in the current project."""
        if not self.current_project:
            raise ValueError("No active project")
            
        _, ext = os.path.splitext(file_path)
        handler = self.handlers.get(ext.lower())
        if not handler:
             for h in self.handlers.values():
                 if ext.lower() in h.get_supported_extensions():
                     handler = h
                     break
        
        if not handler:
            raise ValueError(f"No handler found for file type: {ext}")

        segments_data = handler.read(file_path)
        
        # Create a new chapter
        chapter_title = os.path.basename(file_path)
        
        # Get next order index
        last_chapter = Chapter.select().where(Chapter.project == self.current_project).order_by(Chapter.order_index.desc()).first()
        new_order = (last_chapter.order_index + 1) if last_chapter else 1
        
        new_chapter = Chapter.create(
            project=self.current_project,
            title=chapter_title,
            order_index=new_order
        )
        
        with self.db.atomic():
            for data in segments_data:
                src_text = data['source_text']
                tgt_text = None
                status = SegmentStatus.UNTRANSLATED.value
                
                enforce_match = self.enforce_tm.enforce_translation(src_text)
                if enforce_match:
                    tgt_text = enforce_match
                    status = SegmentStatus.VERIFIED.value
                else:
                    auto_match = self.auto_tm.search_exact_match(src_text)
                    if auto_match:
                        tgt_text = auto_match
                        status = SegmentStatus.TRANSLATED.value

                Segment.create(
                    project=self.current_project,
                    chapter=new_chapter,
                    index=data['index'],
                    source_text=src_text,
                    target_text=tgt_text,
                    status=status,
                    metadata=json.dumps(data.get('metadata')) if data.get('metadata') else None
                )
        return new_chapter

    def load_project(self, db_path):
        """Loads an existing project database."""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Project interface not found at {db_path}")
            
        self.db = init_db(db_path)
        self.current_project = Project.select().first()
        
        # Load and validate project.json
        project_dir = os.path.dirname(os.path.abspath(db_path))
        json_path = os.path.join(project_dir, ".noveltrad", "project.json")
        self.project_config = None
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                from src.core.project_schema import ProjectManagerSchema, ProjectSchema
                migrated_data = ProjectManagerSchema.migrate_v2_to_v3(data)
                self.project_config = ProjectSchema(**migrated_data)
            except Exception as e:
                print(f"Error loading project.json: {e}")
                
        # Load TM Managers data
        self.auto_tm.load_tmx_files(project_dir)
        self.enforce_tm.load_tmx_files(project_dir)
        self.mt_manager.load_tmx_files(project_dir)
        
        self.last_entry = LastEntryManager(os.path.join(project_dir, ".noveltrad"))
        self.last_entry.set_last_project(db_path)
                
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
        segment.set_status(SegmentStatus.VALIDATED)

    def export_project(self, output_path):
        """Exports the current project to the target format."""
        if not self.current_project or not self.current_project.file_path:
            raise ValueError("No active project or source file missing")
            
        _, ext = os.path.splitext(output_path)
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

    def search_translation_memory(self, text, source_lang=None, target_lang=None, threshold=60, limit=10):
        """Search TM for similar segments using fuzzy matching."""
        if not self.current_project or not text:
            return []
        src = source_lang or self.current_project.source_language
        tgt = target_lang or self.current_project.target_language
        
        query = TranslationMemory.select().where(
            (TranslationMemory.source_lang == src) &
            (TranslationMemory.target_lang == tgt)
            # Only match the current project. Wait, the original code didn't filter by project in search_translation_memory! 
            # TM usually spans the project. Project filtering wasn't there originally but it's okay.
        )
        
        words = [w for w in text.split() if len(w) > 3]
        if words:
            import operator
            from functools import reduce
            # Limit to top 5 longest words to prevent massive query, cast a wide net
            longest_words = sorted(words, key=len, reverse=True)[:5]
            conditions = [TranslationMemory.source_text.contains(w) for w in longest_words]
            query = query.where(reduce(operator.or_, conditions))
        
        from difflib import SequenceMatcher
        matches = []
        for tm in query:
            ratio = SequenceMatcher(None, text, tm.source_text).ratio()
            similarity = int(ratio * 100)
            if similarity >= threshold:
                matches.append({
                    'source': tm.source_text,
                    'target': tm.target_text,
                    'similarity': similarity
                })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)[:limit]

    def _calculate_similarity(self, s1, s2):
        """Calculate simple similarity percentage between two strings. (Deprecated)"""
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
    def close_project(self):
        """Closes the current project and database connection."""
        if self.db:
            self.db.close()
        self.current_project = None
        self.db = None

    def export_project_tmx(self, output_path):
        """Exports all translated segments of the current project to a TMX file."""
        if not self.current_project:
            return False
        
        segments = Segment.select().where(
            (Segment.project == self.current_project) & 
            (Segment.target_text.is_null(False)) & 
            (Segment.target_text != "")
        )
        
        return TMXHandler.export_tmx(
            segments, 
            self.current_project.source_language, 
            self.current_project.target_language, 
            output_path
        )

    def import_project_tmx(self, tmx_path):
        """Import translations from a TMX file into the current project's untranslated segments."""
        if not self.current_project:
            return 0
        
        pairs = TMXHandler.import_tmx(tmx_path)
        # Build a dictionary for fast lookup
        tm_dict = {src: tgt for src, tgt in pairs}
        
        count = 0
        # Only target segments that are currently empty
        segments = Segment.select().where(
            (Segment.project == self.current_project) & 
            ((Segment.target_text.is_null()) | (Segment.target_text == ""))
        )
        
        with self.db.atomic():
            for seg in segments:
                if seg.source_text in tm_dict:
                    seg.target_text = tm_dict[seg.source_text]
                    seg.set_status(SegmentStatus.VALIDATED)
                    count += 1
        return count

    def add_to_tm(self, source, target):
        """Adds a translation pair to the Translation Memory."""
        if not self.current_project or not source or not target:
            return
            
        # Avoid exact duplicates
        exists = TranslationMemory.select().where(
            (TranslationMemory.source_text == source) & 
            (TranslationMemory.target_text == target)
        ).exists()
        
        if not exists:
            TranslationMemory.create(
                source_lang=self.current_project.source_language,
                target_lang=self.current_project.target_language,
                source_text=source,
                target_text=target,
                project=self.current_project
            )

    def get_fuzzy_matches(self, text, threshold=0.6):
        """Deprecated: Finds potential translation matches in the TM."""
        return self.search_translation_memory(text, threshold=int(threshold * 100))

    def auto_structure_project(self, llm_engine, progress_callback=None):
        """Structure AI - split segments into chapters based on LLM detection."""
        if not self.current_project:
            return 0
            
        if progress_callback:
            progress_callback(5, "Collecting segments...")
            
        segments = list(Segment.select().where(Segment.project == self.current_project).order_by(Segment.index))
        if not segments:
            return 0
            
        # 1. Chunk segments to avoid exceeding context limits
        chunks = []
        current_chunk_text = ""
        current_chunk_segments = []
        
        for s in segments:
            line_len = len(s.source_text) + 20 # approx overhead
            if len(current_chunk_text) + line_len > 15000:
                chunks.append((current_chunk_text, current_chunk_segments))
                current_chunk_text = ""
                current_chunk_segments = []
            
            current_chunk_text += f"[{s.index}] {s.source_text}\n"
            current_chunk_segments.append(s)
            
        if current_chunk_text:
            chunks.append((current_chunk_text, current_chunk_segments))
            
        all_chapter_data = []
        
        # 2. Detect chapters via LLM for each chunk
        for i, (chunk_text, chunk_segs) in enumerate(chunks):
            if progress_callback:
                progress = 10 + int(80 * (i / len(chunks))) # range 10-90%
                progress_callback(progress, f"Detecting chapters (chunk {i+1}/{len(chunks)})...")
                
            chapter_list_json = llm_engine.detect_chapters(
                chunk_text, 
                src_lang=self.current_project.source_language, 
                tgt_lang=self.current_project.target_language
            )
            
            try:
                import json
                chapter_list = json.loads(chapter_list_json)
                if isinstance(chapter_list, list):
                    # Keep track of which chunk these belong to to restrict our search space
                    for ch in chapter_list:
                        ch['_chunk_segments'] = chunk_segs
                    all_chapter_data.extend(chapter_list)
            except Exception as e:
                print(f"Error parsing chapter json for chunk {i}: {e}")
                
        if not all_chapter_data:
            return 0
            
        if progress_callback:
            progress_callback(92, "Aligning boundaries...")
            
        # 3. Create new chapters and reassign segments
        count = 0
        from difflib import SequenceMatcher
        
        with self.db.atomic():
            
            boundaries = [] # list of (start_index, title)
            
            for ch_data in all_chapter_data:
                title = ch_data.get('title', "Untitled Chapter")
                start_line = ch_data.get('start_line', "").lower().strip()
                chunk_segs = ch_data.get('_chunk_segments', [])
                
                if not start_line or not chunk_segs:
                    continue
                
                # Find start index with Fuzzy Matching within the specific chunk
                best_match_idx = -1
                best_ratio = 0.0
                
                for s in chunk_segs:
                    source_lower = s.source_text.lower()
                    
                    # Direct check
                    if start_line in source_lower:
                        best_match_idx = s.index
                        best_ratio = 1.0
                        break
                        
                    # Fuzzy check
                    ratio = SequenceMatcher(None, start_line, source_lower).ratio()
                    if ratio > best_ratio and ratio > 0.65: # 65% threshold
                        best_ratio = ratio
                        best_match_idx = s.index
                        
                if best_match_idx != -1:
                    # check if we already have a boundary very close (e.g., within 5 segments)
                    # to prevent duplicate boundaries from overlap or LLM hallucination
                    is_duplicate = any(abs(b[0] - best_match_idx) < 5 for b in boundaries)
                    if not is_duplicate:
                        boundaries.append((best_match_idx, title))

            if not boundaries:
                return 0

            # Sort boundaries just in case
            boundaries.sort()
            
            # Ensure the first boundary starts at segment index 0 if not already
            if boundaries[0][0] > 0:
                 # If the first chapter detected doesn't start at 0, prepend a 'Prologue' or start one
                 # Or just adjust the first boundary to cover the start
                 boundaries.insert(0, (0, "Prologue" if boundaries[0][0] > 10 else boundaries[0][1]))

            if progress_callback:
                progress_callback(95, "Creating chapters in database...")

            # Clean up old chapters
            Chapter.delete().where(Chapter.project == self.current_project).execute()

            # Create chapters and update segments
            for i, (start_idx, title) in enumerate(boundaries):
                end_idx = boundaries[i+1][0] if i+1 < len(boundaries) else 999999
                
                new_chapter = Chapter.create(
                    project=self.current_project,
                    title=title,
                    order_index=i + 1
                )
                
                # Reassign segments in range
                Segment.update(chapter=new_chapter).where(
                    (Segment.project == self.current_project) & 
                    (Segment.index >= start_idx) & 
                    (Segment.index < end_idx)
                ).execute()
                count += 1
                
            if progress_callback:
                progress_callback(100, "Done.")
                
        return count



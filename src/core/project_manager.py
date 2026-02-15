from src.core.database import init_db, Project, Chapter, Segment, GlossaryTerm
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


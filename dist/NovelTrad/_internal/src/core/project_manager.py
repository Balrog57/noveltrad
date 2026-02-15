from src.core.database import init_db, Project, Segment, GlossaryTerm
from src.formats.txt_handler import TxtHandler
from src.formats.epub_handler import EpubHandler
from src.formats.docx_handler import DocxHandler
import os

class ProjectManager:
    def __init__(self):
        self.current_project = None
        self.db = None
        self.handlers = {
            '.txt': TxtHandler(),
            '.epub': EpubHandler(),
            '.docx': DocxHandler()
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
        batch_size = 100
        for i in range(0, len(segments_data), batch_size):
            batch = segments_data[i:i+batch_size]
            with self.db.atomic():
                for data in batch:
                    Segment.create(
                        project=self.current_project,
                        index=data['index'],
                        source_text=data['source_text']
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

    def get_segments(self):
        if not self.current_project:
            return []
        return list(self.current_project.segments)

    def save_translation(self, segment_id, target_text):
        segment = Segment.get_by_id(segment_id)
        segment.target_text = target_text
        segment.status = 'translated'
        segment.save()

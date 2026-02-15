from src.formats.format_handler import FormatHandler
import docx
import os

class DocxHandler(FormatHandler):
    def read(self, file_path):
        doc = docx.Document(file_path)
        segments = []
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if text:
                segments.append({'index': i, 'source_text': text})
        return segments

    def write(self, file_path, segments, original_file_path=None):
        if not original_file_path:
             # Basic creation if no original
             doc = docx.Document()
             for segment in segments:
                 text = segment.target_text if segment.target_text else segment.source_text
                 doc.add_paragraph(text)
             doc.save(file_path)
             return

        # Preservation mode
        doc = docx.Document(original_file_path)
        # TODO: Implement smart replacement preserving runs/styles
        # This acts as a placeholder
        doc.save(file_path)

    def get_supported_extensions(self):
        return ['.docx']

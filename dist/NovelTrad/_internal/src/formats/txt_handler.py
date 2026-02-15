from src.formats.format_handler import FormatHandler
import os

class TxtHandler(FormatHandler):
    def read(self, file_path):
        segments = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    segments.append({'index': i, 'source_text': line})
        return segments

    def write(self, file_path, segments, original_file_path=None):
        with open(file_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                text = segment.target_text if segment.target_text else segment.source_text
                f.write(f"{text}\n\n")

    def get_supported_extensions(self):
        return ['.txt']

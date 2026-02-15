from src.formats.format_handler import FormatHandler
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os

class EpubHandler(FormatHandler):
    def read(self, file_path):
        book = epub.read_epub(file_path)
        segments = []
        index = 0
        
        # Iterate over document items
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            # Extract text from paragraphs
            # This is a simplified version; real implementation needs to handle IDs and structure preservation
            for p in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text().strip()
                if text:
                    segments.append({
                        'index': index,
                        'source_text': text,
                        'original_id': item.get_name() # Store chapter filename
                    })
                    index += 1
                    
        return segments

    def write(self, file_path, segments, original_file_path=None):
        if not original_file_path:
            raise ValueError("Original EPUB file path required for reconstruction")
            
        book = epub.read_epub(original_file_path)
        
        # Mapping segments by index isn't enough for EPUB as we need to map back to DOM nodes
        # This implementation is a placeholder for the complex logic required
        
        # For MVP: just create a basic EPUB with translated text (ignoring full layout preservation for now)
        # TODO: Implement full structure preservation
        
        epub.write_epub(file_path, book)

    def get_supported_extensions(self):
        return ['.epub']

from src.formats.format_handler import FormatHandler
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString
import os
import copy

class EpubHandler(FormatHandler):
    def read(self, file_path):
        book = epub.read_epub(file_path)
        segments = []
        global_index = 0
        
        # Iterate over document items (HTML chapters)
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            # We use generic bs4 features. explicitly use lxml-xml or html.parser depending on content
            # EPUB is technically XHTML, so 'html.parser' is usually fine, or 'lxml-xml'
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            # recursive traversal to find text nodes
            # We store the 'address' of the text node implicitly by order of appearance within the item
            # This is fragile if the structure changes, but for translation of a static file it's robust enough
            
            # Verify if this item has body content (skip pure navigational items if possible/needed)
            if not soup.find('body'):
                continue

            # We will use a simple specialized walker
            text_nodes = self._get_translatable_text_nodes(soup)
            
            for i, node in enumerate(text_nodes):
                text = node.string.strip()
                if text:
                    segments.append({
                        'index': global_index,
                        'source_text': text,
                        'metadata': {
                            'item_name': item.get_name(),
                            'node_index': i  # The Nth text node in this item
                        }
                    })
                    global_index += 1
                    
        return segments

    def write(self, file_path, segments, original_file_path=None):
        if not original_file_path:
            raise ValueError("Original EPUB file path required for reconstruction")
            
        # 1. Load original
        book = epub.read_epub(original_file_path)
        
        # 2. Group segments by item_name for faster lookup
        segments_by_item = {}
        for seg in segments:
            if not seg.get('target_text'):
                continue # Skip untranslated or empty
                
            meta = seg.get('metadata')
            if not meta: continue
            
            item_name = meta.get('item_name')
            if item_name not in segments_by_item:
                segments_by_item[item_name] = {}
            
            segments_by_item[item_name][meta['node_index']] = seg['target_text']

        # 3. Iterate and replace
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            item_name = item.get_name()
            if item_name in segments_by_item:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                
                text_nodes = self._get_translatable_text_nodes(soup)
                item_translations = segments_by_item[item_name]
                
                modified = False
                for i, node in enumerate(text_nodes):
                    if i in item_translations:
                        # Replace the string content
                        # We use .replace_with to ensure we keep the tree valid
                        new_text = item_translations[i]
                        node.replace_with(new_text)
                        modified = True
                
                if modified:
                    # Update item content. Be careful with encoding.
                    # Output as UTF-8
                    item.set_content(str(soup).encode('utf-8'))

        # 4. Write new EPUB
        epub.write_epub(file_path, book, {})

    def _get_translatable_text_nodes(self, soup):
        """
        Returns a list of NavigableStrings that are children of standard formatting tags.
        We skip pure whitespace or script/style tags.
        """
        nodes = []
        # invalid tags to skip content from
        blacklist = ['script', 'style', 'code', 'pre']
        
        def walker(element):
            if element.name in blacklist:
                return
                
            # If it's a NavigableString and not just whitespace
            if isinstance(element, NavigableString):
                if element.strip():
                    nodes.append(element)
            elif hasattr(element, 'children'):
                for child in element.children:
                    walker(child)
                    
        if soup.body:
            walker(soup.body)
        else:
            walker(soup)
            
        return nodes

    def get_supported_extensions(self):
        return ['.epub']

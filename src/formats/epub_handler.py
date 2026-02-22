from src.formats.format_handler import FormatHandler
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os
import json
from src.core.tag_manager import TagManager

class EpubHandler(FormatHandler):
    def __init__(self):
        super().__init__()
        self.tag_manager = TagManager()

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

            # We will use a simple specialized walker focusing on block elements
            block_nodes = self._get_translatable_blocks(soup)
            
            for i, node in enumerate(block_nodes):
                # Extract the inner HTML to keep inline tags like <b>, <i>, etc.
                inner_html = "".join([str(child) for child in node.contents]).strip()
                if inner_html:
                    # Use TagManager to process inline tags into placeholders
                    clean_text, tags_map = self.tag_manager.extract_tags(inner_html)
                    
                    segments.append({
                        'index': global_index,
                        'source_text': clean_text,
                        'metadata': {
                            'item_name': item.get_name(),
                            'node_index': i,  # The Nth block node in this item
                            'tags_map': tags_map  # Dictionary mapping placeholder -> original tag
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
            
            # In DB contexts, metadata string might be evaluated or parsed, ensure dict
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    pass
                    
            item_name = meta.get('item_name')
            if item_name not in segments_by_item:
                segments_by_item[item_name] = {}
            
            # Store the text and the tags_map so we can reconstruct
            segments_by_item[item_name][meta['node_index']] = {
                'text': seg['target_text'],
                'tags_map': meta.get('tags_map', {})
            }

        # 3. Iterate and replace
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            item_name = item.get_name()
            if item_name in segments_by_item:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                
                block_nodes = self._get_translatable_blocks(soup)
                item_translations = segments_by_item[item_name]
                
                modified = False
                for i, node in enumerate(block_nodes):
                    if i in item_translations:
                        # Restore original tags in the translated text
                        translated_clean = item_translations[i]['text']
                        tags_map = item_translations[i]['tags_map']
                        restored_html = self.tag_manager.restore_tags(translated_clean, tags_map)
                        
                        # Replace the block's inner HTML with the restored HTML
                        # Create a new BeautifulSoup object from the restored HTML to parse it properly
                        new_content_soup = BeautifulSoup(restored_html, 'html.parser')
                        node.clear()  # Remove old contents
                        # IMPORTANT: wrap in list() because .append removes from the original tree
                        for child in list(new_content_soup.contents):
                            node.append(child)
                        modified = True
                
                if modified:
                    # Update item content. Be careful with encoding.
                    # Output as UTF-8
                    item.set_content(str(soup).encode('utf-8'))

        # 4. Write new EPUB
        epub.write_epub(file_path, book, {})

    def _get_translatable_blocks(self, soup):
        """
        Returns a list of BeautifulSoup block elements that contain translatable text.
        Instead of navigating to the deepest NavigableString, we treat blocks (p, h1, div, li)
        as a single unit containing inline formatting.
        """
        nodes = []
        # Elements to extract as whole blocks
        block_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'td', 'th', 'blockquote']
        # Elements to totally ignore 
        blacklist = ['script', 'style', 'code', 'pre', 'head', 'meta', 'link', 'nav']
        
        # We find all block tags, but we must ensure we don't grab nested blocks multiple times.
        # A simple approach: grab block_tags that don't contain other block_tags.
        for tag_name in block_tags:
            for element in soup.find_all(tag_name):
                # Check if it has any block_tags as descendants
                has_inner_blocks = False
                for inner_tag_name in block_tags:
                    if element.find(inner_tag_name):
                        has_inner_blocks = True
                        break
                        
                # Skip if it's inside a blacklist
                is_blacklisted = False
                for parentLine in element.parents:
                    if parentLine.name in blacklist:
                        is_blacklisted = True
                        break
                        
                if not has_inner_blocks and not is_blacklisted:
                    # Verify it actually has some text inside
                    if element.get_text(strip=True):
                        nodes.append(element)
                        
        # The list might not be in the document order. Fix it using .sourceline if available, 
        # or just find all and filter.
        
        # Better approach for order: walk the tree.
        ordered_nodes = []
        def block_walker(element):
            if hasattr(element, 'name') and element.name in blacklist:
                return
            
            if hasattr(element, 'name') and element.name in block_tags:
                has_inner_blocks = False
                for inner_tag_name in block_tags:
                    if element.find(inner_tag_name):
                        has_inner_blocks = True
                        break
                
                if not has_inner_blocks and element.get_text(strip=True):
                    ordered_nodes.append(element)
                    return # Don't traverse inside this block
            
            if hasattr(element, 'children'):
                for child in element.children:
                    block_walker(child)
                    
        if soup.body:
            block_walker(soup.body)
        else:
            block_walker(soup)
            
        return ordered_nodes

    def get_supported_extensions(self):
        return ['.epub']

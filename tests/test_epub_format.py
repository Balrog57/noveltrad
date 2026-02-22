import os
import shutil
import pytest
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from src.formats.epub_handler import EpubHandler

def create_mock_epub(file_path):
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title('Test Formatting Preservation')
    book.set_language('en')

    # Chapter 1 with various formatted blocks
    c1 = epub.EpubHtml(title='Chapter 1', file_name='chap_01.xhtml', lang='en')
    c1.content = '''
        <html>
            <body>
                <h1>Title with <b>bold</b> text</h1>
                <p>A simple paragraph with <i>italic</i> and <b>bold</b> formatting.</p>
                <div>A div block with a <a href="http://example.com">link</a> inside.</div>
                <p>Pure text without formatting.</p>
            </body>
        </html>
    '''
    book.add_item(c1)
    
    # Simple spine
    book.spine = ['nav', c1]
    
    # We do not need complex TOC or NCX to test basic block extraction
    # The epub.write_epub function often crashes without perfectly structured TOCs
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Don't fail if NCX generation complains about TOC
    epub.write_epub(file_path, book, {"ignore_ncx": True})

def test_epub_format_preservation(tmp_path):
    epub_path = tmp_path / "test_format.epub"
    out_path = tmp_path / "out_format.epub"
    create_mock_epub(str(epub_path))

    handler = EpubHandler()
    
    # 1. Read the EPUB
    segments = handler.read(str(epub_path))
    
    # Check that segments were extracted correctly and placeholders applied
    assert len(segments) == 4
    
    # <h1>
    assert segments[0]['source_text'] == "Title with <b0>bold</b0> text"
    assert 'tags_map' in segments[0]['metadata']
    assert '<b0>' in segments[0]['metadata']['tags_map']
    
    # <p>
    assert segments[1]['source_text'] == "A simple paragraph with <i0>italic</i0> and <b0>bold</b0> formatting."
    assert '<i0>' in segments[1]['metadata']['tags_map']
    
    # <div>
    assert segments[2]['source_text'] == 'A div block with a <a0>link</a0> inside.'
    assert '<a0>' in segments[2]['metadata']['tags_map']
    
    # <p> pure text
    assert segments[3]['source_text'] == "Pure text without formatting."
    assert not segments[3]['metadata']['tags_map']

    # 2. Translate the segments (simulating human/LLM translation keeping the tags)
    segments[0]['target_text'] = "Titre avec texte <b0>gras</b0>"
    segments[1]['target_text'] = "Un paragraphe simple avec un formatage <i0>italique</i0> et <b0>gras</b0>."
    segments[2]['target_text'] = """Un bloc div avec un <a0>lien</a0> à l'intérieur."""
    segments[3]['target_text'] = "Texte pur sans formatage."

    # 3. Write out the new translated EPUB
    handler.write(str(out_path), segments, original_file_path=str(epub_path))
    
    # 4. Read back the new EPUB and verify the raw HTML output
    book_out = epub.read_epub(str(out_path))
    items = [item for item in book_out.get_items_of_type(ebooklib.ITEM_DOCUMENT) 
             if item.get_name() == 'chap_01.xhtml']
    assert len(items) == 1
    
    soup = BeautifulSoup(items[0].get_content(), 'html.parser')
    
    h1 = soup.find('h1')
    assert str(h1) == "<h1>Titre avec texte <b>gras</b></h1>"
    
    # Find the first paragraph
    p1 = soup.find_all('p')[0]
    assert str(p1) == "<p>Un paragraphe simple avec un formatage <i>italique</i> et <b>gras</b>.</p>"
    
    div = soup.find('div')
    assert str(div) == """<div>Un bloc div avec un <a href="http://example.com">lien</a> à l'intérieur.</div>"""
    
    p2 = soup.find_all('p')[1]
    assert str(p2) == "<p>Texte pur sans formatage.</p>"

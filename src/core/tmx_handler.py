import xml.etree.ElementTree as ET
from datetime import datetime
import os

class TMXHandler:
    @staticmethod
    def export_tmx(segments, source_lang, target_lang, output_path):
        """
        Exports a list of segment objects (with source_text and target_text) to a TMX file.
        """
        tmx = ET.Element('tmx', version='1.4')
        header = ET.SubElement(tmx, 'header', {
            'creationtool': 'NovelTrad',
            'creationtoolversion': '1.0',
            'datatype': 'PlainText',
            'segtype': 'sentence',
            'adminlang': 'en',
            'srclang': source_lang,
            'o-tmf': 'NovelTradDB'
        })
        
        body = ET.SubElement(tmx, 'body')
        
        for seg in segments:
            if not seg.target_text:
                continue
                
            tu = ET.SubElement(body, 'tu')
            
            # Source
            tuv_src = ET.SubElement(tu, 'tuv', {'xml:lang': source_lang})
            seg_src = ET.SubElement(tuv_src, 'seg')
            seg_src.text = seg.source_text
            
            # Target
            tuv_tgt = ET.SubElement(tu, 'tuv', {'xml:lang': target_lang})
            seg_tgt = ET.SubElement(tuv_tgt, 'seg')
            seg_tgt.text = seg.target_text
            
        tree = ET.ElementTree(tmx)
        # Use indent if available (Python 3.9+)
        if hasattr(ET, 'indent'):
            ET.indent(tree, space="  ", level=0)
            
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        return True

    @staticmethod
    def import_tmx(file_path):
        """
        Parses a TMX file and returns a list of (source_text, target_text) tuples.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            pairs = []
            for tu in root.findall('.//tu'):
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    src_text = tuvs[0].find('seg').text or ""
                    tgt_text = tuvs[1].find('seg').text or ""
                    if src_text and tgt_text:
                        pairs.append((src_text, tgt_text))
            return pairs
        except Exception as e:
            print(f"Error reading TMX: {e}")
            return []
